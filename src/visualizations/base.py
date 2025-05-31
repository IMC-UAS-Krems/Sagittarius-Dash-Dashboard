from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Optional, Callable

import polars as pl
from plotly import graph_objects as go

from src.model import Panel
from ..requests import DataSources, Filter, Selector

logger = logging.getLogger("dash_app")


class BaseVisualization(ABC):
    """
    Base class for all visualizations.
    """

    def __init__(self, plot_name: str, plot_config: Panel):
        self.plot_name = plot_name
        self.plot_config = plot_config
        self.source = plot_config.source

    def get_data(self, name: str):
        """
        Get the data from the data source.
        """
        return DataSources.get_request(name)

    def apply_default_layout(self, fig: go.Figure):
        """
        Apply default layout to the figure.
        """
        fig.update_layout(
            title=self.plot_name,
            legend=dict(orientation="h", yanchor="bottom",
                        y=1.02, xanchor="right", x=1),
            showlegend=True,
            margin=dict(l=20, r=60, t=40, b=20),
        )
        return fig

    def create_filter(self, filter_col: str, filter_value: str) -> Filter:
        """
        Create a filter function.
        """
        return lambda df: df.filter(pl.col(filter_col) == filter_value)

    def create_selector(self, path: str) -> Selector:
        """
        Create a selector function.
        """
        return lambda df: df.select(pl.col(path))
    
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

    @abstractmethod
    def create(
        self,
        filter_col: str = "id",
        filter_value: Optional[str] = None,
        external_filter: Optional[Callable[[
            pl.DataFrame], pl.DataFrame]] = None,
    ) -> go.Figure:
        """
        Create the visualization.
        - filter_col: column to filter on (e.g., 'id')
        - filter_value: value for the column
        - external_filter: a global filter function (e.g., date range)
        """
        pass
