import logging
from typing import Optional, Dict, Any, Callable

from dash import Input, Output, callback
from plotly import graph_objects as go
from datetime import datetime

import polars as pl
from src.model import Panel
from .registry import create_visualization

logger = logging.getLogger("dash_app")


def make_plot_with_callback(
    plot_name: str,
    plot_config: Panel,
    comp_id: Optional[str],
    graph_id: str,
    geo_map_id: Optional[str] = None,
    filter_key: str = "id",
):
    visualization = create_visualization(
        plot_config.type, plot_name, plot_config)

    if comp_id:

        @callback(
            Output(graph_id, "figure"),
            Input(comp_id, "value"),
            Input("sag-global-date-picker", "start_date"),
            Input("sag-global-date-picker", "end_date"),
        )
        def update_with_dropdown_and_date(input_value, start_date, end_date):
            def external_filter(df: pl.DataFrame) -> pl.DataFrame:
                if not start_date or not end_date:
                    logger.warning(
                        "External filter called with missing start_date or end_date. No date filter applied.")
                    return df
                try:
                    start_date_obj = datetime.fromisoformat(start_date).date()
                    end_date_obj = datetime.fromisoformat(end_date).date()
                except ValueError as e:
                    logger.error(
                        f"Error parsing date strings in external_filter: start='{start_date}', end='{end_date}'. Error: {e}")
                    return df

                logger.debug(
                    f"Applying date filter: dateObserved dates >= {start_date_obj} AND <= {end_date_obj}")

                df_filtered = df.filter(
                    (pl.col("dateObserved").dt.date() >= start_date_obj) &
                    (pl.col("dateObserved").dt.date() <= end_date_obj)
                )

                log_msg_suffix = " (comp_id branch)" if comp_id else " (no comp_id branch)"
                logger.debug(
                    f"Shape after date filtering{log_msg_suffix}: original {df.shape}, filtered {df_filtered.shape}. Unique dates in filtered: {df_filtered['dateObserved'].dt.date().unique().sort().to_list() if not df_filtered.is_empty() and 'dateObserved' in df_filtered.columns else 'N/A or empty'}")
                return df_filtered

            if input_value:
                return visualization.create(
                    filter_col=filter_key,
                    filter_value=input_value,
                    external_filter=external_filter,
                )

            return visualization.apply_default_layout(go.Figure())

    else:
        @callback(
            Output(component_id=graph_id, component_property="figure"),
            Input("sag-global-date-picker", "start_date"),
            Input("sag-global-date-picker", "end_date"),
        )
        def update_from_date_range(start_date: str, end_date: str) -> go.Figure:
            def external_filter(df: pl.DataFrame) -> pl.DataFrame:
                if not start_date or not end_date:
                    logger.warning(
                        "External filter called with missing start_date or end_date. No date filter applied.")
                    return df

                try:
                    start_date_obj = datetime.fromisoformat(start_date).date()
                    end_date_obj = datetime.fromisoformat(end_date).date()
                except ValueError as e:
                    logger.error(
                        f"Error parsing date strings in external_filter: start='{start_date}', end='{end_date}'. Error: {e}")
                    return df
                logger.debug(
                    f"Applying date filter: dateObserved >= {start_date_obj} AND dateObserved <= {end_date_obj}")

                df_filtered = df.filter(
                    (pl.col("dateObserved").dt.date() >= start_date_obj) &
                    (pl.col("dateObserved").dt.date() <= end_date_obj)
                )

                logger.debug(
                    f"Shape after date filtering: original {df.shape}, filtered {df_filtered.shape}")
                return df_filtered

            return visualization.create(
                filter_col="id",
                filter_value=None,
                external_filter=external_filter
            )

    if geo_map_id:
        @callback(
            Output(graph_id, "figure", allow_duplicate=True),
            Input(geo_map_id, "clickData"),
            prevent_initial_call=True,
        )
        def update_from_map_click(geomap_input: Dict[str, Any]) -> go.Figure:
            if geomap_input and "points" in geomap_input and len(geomap_input["points"]) > 0:
                try:
                    filter_value = geomap_input["points"][0]["customdata"][-1]
                    return visualization.create(filter_col=filter_key, filter_value=filter_value)
                except (IndexError, KeyError) as e:
                    logger.warning(
                        f"Error extracting filter value from map click: {e}")

            fig = go.Figure()
            return visualization.apply_default_layout(fig)
