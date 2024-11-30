from __future__ import annotations

import logging
from hashlib import md5
from typing import Any, NamedTuple

from plotly.graph_objs import Figure
import polars as pl
from dash import dcc, html
from requests import get as r_get

from src.model import Config, GeoMap, Panel

from . import env
from .exceptions import ConfigError
from .visualizations import make_map, make_plot, make_plot_with_callback
from src.requests import Requests

logger = logging.getLogger("dash_app")


class GridItem(NamedTuple):
    """Class representing a grid item in the dashboard"""

    plot: Figure | None = None  # visualization
    selector: dcc.Dropdown | None = None  # dropdown in the dashboard
    plot_id: str | None = None  # id of the plot
    with_callback: bool = False  # whether the plot has a callback


class App:
    def __init__(
        self,
        app_config_str: str | None = None,  # pyright: ignore
    ) -> None:
        file_path: str = env.FILE_PATH  # pyright: ignore

        logger.info("Initializing app...")

        if app_config_str is None:
            if file_path.startswith("https://"):
                app_config_str = r_get(file_path).text
            else:
                with open(file_path, "r") as f:
                    app_config_str = f.read()

        app_config: Config = Config.model_validate_json(app_config_str)

        logger.info(f"Config file loaded: {app_config=}")

        try:
            Requests.add_requests(app_config.data_sources)
            self.service = app_config.service
            self.plots, self.selector = self._parse_plots_config(
                app_config.application.visualizations
            )
            self.hash = self._calc_hash(str(app_config.application.visualizations))

        except Exception as e:
            if isinstance(e, ConfigError):
                e.log()
            else:
                logger.exception(e)
            self.plots = []
            self.tables = []
            self.selector = None
            self.hash = self._calc_hash("empty")

    def _parse_plots_config(
        self, data: dict[str, Panel]
    ) -> tuple[list[GridItem], dcc.Dropdown | None]:
        plots = []
        selector = None

        need_dropdown_selector = any(
            plot.type in ("timeseries", "xy_chart", "bar_chart", "pie_chart")
            for plot in data.values()
        )
        need_map_selector = (
            any(isinstance(plot, GeoMap) for plot in data.values())
            and need_dropdown_selector
        )

        for i, (plot_name, plot) in enumerate(data.items()):
            try:
                if isinstance(plot, GeoMap):
                    plot_item = self._parse_plots_config_map(plot_name, plot)
                else:
                    plot_item, sel = self._parse_plots_config_plot(plot_name, plot, i)
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

    def _parse_plots_config_map(self, plot_name: str, plot: GeoMap) -> GridItem:
        return GridItem(
            plot=make_map(plot_name, plot),
            plot_id="sag-map",
        )

    def _parse_plots_config_plot(
        self, plot_name: str, plot: Panel, i: int
    ) -> tuple[GridItem, html.Div | None]:
        if plot.type in ("timeseries", "xy_chart", "bar_chart", "pie_chart"):
            comp_id = "sag-selector"
            graph_id = f"sag-plot{i}"
            func_name = f"update_graph_{i}"

            make_plot_with_callback(
                plot_name,
                plot,
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
                self._create_selector(comp_id, plot.source),
            )

        return GridItem(
            plot=make_plot(plot_name, plot),
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

    def _create_selector(self, comp_id: str, source: str):
        options = self._get_data(source, "id").unique().to_list()
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

    def _get_data(self, source: str, value: str) -> pl.Series:
        return Requests.get_request(source).df.select(pl.col(value)).to_series()
