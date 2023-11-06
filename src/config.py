from __future__ import annotations

import logging
from dataclasses import dataclass, field
from hashlib import md5
from typing import Any, NamedTuple
from urllib.parse import urljoin

import orjson
import polars as pl
from dash import dcc, html
from dash.dash_table import DataTable
from requests import get as r_get

from src.visualizations.general import make_table

from . import env
from . import ssdl_types as t
from .exceptions import ConfigError
from .parser import parse
from .visualizations import Visualization, make_map, make_plot, make_plot_with_callback

logger = logging.getLogger("dash_app")


@dataclass
class Request:
    """Class representing a request to a data_source section in the config file"""

    url: str
    provider: t.Provider
    type: t.SensorType
    query: Query
    to_table: bool

    df: pl.DataFrame = field(init=False)

    def __post_init__(self) -> None:
        if not self.url.endswith("entities"):
            if not self.url.endswith("/"):
                self.url += "/"
            self.url = urljoin(self.url, "v2/entities")

        if "id" not in self.query.select:
            self.query.select.append("id")

        self._request()

    def _request(self) -> None:
        """Get data from the data source, parse it and save it as a polars DataFrame to `self.df`"""

        params = {"type": self.query.type}
        if self.query.limit:
            params["limit"] = self.query.limit
        else:
            params["limit"] = 1000
        resp = r_get(self.url, params=params)
        data = orjson.loads(resp.content)

        if not data:
            raise ValueError("No data received")

        data_list: list[list[Any]] = parse(data, self.query.select)

        self.df = pl.DataFrame(data_list, schema=self.query.select)

    def _convert_to_table(self) -> DataTable:
        return make_table(self.df)


class Query(NamedTuple):
    """Class representing a query to a data_source section in the config file"""

    type: str = ""
    select: list[str] = []
    limit: int | None = None


class GridItem(NamedTuple):
    """Class representing a grid item in the dashboard"""

    plot: Visualization | None = None  # visualization
    selector: dcc.Dropdown | None = None  # dropdown in the dashboard
    plot_id: str | None = None  # id of the plot


class App:
    def __init__(
        self,
        app_config: dict[str, Any] | None = None,  # pyright: ignore
    ) -> None:
        requests = {}

        logger.info("Initializing app...")

        if app_config is None:
            if env.FILE_PATH.startswith("https://"):
                app_config: dict[str, Any] = r_get(env.FILE_PATH).json()
            else:
                with open(env.FILE_PATH, "r") as f:
                    app_config = orjson.loads(f.read())

        service = self._create_service(app_config)

        try:
            requests = self._parse_requests_config(
                app_config["data_sources"]["measurements"]
            )
            plots = self._parse_plots_config(
                app_config["application"]["visualizations"], requests
            )
            tables = self._create_tables(requests)
            hash = self._calc_hash(str(app_config["application"]["visualizations"]))

        except ConfigError as e:
            e.log()
            plots = []
            tables = []
            hash = self._calc_hash("empty")

        except Exception as e:
            logger.exception(e)
            plots = []
            tables = []
            hash = self._calc_hash("empty")

        self.service: t.Service = service
        self.requests: dict[str, Request] = requests
        self.plots: list[GridItem] = plots
        self.tables: list[GridItem] = tables
        self.hash: str = hash

    def _parse_requests_config(self, data: dict[str, Any]) -> dict[str, Request]:
        requests = {}
        for name, request in data.items():
            try:
                requests[name] = Request(
                    url=request["uri"],
                    type=t.SensorType(request["type"].lower()),
                    provider=t.Provider(request["provider"].lower()),
                    query=Query(
                        request["query"]["type"],
                        request["query"]["select"],
                        request["query"].get("limit"),
                    ),
                    to_table=request.get("table", False),
                )
            except KeyError as e:
                raise ConfigError(
                    f"Invalid config file. Missing key {e} in {name} request.",
                    "Please check your config file.",
                )

        return requests

    def _parse_plots_config(self, data: dict[str, Any], requests) -> list[GridItem]:
        plots = []
        for i, plot in enumerate(data.values()):
            try:
                if plot["type"] == "Map":
                    plot_item = self._parse_plots_config_map(plot, requests)
                else:
                    plot_item = self._parse_plots_config_plot(plot, requests, i)

                plots.append(plot_item)

            except KeyError as e:
                raise ConfigError(f"Missing key {e} in plot {plot['name']}")

            except IndexError:
                raise ConfigError(
                    f"Invalid config file. Chech if '{plot['name']}.data' has at least 2 items. {plot['data']=}",
                    "Please check your config file.",
                )
        return plots

    def _parse_plots_config_map(self, plot: dict[str, Any], requests) -> GridItem:
        return GridItem(
            plot=make_map(plot, requests),
        )

    def _parse_plots_config_plot(
        self, plot: dict[str, Any], requests, i: int
    ) -> GridItem:
        if group_by := plot.get("group_by"):
            comp_id = f"sag-selector-{i}"
            graph_id = f"sag-plot{i}"
            func_name = f"update_graph_{i}"

            make_plot_with_callback(
                plot,
                requests=requests,
                comp_id=comp_id,
                graph_id=graph_id,
                func_name=func_name,
            )
            return GridItem(
                selector=self._create_selector(
                    group_by, comp_id, requests, plot["source"]
                ),
                plot_id=graph_id,
            )

        return GridItem(
            plot=make_plot(plot, requests),
        )

    def _create_service(self, app_config: dict[str, Any]) -> t.Service:
        return t.Service(
            name=app_config["service"]["name"],
            version=t.Version(
                app_config["service"]["version"]["major"],
                app_config["service"]["version"]["minor"],
                app_config["service"]["version"]["patch"],
            ),
            scope=t.Scope(app_config["service"]["scope"].lower()),
        )

    def _calc_hash(self, _to_hash: str | dict[str, Any]) -> str:
        """
        Calculates the hash of visualizations config part

        :param _to_hash: config str to be hashed
        :return: MD5 hash
        """

        if isinstance(_to_hash, dict):
            _to_hash = str(_to_hash)

        return md5(_to_hash.encode()).hexdigest()

    def _create_selector(
        self, group_by: str, comp_id: str, requests: dict[str, Request], source: str
    ):
        return (
            html.Label(group_by.casefold().capitalize()),
            dcc.Dropdown(
                self._get_data(requests, source, group_by).unique().sort().to_list(),
                id=comp_id,
            ),
        )

    def _create_tables(self, requests: dict[str, Request]) -> list[GridItem]:
        tables = []
        for request in requests.values():
            if request.to_table:
                tables.append(GridItem(plot=request._convert_to_table()))

        return tables

    def _get_data(
        self, requests: dict[str, Request], source: str, value: str
    ) -> pl.Series:
        return requests[source].df.select(pl.col(value)).to_series()
