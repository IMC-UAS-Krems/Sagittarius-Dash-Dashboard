from typing import Optional

import polars as pl
from plotly import graph_objects as go

from ..base import BaseVisualization
from ..registry import register_visualization
from ...requests import Filter, Selector

@register_visualization("bar_chart")
class BarChartVisualization(BaseVisualization):
    
    def create_selector(self, path: str) -> Selector:
        """
        Create a selector function to extract data for a specific column.
        Arg: path: Column name to select from the df.
        """
        return lambda df: df.select(pl.col(path))
    
    def create_filter(self, filter_col: str, filter_value: str) -> Filter:
        """
        Filter function to filter data by a specific column value.
        Arg: filter_col: Column name to filter on.
        filter_value: Value to filter for.
        
        Args:
            filter_col: Column name to filter on.
            filter_value: Value to filter for.
        Returns:
            Filter lambda function that filters the data.
        """
        return lambda df: df.filter(pl.col(filter_col) == filter_value)
    
    def create_filter_with_agg(self, filter_col: str, filter_value: str, agg_col: str, group_by_value: str = "dateObserved") -> Filter:
        """
        Create a filter function with aggregation.
        
        This filter groups data by a specific value and aggregates it using
        the first value of the specified column.
        
        Args:
            filter_col: Column name to filter on.
            filter_value: Value to filter for.
            agg_col: Column name to aggregate.
            group_by_value: Column name to group by (default: "DateObserved").
        Returns:
            Filter lambda function that filters and aggregates the data.
        """
        return (
            lambda df: df.filter(pl.col(filter_col) == filter_value)
            .group_by(group_by_value, maintain_order=True)
            .agg(pl.first(agg_col))
            .sort(group_by_value)
        )
    
    def create(self, filter_col: str = "id", filter_value: Optional[str] = None) -> go.Figure:
        """
        Create a bar chart visualization.
        
        Args:
            filter_col: Column name to filter on (default: "id")
            filter_value: Value to filter for (optional)
            
        Returns:
            Plotly Figure object containing the bar chart
        """
        fig = go.Figure()
        df = self.get_data(self.source)
        
        traces = self.plot_config.traces.copy()
        
        if "id" in traces:
            traces.remove("id")
        
        try:
            dateObserved_index = traces.index("dateObserved")
        except ValueError:
            raise ValueError("Bar chart requires 'dateObserved' in traces")
        
        for i in range(len(traces)):
            if i == dateObserved_index:
                continue
                
            trace = traces[i]
            
            x = (
                df.get_data(
                    self.create_selector(traces[dateObserved_index]),
                    filter=self.create_filter(filter_col, filter_value) if filter_value else None,
                )
                .to_series()
                .sort()
            )
            
            y = df.get_data(
                self.create_selector(trace),
                filter=self.create_filter_with_agg(filter_col, filter_value, trace)
                if filter_value
                else None,
            ).to_series()
            
            fig.add_bar(
                x=x,
                y=y,
                name=trace,
            )
        
        self.apply_default_layout(fig)
        return fig