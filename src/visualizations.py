from __future__ import annotations

import logging
import textwrap
from typing import Literal
from itertools import cycle

import polars as pl
from dash import Input, Output, callback
from plotly import graph_objects as go
from plotly.colors import sample_colorscale

from requests import Response
from requests import get as r_get
from src.model import GeoMap, Panel

from .requests import DataSources, Filter, Selector

logger = logging.getLogger("dash_app")

VisualizationType = Literal[
    "timeseries", "xy_chart", "bar_chart", "pie_chart", "boolean_pie", "geomap"
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
    result: Response = r_get(
        "https://nominatim.openstreetmap.org/search",
        params={"city": area, "format": "json", "limit": 1},
        headers={
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:132.0) Gecko/20100101 Firefox/132.0"
        },
    )

    if not result:
        raise ValueError(f"Could not find location for {area}")

    result_json: list[dict[str, int]] = result.json()
    location: Coordinates = {
        "lat": float(result_json[0]["lat"]),
        "lon": float(result_json[0]["lon"]),
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
    print("\n\n----\nCreating map with config:", plot_config)

    # --- HELPER FUNCTIONS ---
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
    # --- HELPER FUNCTIONS ---

    # --- GET DATA - General ---
    df = _get_df(plot_config.source)  # FiwareDatasource object
    print("Traces:", plot_config.traces)  # ['wind
    lat_lon = plot_config.traces[0]
    label = plot_config.traces[1]
    extra = plot_config.traces[2:]
    if "id" not in extra:
        extra.append("id")
    custom_data = df.get_data(custom_data_selector(extra)).rows()
    hover_text = df.get_data(data_selector(label)).to_series().to_list()
    # --- GET DATA - General ---

    # --- INSTANTIATE FIGURE - MODIFY IT BASED ON GEMOETRY_TYPE ---
    fig = go.Figure()
    geometry_type = getattr(plot_config, "geometry_type", "point")
    if geometry_type == "polygon":
        polygons = df.get_data(data_selector(lat_lon)).to_series().to_list()

        # --- Cut to 50 polygons for display ---
        if len(polygons) > 50:
            print(
                f"Warning: More than 50 polygons detected. ({len(polygons)} polygons)")
            polygons = polygons[:50]
        # print("Custom data:", custom_data[0])  # (id,)
        # print("Hover text:", hover_text[0])  # Correct

        # --- Add polygons as Traces ---
        for i, poly in enumerate(polygons):
            if not poly:
                continue
            lats = [vertex[0] for vertex in poly]
            lons = [vertex[1] for vertex in poly]
            fig.add_trace(
                go.Scattermap(
                    lat=lats,
                    lon=lons,
                    mode="lines",
                    fill="toself",
                    # name=hover_text[i],
                    hovertemplate=f"<b>{hover_text[i]}</b><br><br>" + "<br>".join(
                        [f"<b>{extra[j]}</b>: {custom_data[i][j]}" for j in range(len(custom_data[i]))]) + "<extra></extra>"
                )
            )

    # --- GEOMETRY_TYPE = `multiplygon` ---
    elif geometry_type == "multipolygon":
        mpolygons = df.get_data(data_selector(lat_lon)).to_series().to_list()

        # --- Cut to 50 polygons for display ---
        print("\n---\nTrying to create map with multipolygons")
        if len(mpolygons) > 50:
            print(
                f"Warning: >50 multipolygons ({len(mpolygons)}). Showing first 50.")
            mpolygons = mpolygons[:50]

        # --- Add multipolygons as Traces ---
        for i, mpoly in enumerate(mpolygons):
            if not mpoly:
                continue

            lats, lons = [], []
            # Each mpoly is a list of Polygons; each Polygon is a list of rings
            for polygon in mpoly:
                for ring in polygon:
                    for vertex in ring:
                        lats.append(vertex[0])
                        lons.append(vertex[1])
                    # break before next ring
                    lats.append(None)
                    lons.append(None)

            # print("Adding multipolygon", i, "with", len(
            #     lats), "vertices\nCustom data:", custom_data[i], "\nHover text:", hover_text[i])
            fig.add_trace(
                go.Scattermap(
                    lat=lats,
                    lon=lons,
                    mode="lines",
                    fill="toself",
                    name=hover_text[i],
                    hovertemplate=f"<b>{hover_text[i]}</b><br><br>" + "<br>".join(
                        [f"<b>{extra[j]}</b>: {custom_data[i][j]}" for j in range(len(custom_data[i]))]) + "<extra></extra>"
                )
            )

    # --- GEOMETRY_TYPE = `point` - DEFAULT ---
    else:
        lat = df.get_data(data_selector(lat_lon)).to_series() \
                .map_elements(lambda x: x[0], return_dtype=pl.Float32)
        lon = df.get_data(data_selector(lat_lon)).to_series() \
                .map_elements(lambda x: x[1], return_dtype=pl.Float32)

        # --- `color_by` map ---
        if plot_config.color_by:
            # find unique categories
            point_cats = df.get_data(data_selector(plot_config.color_by)) \
                .to_series().to_list()
            unique_cats = [c for c in sorted(set(point_cats)) if c is not None]
            for cat in unique_cats:
                idxs = [i for i, c in enumerate(point_cats) if c == cat]
                fig.add_trace(
                    go.Scattermap(
                        lat=[lat[i] for i in idxs],
                        lon=[lon[i] for i in idxs],
                        mode="markers",
                        marker=dict(size=10),
                        customdata=[custom_data[i] for i in idxs],
                        hovertext=[hover_text[i] for i in idxs],
                        name=str(cat),  # legend entry
                    )
                )

        # --- No `color_by` - single trace ---
        else:
            # single‐trace fallback
            fig.add_trace(
                go.Scattermap(
                    lat=lat,
                    lon=lon,
                    mode="markers",
                    marker=dict(size=10),
                    customdata=custom_data,
                    hovertext=hover_text,
                    name=plot_name,
                )
            )

        fig.update_traces(
            hovertemplate="<b>%{hovertext}</b><br><br>"
            + "<br>".join(
                [
                    "<b>" + key.capitalize() +
                    "</b>: %{customdata[" + str(i) + "]}"
                    for i, key in enumerate(extra)
                ]
            )
            + "<extra></extra>"
        )
        # --- No `color_by` - single trace ---

    # --- EXTRA COMMON SETTINGS ---
    # - layout
    # - map center, zoom
    # - legend position
    fig.update_layout(
        mapbox_style="carto-positron",
        margin=dict(l=10, r=10, t=40, b=10),
        title=plot_name,
    )

    print("Centering map to area:", plot_config.area)
    if plot_config.area:
        try:
            fig.update_layout(
                map=dict(
                    center=_get_map_center(plot_config.area),
                    zoom=10,
                )
            )
        except ValueError as e:
            logger.error(e)

    if hover_text:
        # If the hover_text / title is too long, put the legen below
        if max([len(h) for h in hover_text]) > 15:
            print("Label text too long, putting legend below")
            fig.update_layout(
                legend=dict(
                    orientation="h",      # horizontal legend
                    x=0,                  # align left
                    y=-0.01,              # place it at the top; use e.g. y=-0.1 for below
                    xanchor="left",
                    yanchor="top"
                )
            )

    return fig


def __apply_default_layout(fig: go.Figure, title: str):
    fig.update_layout(
        title=title,
        legend=dict(orientation="h", yanchor="bottom",
                    y=1.02, xanchor="right", x=1),
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

    traces = plot_config.traces

    if "id" in traces:
        traces.remove("id")

    dateObserved_index = traces.index("dateObserved")

    for i in range(len(traces)):
        if i == dateObserved_index:
            continue

        trace = traces[i]
        x = (
            df.get_data(
                get_data(traces[dateObserved_index]),
                filter=filter_data(
                    filter_col, filter_value) if filter_value else None,
            ).to_series()
            # .sort()
        )
        y = df.get_data(
            get_data(trace),
            filter=filter_data(
                filter_col, filter_value) if filter_value else None,
        ).to_series()

        # Remove fully null columns, skip traces with all null values
        if y.null_count() == y.len():
            continue

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

    traces = plot_config.traces

    if "id" in traces:
        traces.remove("id")

    dateObserved_index = traces.index("dateObserved")

    for i in range(len(plot_config.traces)):
        if i == dateObserved_index:
            continue

        trace = traces[i]
        x = df.get_data(
            get_data(traces[dateObserved_index]),
            filter=filter_data(
                filter_col, filter_value) if filter_value else None,
        ).to_series()
        y = df.get_data(
            get_data(trace),
            filter=filter_data(
                filter_col, filter_value) if filter_value else None,
        ).to_series()

        # Remove fully null columns, skip traces with all null values
        if y.null_count() == y.len():
            continue

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
    traces = list(plot_config.traces)  # Work with a mutable copy

    if plot_config.reduce == "unique_trace_counts":
        logger.info(
            f"Creating bar chart '{plot_name}' with 'reduce: unique_trace_counts'."
        )
        if not traces:
            logger.warning(
                f"No traces defined for 'unique_trace_counts' in bar chart '{plot_name}'.")
            __apply_default_layout(fig, plot_name)
            return fig
        if len(traces) > 1:
            logger.warning(
                f"'unique_trace_counts' for bar chart '{plot_name}' expects a single trace, but got {len(traces)}. Using the first one: '{traces[0]}'."
            )

        trace_to_count = traces[0]
        try:
            series_to_count = df.get_data(
                get_data(trace_to_count),
            ).to_series()

            if series_to_count.is_empty() or series_to_count.null_count() == series_to_count.len():
                logger.warning(
                    f"Trace column '{trace_to_count}' for bar chart '{plot_name}' (unique_trace_counts mode) is empty or all nulls."
                )
                __apply_default_layout(fig, plot_name)
                return fig

            value_counts_df = series_to_count.value_counts().sort(by="count").reverse()

            logger.info(
                f"Value counts for trace '{trace_to_count}' in bar chart '{plot_name}': {value_counts_df}"
            )
            x_values = value_counts_df.get_column(trace_to_count).to_list()
            y_values = value_counts_df.get_column("count").to_list()

            fig.add_bar(x=x_values, y=y_values,
                        name=f"Counts of {trace_to_count}")

        except Exception as e:
            logger.error(
                f"Failed to create bar chart '{plot_name}' with 'unique_trace_counts' for trace '{trace_to_count}': {e}."
            )
            __apply_default_layout(fig, plot_name)
            return fig

    else:  # Original logic
        if "id" in traces:
            traces.remove("id")

        if "dateObserved" not in traces:
            logger.error(
                f"Bar chart '{plot_name}' requires 'dateObserved' in traces for default mode.")
            __apply_default_layout(fig, plot_name)
            return fig

        dateObserved_index = traces.index("dateObserved")

        for i in range(len(traces)):  # Iterate using the modified traces list
            if i == dateObserved_index:
                continue

            trace = traces[i]
            x_series = (
                df.get_data(
                    # Use traces list here
                    get_data(traces[dateObserved_index]),
                    filter=filter_data(
                        filter_col, filter_value) if filter_value else None,
                )
                .to_series()
                .sort()
            )
            y_series = df.get_data(
                get_data(trace),
                filter=filter_data_with_agg(filter_col, filter_value, trace)
                if filter_value
                else get_data(trace),  # If no filter, just get the data
            ).to_series()

            # Ensure x and y series align if filter_data_with_agg was used for y
            # This might be complex if filter_data_with_agg changes the length or order of dateObserved
            # For simplicity, assuming filter_data_with_agg preserves alignment or is handled by Polars' join/aggregation logic
            # If not filtering, x and y should align by default if from the same source df.
            # If filter_value is present, filter_data_with_agg is applied to y,
            # and filter_data to x. We need to ensure x_series aligns with the dateObserved from y_series.
            if filter_value:
                # Re-fetch x based on the dateObserved from the aggregated y
                # This assumes filter_data_with_agg returns a dataframe with 'dateObserved'
                filtered_y_df = df.get_data(
                    None,  # No specific selector, operate on whole df
                    filter=filter_data_with_agg(
                        filter_col, filter_value, trace)
                )
                if 'dateObserved' in filtered_y_df.columns:
                    x_series = filtered_y_df.get_column(
                        'dateObserved').sort().to_series()
                    y_series = filtered_y_df.get_column(
                        trace).to_series()  # Assuming agg keeps trace name
                else:  # Fallback if dateObserved is not in the aggregated output as expected
                    logger.warning(
                        f"Could not realign x-axis for bar chart '{plot_name}' after aggregation. Plot might be incorrect.")

            if y_series.is_empty() or y_series.null_count() == y_series.len():
                continue

            fig.add_bar(
                x=x_series,
                y=y_series,
                name=trace,
            )

    __apply_default_layout(fig, plot_name)
    return fig

# def _create_bar_chart(
#     plot_name: str,
#     plot_config: Panel,
#     filter_col: str = "id",
#     filter_value: str | None = None,
# ) -> go.Figure:
#     def get_data(path: str) -> Selector:
#         return lambda df: df.select(pl.col(path))

#     def filter_data_with_agg(
#         filter_col: str, filter_value: str, agg_col: str
#     ) -> Filter:
#         return (
#             lambda df: df.filter(pl.col(filter_col) == filter_value)
#             .group_by("dateObserved", maintain_order=True)
#             .agg(pl.first(agg_col))
#             .sort("dateObserved")
#         )

#     def filter_data(filter_col: str, filter_value: str) -> Filter:
#         return lambda df: df.filter(pl.col(filter_col) == filter_value)

#     fig = go.Figure()
#     df = _get_df(plot_config.source)

#     traces = plot_config.traces

#     if "id" in traces:
#         traces.remove("id")

#     dateObserved_index = traces.index("dateObserved")

#     for i in range(len(plot_config.traces)):
#         if i == dateObserved_index:
#             continue

#         trace = traces[i]
#         x = (
#             df.get_data(
#                 get_data(traces[dateObserved_index]),
#                 filter=filter_data(
#                     filter_col, filter_value) if filter_value else None,
#             )
#             .to_series()
#             .sort()
#         )
#         y = df.get_data(
#             get_data(trace),
#             filter=filter_data_with_agg(filter_col, filter_value, trace)
#             if filter_value
#             else None,
#         ).to_series()

#         # Remove fully null columns, skip traces with all null values
#         if y.null_count() == y.len():
#             continue

#         fig.add_bar(
#             x=x,
#             y=y,
#             name=trace,
#         )
#     __apply_default_layout(fig, plot_name)
#     return fig


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
    labels = []

    # Work on a copy so we don't modify the original list.
    processed_traces = list(plot_config.traces)
    if "id" in processed_traces:
        processed_traces.remove("id")

    # If there are no traces to process, bail out.
    if not processed_traces:
        logger.warning(f"No traces to display for pie chart '{plot_name}'.")
        __apply_default_layout(fig, plot_name)
        return fig

    if plot_config.reduce == "sum":  # Check if reduce operation is 'sum'
        logger.info(
            f"Creating pie chart '{plot_name}' by summing each trace based on 'reduce: sum' config."
        )
        for trace_column in processed_traces:
            try:
                series = df.get_data(
                    # Get data for the current trace_column
                    get_data(trace_column),
                    # filter=filter_data(
                    #     filter_col, filter_value
                    # ) if filter_value else None,
                ).to_series()

                # Apply the filter AFTER getting the series
                # if filter_value:
                #     series = series[df.get_data(lambda df: df.select(
                #         pl.col(filter_col))).to_series() == filter_value]

                if series.is_empty() or series.null_count() == series.len():
                    logger.warning(
                        f"Trace column '{trace_column}' for pie chart '{plot_name}' (reduce mode) is empty or all nulls. Skipping."
                    )
                    continue

                if series.dtype == pl.Boolean:
                    total_for_trace = series.sum()  # Sum booleans (True = 1, False = 0)
                elif series.dtype.is_numeric():
                    total_for_trace = series.sum()
                else:
                    logger.warning(
                        f"Trace column '{trace_column}' for pie chart '{plot_name}' (reduce mode) is not numeric or boolean ({series.dtype}). Skipping sum."
                    )
                    continue

                values.append(total_for_trace)
                # Label is the name of the trace column
                labels.append(trace_column)
            except Exception as e:
                logger.error(
                    f"Failed to sum trace column '{trace_column}' for pie chart '{plot_name}' (reduce mode): {e}. Skipping."
                )
                continue

        if not values:  # If all traces were skipped or failed
            logger.warning(
                f"No valid data to display in pie chart '{plot_name}' after 'reduce: sum' attempt.")
            __apply_default_layout(fig, plot_name)
            return fig

    else:  # Original logic when plot_config.reduce is None or not "sum"
        # Use the first trace to determine type for row-by-row or boolean logic
        first_series = df.get_data(
            get_data(processed_traces[0]),
            filter=filter_data(
                filter_col, filter_value) if filter_value else None,
        ).to_series()

        if first_series.is_empty():
            logger.warning(
                f"First trace '{processed_traces[0]}' for pie chart '{plot_name}' is empty. Cannot determine data type for default mode.")
            __apply_default_layout(fig, plot_name)  # Create an empty chart
            return fig

        # Check if the data type of the first series is boolean
        if first_series.dtype == pl.Boolean:
            logger.info(
                f"Creating pie chart '{plot_name}' in boolean mode (counting True values for each trace).")
            for trace_column in processed_traces:
                series = df.get_data(
                    get_data(trace_column),
                    filter=filter_data(
                        filter_col, filter_value) if filter_value else None,
                ).to_series()

                if series.is_empty() or series.null_count() == series.len():
                    continue  # Skip empty or all-null series

                if series.dtype == pl.Boolean:
                    true_count = series.sum()  # For boolean series, sum() counts True values
                    if true_count > 0:  # Only add slice if there are True values
                        values.append(true_count)
                        labels.append(trace_column)
                else:
                    logger.warning(
                        f"Trace '{trace_column}' in pie chart '{plot_name}' expected to be boolean (based on first trace) but is {series.dtype}. Skipping.")

        # Check if the data type of the first series is numeric
        elif first_series.dtype.is_numeric():
            logger.info(
                f"Creating pie chart '{plot_name}' in numeric default mode (summing each trace).")
            for trace_column in processed_traces:
                series = df.get_data(
                    get_data(trace_column),
                    filter=filter_data(
                        filter_col, filter_value) if filter_value else None,
                ).to_series()

                if series.is_empty() or series.null_count() == series.len():
                    continue  # Skip empty or all-null series

                if series.dtype.is_numeric():
                    values.append(series.sum())
                    labels.append(trace_column)
                else:
                    logger.warning(
                        f"Trace '{trace_column}' in pie chart '{plot_name}' expected to be numeric (based on first trace) but is {series.dtype}. Skipping.")
        else:
            logger.warning(
                f"Data type for pie chart '{plot_name}' (first trace: {first_series.dtype}) is not boolean or numeric. Cannot create pie chart in default mode.")
            __apply_default_layout(fig, plot_name)  # Create an empty chart
            return fig

        if not values:  # If all traces were skipped in the default mode
            logger.warning(
                f"No valid data to display in pie chart '{plot_name}' for default mode.")
            __apply_default_layout(fig, plot_name)
            return fig

    fig.add_pie(values=values, labels=labels, hole=0.3)
    __apply_default_layout(fig, plot_name)
    return fig
