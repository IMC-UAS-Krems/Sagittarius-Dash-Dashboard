from typing import Optional, Callable
import logging

import polars as pl
from plotly import graph_objects as go

from ..base import BaseVisualization
from ..registry import register_visualization

logger = logging.getLogger("dash_app")


@register_visualization("timeseries")
class TimeSeriesVisualization(BaseVisualization):

    def create(
        self,
        filter_col: str = "id",
        filter_value: Optional[str] = None,
        external_filter: Optional[Callable[[
            pl.DataFrame], pl.DataFrame]] = None
    ) -> go.Figure:
        fig = go.Figure()
        df_initial = self.get_data(self.source).df

        # Apply global filters if provided
        if df_initial.is_empty():
            logger.warning("TimeSeries: Initial DataFrame is empty.")
            self.apply_default_layout(fig)
            return fig

        df_filtered = df_initial
        if external_filter:
            df_filtered = external_filter(df_initial)
            if df_filtered.is_empty():
                logger.warning(
                    "TimeSeries: DataFrame empty after external (date) filter.")
                self.apply_default_layout(fig)
                return fig

        if "dateObserved" in df_filtered.columns and not df_filtered.is_empty():
            unique_dates_log = df_filtered["dateObserved"].dt.date(
            ).unique().sort().to_list()
            logger.info(
                f"TimeSeries: Unique dates after external_filter: {unique_dates_log}")

        # Apply specific filter if provided
        if filter_value and filter_col in df_filtered.columns:
            df_filtered = df_filtered.filter(
                pl.col(filter_col) == filter_value)
            if df_filtered.is_empty():
                logger.warning(
                    f"TimeSeries: DataFrame empty after specific filter: {filter_col}='{filter_value}'.")
                self.apply_default_layout(fig)
                return fig
        # If no data is available after filtering, return an empty figure with default layout
        if df_filtered.is_empty():
            logger.warning(
                "TimeSeries: DataFrame is empty before daily aggregation.")
            self.apply_default_layout(fig)
            return fig

        if "dateObserved" not in df_filtered.columns:
            logger.error(
                "TimeSeries: 'dateObserved' column missing for aggregation.")
            self.apply_default_layout(fig)
            return fig

        logger.debug(
            f"TimeSeries: DataFrame head before daily aggregation:\n{df_filtered.head()}")

        # Aggregate data by day using the mean of available data points
        traces_from_config = self.plot_config.traces.copy()
        y_value_traces = [
            t for t in traces_from_config if t not in {"dateObserved", "id"}]

        if not y_value_traces:
            logger.warning(
                "TimeSeries: No Y-value traces identified for daily aggregation from plot_config.")
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
                "TimeSeries: DataFrame is empty after daily aggregation.")
            self.apply_default_layout(fig)
            return fig

        logger.debug(
            f"TimeSeries: Aggregated daily DataFrame (head):\n{aggregated_df.head()}")

        x_axis_data = aggregated_df["chart_date"]

        # Create time series traces for each Y-value trace
        for trace_name in y_value_traces:
            if trace_name not in aggregated_df.columns:
                logger.warning(
                    f"TimeSeries: Trace '{trace_name}' not found in aggregated_df. Skipping.")
                continue

            y_series = aggregated_df[trace_name]
            fig.add_scatter(x=x_axis_data, y=y_series,
                            mode="lines", name=trace_name)

        self.apply_default_layout(fig)
        fig.update_xaxes(title_text="Date")

        return fig
