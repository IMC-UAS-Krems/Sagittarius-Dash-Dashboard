from typing import Optional

from plotly import graph_objects as go
import polars as pl
from datetime import datetime

from ..base import BaseVisualization
from ..registry import register_visualization

@register_visualization("timeseries")
class TimeSeriesVisualization(BaseVisualization):

    def create(
        self,
        filter_value: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        filter_col: str = "id",
    ) -> go.Figure:

        """
        Create a time series visualization.
        
        Args:
            filter_col: Column name to filter on (default: "id").
            filter_value: Value to filter for (default: None).
        Returns:
            A Plotly Figure object representing the time series visualization.
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

        df = df.sort("dateObserved")

        traces = self.plot_config.traces.copy()
        x_axis_col = "dateObserved"

        if "id" in traces:
            traces.remove("id")
        if x_axis_col in traces:
            traces.remove(x_axis_col)

        for trace in traces:
            if df.select(pl.col(trace).is_null()).to_series().all():
                continue

            fig.add_scatter(
                x=df.get_column(x_axis_col),
                y=df.get_column(trace),
                mode="lines",
                name=trace,
            )

        self.apply_default_layout(fig)
        return fig
