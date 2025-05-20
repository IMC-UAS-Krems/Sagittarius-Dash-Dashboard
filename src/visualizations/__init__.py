from typing import Literal

from .registry import create_visualization, register_visualization
from .base import BaseVisualization
from .charts import BarChartVisualization, PieVisualization, GeoMapVisualization, XYVisualization, TimeSeriesVisualization

VisualizationType = Literal[
    "timeseries", "xy_chart", "bar_chart", "pie_chart", "geomap"
]

__all__ = [
    "create_visualization", 
    "register_visualization",
    "BaseVisualization",
    "VisualizationType"
]