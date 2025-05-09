from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Optional

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
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
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
    
    @abstractmethod
    def create(self, filter_col: str = "id", filter_value: Optional[str] = None) -> go.Figure:
        """
        Create the visualization.
        """
        pass