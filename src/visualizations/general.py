from __future__ import annotations

import logging
import textwrap
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Literal

import dash_ag_grid as dag
import polars as pl
from dash import Input, Output, callback
from plotly import graph_objects as go
from requests import get as r_get

if TYPE_CHECKING:  # https://docs.python.org/3/library/typing.html#typing.TYPE_CHECKING
    from config import Request

from ..exceptions import ConfigError

logger = logging.getLogger("dash_app")

VisualizationType = Literal["LineChart", "Scatter", "BarChart", "Map", "PieChart"]

_all__ = [
    "make_map",
    "make_plot",
    "make_table",
    "make_plot_with_callback",
    "Visualization",
    "VisualizationType",
]


def make_map(plot_config: dict[str, Any], requests: dict[str, Request]):
    return Map(
        source_name=plot_config["source"],
        name=plot_config["name"],
        type=plot_config["type"],
        area=plot_config["extra"]["area"] if "extra" in plot_config else None,
        lat=plot_config["data"][0],
        lon=plot_config["data"][0],
        label=plot_config["data"][1],
        extra=plot_config["data"][2:],
        requests=requests,
    ).create()


def make_plot_with_callback(
    plot_config: dict[str, Any],
    requests: dict[str, Request],
    comp_id: str,
    graph_id: str,
    func_name: str,
):
    """
    Makes a plot with a callback to update the plot on input change.
    See https://dash.plotly.com/basic-callbacks
    """
    return Plot(
        source_name=plot_config["source"],
        name=plot_config["name"],
        type=plot_config["type"],
        traces=plot_config["traces"],
        filter=plot_config["group_by"],
        requests=requests,
    ).add_callback(comp_id, graph_id, func_name)


def make_plot(plot_config: dict[str, Any], requests: dict[str, Request]):
    return Plot(
        source_name=plot_config["source"],
        name=plot_config["name"],
        type=plot_config["type"],
        traces=plot_config["traces"],
        requests=requests,
    ).create()


def make_table(df: pl.DataFrame) -> go.Figure:
    # fig = go.Figure(
    #     data=[
    #         go.Table(
    #             header=dict(
    #                 values=list(df.columns),
    #                 font=dict(size=10),
    #                 align="center",
    #             ),
    #             cells=dict(
    #                 values=[
    #                     df.select(pl.col(col)).to_series().to_list()
    #                     for col in df.columns
    #                 ],
    #                 align="center",
    #                 height=30,
    #             ),
    #         )
    #     ]
    # )
    # fig.update_layout(
    #     margin=dict(l=10, r=10, t=10, b=10),
    # )
    fig = dag.AgGrid(
        columnDefs=[{"field": col} for col in df.columns],
        rowData=[row for row in df.rows(named=True)],
        dashGridOptions={"pagination": True, "paginationAutoPageSize": True},
        defaultColDef={
            "resizable": True,
            "sortable": True,
            "filter": True,
        },
        columnSize="autoSize",
        style={"height": "100%", "width": "100%"},
    )

    return fig


@dataclass
class Visualization(ABC):
    name: str
    type: VisualizationType
    source_name: str
    requests: dict[str, Any]

    @abstractmethod
    def create(self) -> None:
        pass

    def get_data(self, path: str) -> pl.Series:
        return self.df.select(pl.col(path)).to_series()

    def get_data_with_filter(
        self,
        path: str,
        filter_by: str,
        filter: str,
        bar_chart: bool = False,
    ) -> pl.Series:
        try:
            if bar_chart:
                result = (
                    self.df.filter(pl.col(filter_by) == filter)
                    .group_by("dateObserved", maintain_order=True)
                    .agg(pl.first(path))
                    .sort("dateObserved")
                    .select(pl.col(path))
                )
            else:
                result = self.df.filter(pl.col(filter_by) == filter).select(
                    pl.col(path)
                )
        except KeyError as e:
            sp = str(e).split("\n")
            column_name = sp[0].strip()
            df = sp[3].split(";")[0].strip()
            raise ConfigError(
                f"{self.type} {self.name}: Column '{column_name}' not found in dataframe {df}",
                "Check if 'data_sources.measurements.<name>.query.select' has this key",
            )

        return result.to_series()

    @property
    def df(self) -> pl.DataFrame:
        return self.requests[self.source_name].df


@dataclass
class Map(Visualization):
    lat: str
    lon: str
    label: str
    area: str | None
    extra: list[str]
    center_cache: dict[str, dict[str, float]] = field(default_factory=dict)

    def get_center(self) -> dict[str, float]:
        if self.area in self.center_cache:
            return self.center_cache[self.area]

        result: list[dict[str, int]] = r_get(
            "https://nominatim.openstreetmap.org/search",
            params={"city": self.area, "format": "json", "limit": 1},
        ).json()

        if not result:
            raise ValueError(f"Could not find location for {self.area}")

        location = {"lat": float(result[0]["lat"]), "lon": float(result[0]["lon"])}
        self.center_cache[self.area] = location  # type: ignore (area is always a string because of the create())
        return location

        # WARNING: google api deprecated

        # result: dict[str, dict] = requests.get(
        #     f"https://maps.googleapis.com/maps/api/geocode/json?address={self.area}&key={GEOCODING_KEY}"
        # ).json()
        #
        # if result["status"] != "OK":
        #     raise ValueError(f"Could not find location for {self.area}")
        # location = result["results"][0]["geometry"]["location"]
        #
        # self.center_cache[self.area] = location
        # location["lon"] = location.pop("lng")
        # return location
        #

    def create(self) -> go.Figure:
        # fig = px.scatter_mapbox(
        #     lat=self.get_data(self.lat).apply(lambda x: x[0]),
        #     lon=self.get_data(self.lon).apply(lambda x: x[1]),
        #     hover_name=self.get_data(self.label),
        #     hover_data={
        #         name: self.get_data(name)
        #         .cast(pl.Utf8)
        #         .apply(lambda x: "<br>".join(textwrap.wrap(x, 40)))
        #         .fill_null("unknown")
        #         for name in self.extra
        #     },
        # )

        self.get_custom_data(self.extra)
        fig = go.Figure(
            go.Scattermapbox(
                lat=self.get_data(self.lat).apply(lambda x: x[0]),
                lon=self.get_data(self.lon).apply(lambda x: x[1]),
                mode="markers",
                customdata=self.get_custom_data(self.extra),
                hovertext=self.get_data(self.label).to_list(),
            )
        )
        # set mapbox_style
        fig.update_layout(
            mapbox_style="carto-positron",
            margin=dict(l=10, r=10, t=40, b=10),
            title=self.name,
        )

        fig.update_traces(
            hovertemplate="<b>%{hovertext}</b><br><br>"
            + "<br>".join(
                [
                    "<b>" + key.capitalize() + "</b>: %{customdata[" + str(i) + "]}"
                    for i, key in enumerate(self.extra)
                ]
            )
            + "<extra></extra>"
        )

        if self.area:
            try:
                fig.update_layout(
                    mapbox=dict(
                        center=self.get_center(),
                        zoom=10,
                    )
                )
            except ValueError as e:
                logger.error(e)
        return fig

    def get_data(self, path: str) -> pl.Series:
        try:
            result = (
                self.df.unique(subset="id", maintain_order=True)
                .select(pl.col(path))
                .to_series()
            )
            return result

        except KeyError:
            raise ConfigError(
                f"Map {self.name}: Column {path} not found in {self.name}",
                "Check if 'data_sources.measurements.<name>.query.select' has this key",
            )

    def get_custom_data(self, paths: list[str]) -> list[tuple[str]]:
        try:
            # python polars dataframe apply to each column
            result = (
                self.df.select(paths)
                .cast(pl.Utf8)
                .fill_null("unknown")
                .with_columns(
                    (pl.all().map_elements(lambda x: "<br>".join(textwrap.wrap(x, 40))))
                )
            )
            return result.rows()

        except KeyError:
            raise ConfigError(
                f"Map {self.name}: Column {paths} not found in {self.name}",
                "Check if 'data_sources.measurements.<name>.query.select' has this key",
            )


@dataclass
class Plot(Visualization):
    traces: list[Any]  # list[dict[str, str]] | list[str]
    filter: str = field(default_factory=str)
    graph_id: str = field(init=False)

    def create(self, filter_by: str | None = None) -> go.Figure:
        # TODO: this needs to be refactored (probably with a factory)
        fig = go.Figure()

        if self.type == "LineChart":
            for trace in self.traces:
                fig.add_scatter(
                    x=self.get_data(trace["x"])
                    if not self.filter
                    else self.get_data_with_filter(trace["x"], self.filter, filter_by),  # type: ignore
                    y=self.get_data(trace["y"])
                    if not self.filter
                    else self.get_data_with_filter(trace["y"], self.filter, filter_by),  # type: ignore
                    mode="lines+markers",
                    name=trace["y"],
                )

        elif self.type == "Scatter":
            for trace in self.traces:
                fig.add_scatter(
                    x=self.get_data(trace["x"])
                    if not self.filter
                    else self.get_data_with_filter(trace["x"], self.filter, filter_by),  # type: ignore
                    y=self.get_data(trace["y"])
                    if not self.filter
                    else self.get_data_with_filter(trace["y"], self.filter, filter_by),  # type: ignore
                    mode="markers",
                    name=trace["y"],
                )

        elif self.type == "BarChart":
            for trace in self.traces:
                fig.add_bar(
                    x=self.get_data("dateObserved").sort()
                    if not self.filter
                    else self.get_data_with_filter(
                        "dateObserved",
                        self.filter,
                        filter_by,  # type: ignore
                    ).sort(),
                    y=self.get_data(trace)
                    if not self.filter
                    else self.get_data_with_filter(
                        trace,
                        self.filter,
                        filter_by,
                        bar_chart=True,  # type: ignore
                    ),
                    name=trace,
                )

        elif self.type == "PieChart":
            values = []
            labels = self.traces
            for trace in self.traces:
                values.append(
                    self.get_data(trace).sum()
                    if not self.filter
                    else self.get_data_with_filter(trace, self.filter, filter_by).sum()  # type: ignore
                )
            fig.add_pie(values=values, labels=labels, hole=0.3)

        fig.update_layout(
            title=self.name,
            legend=dict(
                orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1
            ),
            showlegend=True,
            margin=dict(l=20, r=60, t=40, b=20),
        )
        return fig

    def add_callback(self, comp_id: str, graph_id: str, func_name: str) -> None:
        @callback(
            Output(component_id=graph_id, component_property="figure"),
            Input(component_id=comp_id, component_property="value"),
        )
        def _func(input: str) -> go.Figure:
            if input:
                return self.create(input)

            fig = go.Figure()
            fig.update_layout(
                title=self.name,
                legend=dict(
                    orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1
                ),
                showlegend=True,
                margin=dict(l=20, r=60, t=40, b=20),
            )

            return fig

        _func.__name__ = func_name
