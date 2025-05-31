from typing import Optional
import logging

import polars as pl
from plotly import graph_objects as go

from ..base import BaseVisualization
from ..registry import register_visualization

logger = logging.getLogger("dash_app")


@register_visualization("pie_chart")
class PieVisualization(BaseVisualization):
    def create(self,
               filter_col: str = "id",
               filter_value: Optional[str] = None,
               external_filter=None
               ) -> go.Figure:
        """
        Create a pie chart visualization. This method generates a pie chart.
        Applies external_filter (e.g., date range) and specific filter_value before aggregation.

        Args:
            filter_col: Column name to filter on (default: "id").
            filter_value: Value to filter for (default: None).
            external_filter: A function to apply global filters like date range.
        Returns:
            A Plotly Figure object representing the pie chart.
        """

        fig = go.Figure()
        df = self.get_data(self.source).df

        if external_filter:
            df = external_filter(df)

        # Apply specific filter if provided
        if filter_value and filter_col in df.columns:
            df = df.filter(pl.col(filter_col) == filter_value)
            if df.is_empty():
                logger.warning(
                    f"PieChart: DataFrame became empty after applying specific filter: {filter_col}='{filter_value}'.")
                self.apply_default_layout(fig)
                return fig

        if df.is_empty():
            logger.warning(
                "PieChart: DataFrame is empty after all filters, before calculating sums.")
            self.apply_default_layout(fig)
            return fig

        logger.debug(f"PieChart: DataFrame for summation (head):\n{df.head()}")
        logger.debug(f"PieChart: DataFrame schema for summation:\n{df.schema}")

        # Ensure 'id' and 'dateObserved' are excluded from pie slices
        slice_values = []
        slice_labels = [
            t for t in self.plot_config.traces if t not in {"id", "dateObserved"}
        ]

        if not slice_labels:
            logger.warning(
                "PieChart: No traces identified for pie slices from plot_config after excluding 'id' and 'dateObserved'.")
            self.apply_default_layout(fig)
            return fig

        # Calculate the sum for each trace in slice_labels
        for trace_name in slice_labels:
            if trace_name not in df.columns:
                logger.warning(
                    f"PieChart: Trace '{trace_name}' for slice not found in DataFrame. Using 0 for this slice.")
                slice_values.append(0)
                continue

            current_sum = df.select(pl.col(trace_name).sum()).item()

            if current_sum is None:
                current_sum = 0
            slice_values.append(current_sum)

        fig.add_pie(values=slice_values, labels=slice_labels, hole=0.3)
        self.apply_default_layout(fig)
        return fig
