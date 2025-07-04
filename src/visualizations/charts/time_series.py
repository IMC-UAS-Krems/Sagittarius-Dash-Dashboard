from typing import Optional

from plotly import graph_objects as go

from ..base import BaseVisualization
from ..registry import register_visualization

@register_visualization("timeseries")
class TimeSeriesVisualization(BaseVisualization):

    def create(self, filter_col: str = "id", filter_value: Optional[str] = None) -> go.Figure:
        """
        Create a time series visualization.
        
        Args:
            filter_col: Column name to filter on (default: "id").
            filter_value: Value to filter for (default: None).
        Returns:
            A Plotly Figure object representing the time series visualization.
        """
        fig = go.Figure()
        df = self.get_data(self.source)
        
        traces = self.plot_config.traces.copy()
        
        if "id" in traces:
            traces.remove("id")
        
        dateObserved_index = traces.index("dateObserved")
        
        for i in range(len(traces)):
            if i == dateObserved_index:
                continue
                
            trace = traces[i]
            x = df.get_data(
                self.create_selector(traces[dateObserved_index]),
                filter=self.create_filter(filter_col, filter_value) if filter_value else None,
            ).to_series()
            
            y = df.get_data(
                self.create_selector(trace),
                filter=self.create_filter(filter_col, filter_value) if filter_value else None,
            ).to_series()
            
            if y.null_count() == y.len():
                continue
            
            fig.add_scatter(
                x=x,
                y=y,
                mode="lines",
                name=trace,
            )
            
        self.apply_default_layout(fig)
        return fig