from typing import Optional

import polars as pl
from plotly import graph_objects as go

from ..base import BaseVisualization
from ..registry import register_visualization
from ...requests import Filter, Selector
import logging

logger = logging.getLogger("dash_app")


@register_visualization("bar_chart")
class BarChartVisualization(BaseVisualization):
    def create(
        self,
        filter_col: str = "id",
        filter_value: Optional[str] = None,
        external_filter=None
    ) -> go.Figure:
        """
        Create a bar chart visualization.
        If a date range is provided via external_filter, it will display daily aggregated data
        using the mean of available data points for each day.

        Args:
            filter_col: Column name to filter on (default: "id")
            filter_value: Value to filter for (optional)
            external_filter: A function to apply global filters like date range.

        Returns:
            Plotly Figure object containing the bar chart
        """
        
        fig = go.Figure()
        df = self.get_data(self.source).df

        # Apply global filters if provided
        if external_filter:
            df = external_filter(df)

        # Apply specific filter if provided
        if filter_value and filter_col in df.columns:
            df = df.filter(pl.col(filter_col) == filter_value)
            if df.is_empty():
                logger.warning(
                    f"DataFrame became empty after applying specific filter: {filter_col}='{filter_value}'.")
                self.apply_default_layout(fig)
                return fig

        # If no data is available after filtering, return an empty figure with default layout
        if df.is_empty():
            logger.warning(
                "DataFrame is empty before daily aggregation processing.")
            self.apply_default_layout(fig)
            return fig

        logger.debug(f"DataFrame head before daily aggregation:\n{df.head()}")
        logger.debug(
            f"DataFrame schema before daily aggregation:\n{df.schema}")

        traces_from_config = self.plot_config.traces.copy()

        if "dateObserved" not in traces_from_config:
            raise ValueError(
                "Bar chart requires 'dateObserved' in traces configuration.")
        # remove 'dateObserved' and 'id' from traces for Y-axis plotting
        value_traces_for_y_plotting = [
            t for t in traces_from_config if t not in {"dateObserved", "id"}
        ]

        if not value_traces_for_y_plotting:
            logger.warning(
                "No value traces identified for Y-axis (e.g., NOx, O3) from plot_config.traces after excluding 'dateObserved' and 'id'.")
            self.apply_default_layout(fig)
            return fig

        aggregated_df = (
            df.with_columns(
                pl.col("dateObserved").dt.date().alias("chart_date")
            )
            .group_by("chart_date", maintain_order=True)
            .agg([pl.mean(trace).alias(trace) for trace in value_traces_for_y_plotting])
            .sort("chart_date")
        )

        if aggregated_df.is_empty():
            logger.warning("DataFrame is empty after daily aggregation.")
            self.apply_default_layout(fig)
            return fig

        logger.debug(
            f"Aggregated daily DataFrame head (using mean):\n{aggregated_df.head()}")
        logger.debug(
            f"Aggregated daily DataFrame schema:\n{aggregated_df.schema}")
        
        # Create bar chart traces for each value trace
        x_axis_data_daily = aggregated_df["chart_date"]

        # Check if the expected traces are present in the aggregated DataFrame
        for trace_name in value_traces_for_y_plotting:
            if trace_name in aggregated_df.columns:
                y_axis_data_daily = aggregated_df[trace_name]
                fig.add_bar(x=x_axis_data_daily,
                            y=y_axis_data_daily, name=trace_name)
            else:
                logger.warning(
                    f"Trace '{trace_name}' was expected but not found in aggregated_df columns: {aggregated_df.columns}")

        self.apply_default_layout(fig)
        fig.update_xaxes(title_text="Date")

        return fig
