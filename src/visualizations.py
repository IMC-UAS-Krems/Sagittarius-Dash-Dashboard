from __future__ import annotations

import logging
import textwrap
from typing import Literal

import polars as pl
from dash import Input, Output, callback
from plotly import graph_objects as go

from requests import get as r_get
from src.model import GeoMap, Panel

from .requests import DataSources, Filter, Selector

logger = logging.getLogger("dash_app")

VisualizationType = Literal[
    "timeseries", "xy_chart", "bar_chart", "pie_chart", "geomap"
]

type Coordinates = dict[Literal["lat", "lon"], float]

_all__ = [
    "make_map",
    "make_plot",
    "make_table",
    "make_plot_with_callback",
    "Visualization",
    "VisualizationType",
]


def make_map(plot_name: str, plot_config: GeoMap):
    return _create_map(plot_name, plot_config)


def make_plot(plot_name: str, plot_config: Panel):
    return _make_plot(plot_name, plot_config)


def _make_plot(plot_name: str, plot_config: Panel, filter_value: str | None = None):
    match plot_config.type:
        case "timeseries":
            return _create_timeseries(plot_name, plot_config, filter_value=filter_value)
        case "xy_chart":
            return _create_xy_chart(plot_name, plot_config, filter_value=filter_value)
        case "bar_chart":
            return _create_bar_chart(plot_name, plot_config, filter_value=filter_value)
        case "pie_chart":
            return _create_pie_chart(plot_name, plot_config, filter_value=filter_value)
        case _:
            raise ValueError(f"Invalid plot type: {plot_config.type}")


def make_plot_with_callback(
    plot_name: str,
    plot_config: Panel,
    comp_id: str,
    graph_id: str,
    geo_map_id: str | None,
):
    """
    Makes a plot with a callback to update the plot on input change.
    See https://dash.plotly.com/basic-callbacks
    """

    @callback(
        Output(component_id=graph_id, component_property="figure"),
        Input(component_id=comp_id, component_property="value"),
    )
    def _func(input: str) -> go.Figure:
        if input:
            return _make_plot(plot_name, plot_config, filter_value=input)

        fig = go.Figure()
        __apply_default_layout(fig, plot_name)

        return fig

    if geo_map_id:

        @callback(
            Output(
                component_id=graph_id, component_property="figure", allow_duplicate=True
            ),
            Input(component_id=geo_map_id, component_property="clickData"),
            prevent_initial_call=True,
        )
        def _func_map(geomap_input: dict) -> go.Figure:
            if geomap_input:
                return _make_plot(
                    plot_name,
                    plot_config,
                    filter_value=geomap_input["points"][0]["customdata"][-1],
                )

            fig = go.Figure()
            __apply_default_layout(fig, plot_name)

            return fig


def _get_df(name: str):
    return DataSources.get_request(name)


def _get_map_center(area: str) -> Coordinates:
    result: list[dict[str, int]] = r_get(
        "https://nominatim.openstreetmap.org/search",
        params={"city": area, "format": "json", "limit": 1},
    ).json()

    if not result:
        raise ValueError(f"Could not find location for {area}")

    location: Coordinates = {
        "lat": float(result[0]["lat"]),
        "lon": float(result[0]["lon"]),
    }
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


def _create_map(plot_name: str, plot_config: GeoMap) -> go.Figure:
    def data_selector(path) -> Selector:
        return lambda df: df.unique(subset="id", maintain_order=True).select(
            pl.col(path)
        )

    def custom_data_selector(paths) -> Selector:
        return lambda df: (
            df.unique(subset="id", maintain_order=True)
            .select(paths)
            .cast(pl.Utf8)
            .fill_null("unknown")
            .with_columns(
                (pl.all().map_elements(lambda x: "<br>".join(textwrap.wrap(x, 40))))
            )
        )

    df = _get_df(plot_config.source)
    lat_lon = plot_config.traces[0]
    label = plot_config.traces[1]
    extra = plot_config.traces[2:] + ["id"]

    lat = (
        df.get_data(data_selector(lat_lon))
        .to_series()
        .map_elements(lambda x: x[0], return_dtype=pl.Float32)
    )
    lon = (
        df.get_data(data_selector(lat_lon))
        .to_series()
        .map_elements(lambda x: x[1], return_dtype=pl.Float32)
    )
    custom_data = df.get_data(custom_data_selector(extra)).rows()
    hover_text = df.get_data(data_selector(label)).to_series().to_list()

    fig = go.Figure(
        go.Scattermap(
            lat=lat,
            lon=lon,
            mode="markers",
            customdata=custom_data,
            hovertext=hover_text,
        )
    )
    # set mapbox_style
    fig.update_layout(
        mapbox_style="carto-positron",
        margin=dict(l=10, r=10, t=40, b=10),
        title=plot_name,
    )

    fig.update_traces(
        hovertemplate="<b>%{hovertext}</b><br><br>"
        + "<br>".join(
            [
                "<b>" + key.capitalize() + "</b>: %{customdata[" + str(i) + "]}"
                for i, key in enumerate(extra)
                if key != "id"
            ]
        )
        + "<extra></extra>"
    )

    if plot_config.area:
        try:
            fig.update_layout(
                mapbox=dict(
                    center=_get_map_center(plot_config.area),
                    zoom=10,
                )
            )
        except ValueError as e:
            logger.error(e)
    return fig


def __apply_default_layout(fig: go.Figure, title: str):
    fig.update_layout(
        title=title,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        showlegend=True,
        margin=dict(l=20, r=60, t=40, b=20),
    )


def _create_timeseries(
    plot_name: str,
    plot_config: Panel,
    filter_col: str = "id",
    filter_value: str | None = None,
) -> go.Figure:
    def get_data(path: str) -> Selector:
        return lambda df: df.select(pl.col(path))

    def filter_data(filter_col: str, filter_value: str) -> Filter:
        return lambda df: df.filter(pl.col(filter_col) == filter_value)

    fig = go.Figure()
    df = _get_df(plot_config.source)
    for i in range(1, len(plot_config.traces)):
        trace = plot_config.traces[i]
        x = (
            df.get_data(
                get_data(plot_config.traces[0]),
                filter=filter_data(filter_col, filter_value) if filter_value else None,
            ).to_series()
            # .sort()
        )
        y = df.get_data(
            get_data(trace),
            filter=filter_data(filter_col, filter_value) if filter_value else None,
        ).to_series()
        fig.add_scatter(
            x=x,
            y=y,
            mode="lines",
            name=trace,
        )
    __apply_default_layout(fig, plot_name)
    return fig


def _create_xy_chart(
    plot_name: str,
    plot_config: Panel,
    filter_col: str = "id",
    filter_value: str | None = None,
) -> go.Figure:
    def get_data(path: str) -> Selector:
        return lambda df: df.select(pl.col(path))

    def filter_data(filter_col: str, filter_value: str) -> Filter:
        return lambda df: df.filter(pl.col(filter_col) == filter_value)

    fig = go.Figure()
    df = _get_df(plot_config.source)
    for i in range(1, len(plot_config.traces)):
        trace = plot_config.traces[i]
        x = df.get_data(
            get_data(plot_config.traces[0]),
            filter=filter_data(filter_col, filter_value) if filter_value else None,
        ).to_series()
        y = df.get_data(
            get_data(trace),
            filter=filter_data(filter_col, filter_value) if filter_value else None,
        ).to_series()
        fig.add_scatter(
            x=x,
            y=y,
            mode="markers",
            name=trace,
        )
    __apply_default_layout(fig, plot_name)
    return fig


def _create_bar_chart(
    plot_name: str,
    plot_config: Panel,
    filter_col: str = "id",
    filter_value: str | None = None,
) -> go.Figure:
    def get_data(path: str) -> Selector:
        return lambda df: df.select(pl.col(path))

    def filter_data_with_agg(
        filter_col: str, filter_value: str, agg_col: str
    ) -> Filter:
        return (
            lambda df: df.filter(pl.col(filter_col) == filter_value)
            .group_by("dateObserved", maintain_order=True)
            .agg(pl.first(agg_col))
            .sort("dateObserved")
        )

    def filter_data(filter_col: str, filter_value: str) -> Filter:
        return lambda df: df.filter(pl.col(filter_col) == filter_value)

    fig = go.Figure()
    df = _get_df(plot_config.source)
    for i in range(1, len(plot_config.traces)):
        trace = plot_config.traces[i]
        x = (
            df.get_data(
                get_data(plot_config.traces[0]),
                filter=filter_data(filter_col, filter_value) if filter_value else None,
            )
            .to_series()
            .sort()
        )
        y = df.get_data(
            get_data(trace),
            filter=filter_data_with_agg(filter_col, filter_value, trace)
            if filter_value
            else None,
        ).to_series()

        fig.add_bar(
            x=x,
            y=y,
            name=trace,
        )
    __apply_default_layout(fig, plot_name)
    return fig


def _create_pie_chart(
    plot_name: str,
    plot_config: Panel,
    filter_col: str = "id",
    filter_value: str | None = None,
) -> go.Figure:
    def get_data(path: str) -> Selector:
        return lambda df: df.select(pl.col(path))

    def filter_data(filter_col: str, filter_value: str) -> Filter:
        return lambda df: df.filter(pl.col(filter_col) == filter_value)

    fig = go.Figure()
    df = _get_df(plot_config.source)
    values = []
    labels = plot_config.traces
    for trace in plot_config.traces:
        values.append(
            df.get_data(
                get_data(trace),
                filter=filter_data(filter_col, filter_value) if filter_value else None,
            )
            .to_series()
            .sum()
        )
    fig.add_pie(values=values, labels=labels, hole=0.3)
    __apply_default_layout(fig, plot_name)
    return fig
