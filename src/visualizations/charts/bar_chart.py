from typing import Optional

import polars as pl
from plotly import graph_objects as go
from datetime import datetime

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
    
    def create(self,
               filter_col: str = "id",
               start_date: Optional[str] = None,
               end_date: Optional[str] = None,
               filter_value: Optional[str] = None
               ) -> go.Figure:
        """
        Create a bar chart visualization.
        
        Args:
            filter_col: Column name to filter on (default: "id")
            filter_value: Value to filter for (optional)
            
        Returns:
            Plotly Figure object containing the bar chart
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
        x_axis_col = "dateObserved"
        if x_axis_col not in traces:
            raise ValueError(f"Bar chart requires '{x_axis_col}' in traces")

        traces.remove(x_axis_col)
        if "id" in traces:
            traces.remove("id")

        for trace in traces:
            plot_df = (
                df.group_by(x_axis_col, maintain_order=True)
                .agg(pl.first(trace))
                .sort(x_axis_col)
            )

            if plot_df.select(pl.col(trace).is_null()).to_series().all():
                continue

            fig.add_bar(
                x=plot_df.get_column(x_axis_col),
                y=plot_df.get_column(trace),
                name=trace,
            )

        self.apply_default_layout(fig)
        return fig
