from typing import Optional

from plotly import graph_objects as go
import polars as pl
from datetime import datetime

from ..base import BaseVisualization
from ..registry import register_visualization


@register_visualization("xy_chart")
class XYVisualization(BaseVisualization):

    def create(
        self,
        filter_value: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        filter_col: str = "id",
    ) -> go.Figure:
        """
        Create a XY chart visualization.
        Args:
            filter_col: Column name to filter on (default: "id").
            filter_value: Value to filter for (default: None).
        Returns:
            A Plotly Figure object representing the XY chart.
        """
        fig = go.Figure()
        df = self.get_data(self.source).df

        filters = []
        if filter_value:
            filters.append(pl.col(filter_col) == filter_value)

        if start_date and end_date:
            start_dt = datetime.fromisoformat(start_date)
            end_dt = datetime.fromisoformat(end_date)
            filters.append(pl.col("dateObserved").is_between(start_dt, end_dt))

        if filters:
            combined_filter = filters[0]
            for f in filters[1:]:
                combined_filter = combined_filter & f
            df = df.filter(combined_filter)

        traces = self.plot_config.traces.copy()

        if len(traces) < 2:
            raise ValueError(
                "XY chart requires at least two traces (for X and Y axes).")

        x_axis_col = traces[0]
        y_axis_col = traces[1]

        fig.add_scatter(
            x=df.get_column(x_axis_col),
            y=df.get_column(y_axis_col),
            mode="markers",
            name=f"{y_axis_col} vs {x_axis_col}",
        )

        self.apply_default_layout(fig)
        fig.update_layout(xaxis_title=x_axis_col, yaxis_title=y_axis_col)

        return fig
