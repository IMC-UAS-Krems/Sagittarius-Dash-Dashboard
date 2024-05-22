from __future__ import annotations

import logging
from dataclasses import dataclass, field
from hashlib import md5
from typing import Any, NamedTuple

import orjson
from plotly.graph_objs import Figure
import polars as pl
from dash import dcc, html
from requests import get as r_get

from src.model import Config, Datasource, GeoMap, Panel, Service

from . import env
from .exceptions import ConfigError
from .parser import parse
from .visualizations import make_map, make_plot, make_plot_with_callback

logger = logging.getLogger("dash_app")


@dataclass
class Request:
    """Class representing a request to a data_source section in the config file"""

    source: Datasource

    df: pl.DataFrame = field(init=False)

    def __post_init__(self) -> None:
        if "id" not in self.source.query.select:
            self.source.query.select.append("id")

        self._request()

    def _request(self) -> None:
        """Get data from the data source, parse it and save it as a polars DataFrame to `self.df`"""

        params = {"type": self.source.query.type}
        params["limit"] = 1000  # type: ignore
        resp = r_get(self.source.uri, params=params)
        data = orjson.loads(resp.content)

        if not data:
            raise ValueError("No data received")

        data_list: list[list[Any]] = parse(data, self.source.query.select)

        self.df = pl.DataFrame(data_list, schema=self.source.query.select)

    # def _convert_to_table(self) -> DataTable:
    #     return make_table(self.df)


class GridItem(NamedTuple):
    """Class representing a grid item in the dashboard"""

    plot: Figure | None = None  # visualization
    selector: dcc.Dropdown | None = None  # dropdown in the dashboard
    plot_id: str | None = None  # id of the plot
    with_callback: bool = False  # whether the plot has a callback


class App:
    def __init__(
        self,
        app_config: Config | None = None,  # pyright: ignore
    ) -> None:
        requests = {}
        file_path: str = env.FILE_PATH  # pyright: ignore

        logger.info("Initializing app...")

        if app_config is None:
            if file_path.startswith("https://"):
                app_config = r_get(file_path).text
            else:
                with open(file_path, "r") as f:
                    app_config = f.read()

            app_config: Config = Config.model_validate_json(app_config)

            logger.info(f"Config file loaded: {app_config=}")

        try:
            requests = self._parse_requests_config(app_config.data_sources)
            plots, selector = self._parse_plots_config(
                app_config.application.visualizations, requests
            )
            hash = self._calc_hash(str(app_config.application.visualizations))

        except ConfigError as e:
            e.log()
            plots = []
            tables = []
            selector = None
            hash = self._calc_hash("empty")

        except Exception as e:
            logger.exception(e)
            plots = []
            tables = []
            selector = None
            hash = self._calc_hash("empty")

        self.service: Service = app_config.service
        self.requests: dict[str, Request] = requests
        self.plots: list[GridItem] = plots
        self.tables: list[GridItem] = []
        self.hash: str = hash
        self.selector = selector

    def _parse_requests_config(self, data: dict[str, Datasource]) -> dict[str, Request]:
        requests = {}
        for name, request in data.items():
            try:
                requests[name] = Request(source=request)
            except KeyError as e:
                raise ConfigError(
                    f"Invalid config file. Missing key {e} in {name} request.",
                    "Please check your config file.",
                )

        return requests

    def _parse_plots_config(
        self, data: dict[str, Panel], requests
    ) -> tuple[list[GridItem], dcc.Dropdown | None]:
        plots = []
        selector = None
        for i, (plot_name, plot) in enumerate(data.items()):
            try:
                if isinstance(plot, GeoMap):
                    plot_item = self._parse_plots_config_map(plot_name, plot, requests)
                else:
                    plot_item, sel = self._parse_plots_config_plot(
                        plot_name, plot, requests, i
                    )
                    selector = sel if not selector else selector

                plots.append(plot_item)

            except KeyError as e:
                raise ConfigError(f"Missing key {e} in plot {plot_name}")

            except IndexError:
                raise ConfigError(
                    f"Invalid config file. Chech if '{plot_name}.traces' has at least 2 items. {plot.traces=}",
                    "Please check your config file.",
                )
        return plots, selector

    def _parse_plots_config_map(
        self, plot_name: str, plot: Panel, requests
    ) -> GridItem:
        return GridItem(
            plot=make_map(plot_name, plot, requests),
            plot_id="sag-map",
        )

    def _parse_plots_config_plot(
        self, plot_name: str, plot: Panel, requests, i: int
    ) -> tuple[GridItem, dcc.Dropdown | None]:
        if plot.type in ("timeseries", "xy_chart", "bar_chart", "pie_chart"):
            comp_id = "sag-selector"
            graph_id = f"sag-plot{i}"
            func_name = f"update_graph_{i}"

            make_plot_with_callback(
                plot_name,
                plot,
                requests=requests,
                comp_id=comp_id,
                graph_id=graph_id,
                func_name=func_name,
                geo_map_id="sag-map",
            )
            return (
                GridItem(
                    plot_id=graph_id,
                    with_callback=True,
                ),
                self._create_selector(comp_id, requests, plot.source),
            )

        return GridItem(
            plot=make_plot(plot_name, plot, requests),
        ), None

    def _calc_hash(self, _to_hash: str | dict[str, Any]) -> str:
        """
        Calculates the hash of visualizations config part

        :param _to_hash: config str to be hashed
        :return: MD5 hash
        """

        if isinstance(_to_hash, dict):
            _to_hash = str(_to_hash)

        return md5(_to_hash.encode()).hexdigest()

    def _create_selector(self, comp_id: str, requests: dict[str, Request], source: str):
        options = self._get_data(requests, source, "id").unique().sort().to_list()
        return html.Div(
            dcc.Dropdown(options, options[0], id=comp_id),
            className="flex-shrink basis-1/3",
        )

    # def _create_tables(self, requests: dict[str, Request]) -> list[GridItem]:
    #     tables = []
    #     for request in requests.values():
    #         if request.to_table:
    #             tables.append(GridItem(plot=request._convert_to_table()))
    #
    #     return tables

    def _get_data(
        self, requests: dict[str, Request], source: str, value: str
    ) -> pl.Series:
        return requests[source].df.select(pl.col(value)).to_series()
