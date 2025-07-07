from typing import Optional

from plotly import graph_objects as go
import polars as pl
from datetime import datetime

from ..base import BaseVisualization
from ..registry import register_visualization

@register_visualization("pie_chart")
class PieVisualization(BaseVisualization):
    def create(self,
               filter_col: str = "id",
               start_date: Optional[str] = None,
               end_date: Optional[str] = None,
               filter_value: Optional[str] = None
               ) -> go.Figure:
        """
        Create a pie chart visualization. This method generates a pie chart.
        
        Args:
            filter_col: Column name to filter on (default: "id").
            filter_value: Value to filter for (default: None).
        Returns:
            A Plotly Figure object representing the pie chart.
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

        
        values = []
        
        traces_to_sum = [
            t for t in self.plot_config.traces
            if t not in ["id", "dateObserved", filter_col]
        ]

        if "id" in traces_to_sum:
            traces_to_sum.remove("id")

        for trace in traces_to_sum:
            total = df.select(pl.col(trace).sum()).item()
            values.append(total)
            
        fig.add_pie(values=values, labels=traces_to_sum, hole=0.3)
        self.apply_default_layout(fig)
        return fig
