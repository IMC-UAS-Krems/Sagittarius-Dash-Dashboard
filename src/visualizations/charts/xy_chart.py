from typing import Optional, Callable
import logging

import polars as pl
from plotly import graph_objects as go

from ..base import BaseVisualization
from ..registry import register_visualization

logger = logging.getLogger("dash_app")


@register_visualization("xy_chart")
class XYVisualization(BaseVisualization):

    def create(
        self,
        filter_col: str = "id",
        filter_value: Optional[str] = None,
        external_filter: Optional[Callable[[
            pl.DataFrame], pl.DataFrame]] = None
    ) -> go.Figure:
        fig = go.Figure()
        df_initial = self.get_data(self.source).df

        if df_initial.is_empty():
            logger.warning("XYChart: Initial DataFrame is empty.")
            self.apply_default_layout(fig)
            return fig

        # Apply external filter if provided
        df_filtered = df_initial
        if external_filter:
            df_filtered = external_filter(df_initial)
            if df_filtered.is_empty():
                logger.warning(
                    "XYChart: DataFrame empty after external (date) filter.")
                self.apply_default_layout(fig)
                return fig

        if "dateObserved" in df_filtered.columns and not df_filtered.is_empty():
            unique_dates_log = df_filtered["dateObserved"].dt.date(
            ).unique().sort().to_list()
            logger.info(
                f"XYChart: Unique dates after external_filter: {unique_dates_log}")
            
        # If a specific filter is provided, apply it
        if filter_value and filter_col in df_filtered.columns:
            df_filtered = df_filtered.filter(
                pl.col(filter_col) == filter_value)
            if df_filtered.is_empty():
                logger.warning(
                    f"XYChart: DataFrame empty after specific filter: {filter_col}='{filter_value}'.")
                self.apply_default_layout(fig)
                return fig

        if df_filtered.is_empty():
            logger.warning(
                "XYChart: DataFrame is empty before daily aggregation.")
            self.apply_default_layout(fig)
            return fig

        if "dateObserved" not in df_filtered.columns:
            logger.error(
                "XYChart: 'dateObserved' column missing (expected for X-axis and aggregation).")
            self.apply_default_layout(fig)
            return fig

        logger.debug(
            f"XYChart: DataFrame head before daily aggregation:\n{df_filtered.head()}")

        traces_from_config = self.plot_config.traces.copy()

        # Identify Y-value traces for daily aggregation
        y_value_traces = [
            t for t in traces_from_config if t not in {"dateObserved", "id"}]

        if not y_value_traces:
            logger.warning(
                "XYChart: No Y-value traces identified for daily aggregation from plot_config.")
            self.apply_default_layout(fig)
            return fig

        aggregated_df = (
            df_filtered.with_columns(
                pl.col("dateObserved").dt.date().alias("chart_date")
            )
            .group_by("chart_date", maintain_order=True)
            .agg([pl.mean(trace).alias(trace) for trace in y_value_traces])
            .sort("chart_date")
        )

        if aggregated_df.is_empty():
            logger.warning(
                "XYChart: DataFrame is empty after daily aggregation.")
            self.apply_default_layout(fig)
            return fig

        logger.debug(
            f"XYChart: Aggregated daily DataFrame (head):\n{aggregated_df.head()}")

        x_axis_data = aggregated_df["chart_date"]

        # Add traces for each Y-value
        for trace_name in y_value_traces:
            if trace_name not in aggregated_df.columns:
                logger.warning(
                    f"XYChart: Trace '{trace_name}' not found in aggregated_df. Skipping.")
                continue

            y_series = aggregated_df[trace_name]
            fig.add_scatter(x=x_axis_data, y=y_series,
                            mode="markers", name=trace_name)

        self.apply_default_layout(fig)
        fig.update_xaxes(title_text="Date")

        return fig
