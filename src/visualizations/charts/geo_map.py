import logging
import textwrap
from typing import Optional, List

import polars as pl
from plotly import graph_objects as go
from requests import Response
from requests import get as r_get

from src.model import GeoMap
from ..base import BaseVisualization
from ..registry import register_visualization
from ...requests import Selector

logger = logging.getLogger("dash_app")

type Coordinates = dict[str, float]


@register_visualization("geomap")
class GeoMapVisualization(BaseVisualization):
    
    def __init__(self, plot_name: str, plot_config: GeoMap):
        """
        Initialize the GeoMap visualization.
        
        Args:
            plot_name: Title of the plot
            plot_config: Configuration object containing source, traces, and area
        """
        super().__init__(plot_name, plot_config)
        self.area = plot_config.area

    def data_selector(self, path: str, subset: str = "id") -> Selector:
        """
        Create a selector that extracts unique values for a specific path.
        
        Args:
            path: Column name to select from the DataFrame
            subset: Column name to filter on (default: "id")
        Returns:
            A lambda function that selects unique values from the DataFrame, subset is used to specify the column to filter on
        """
        return lambda df: df.unique(subset=subset, maintain_order=True).select(
            pl.col(path)
        )

    def custom_data_selector(self, paths: List[str], subset: str = "id") -> Selector:
        """
        Create a selector that prepares custom data for hover tooltips.
        
        Args:
            paths: List of column names to select from the DataFrame
            subset: Column name to filter on (default: "id")
        Returns:
            A lambda function that selects and formats the data for hover
        """
        return lambda df: (
            df.unique(subset=subset, maintain_order=True)
            .select(paths)
            .cast(pl.Utf8)
            .fill_null("unknown")
            .with_columns(
                (pl.all().map_elements(lambda x: "<br>".join(textwrap.wrap(x, 40))))
            )
        )

    def get_map_center(self, area: str) -> Coordinates:
        """
        Get the center coordinates for the specified area.
        
        Args:
            area: Name of the area to center the map on
            
        Returns:
            Dictionary containing latitude and longitude
            
        Raises:
            ValueError: If the location cannot be found
        """
        result: Response = r_get(
            "https://nominatim.openstreetmap.org/search",
            params={"city": area, "format": "json", "limit": 1},
            headers={
                "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:132.0) Gecko/20100101 Firefox/132.0"
            },
        )

        if not result:
            raise ValueError(f"Could not find location for {area}")

        result_json: list[dict[str, int]] = result.json()
        location: Coordinates = {
            "lat": float(result_json[0]["lat"]),
            "lon": float(result_json[0]["lon"]),
        }
        return location

    def create(self, filter_col: str = "id", filter_value: Optional[str] = None) -> go.Figure:
        """
        Create the map visualization.
        
        Args:
            filter_col: Column name to filter on (default: "id")
            filter_value: Value to filter for (optional)
            
        Returns:
            Plotly Figure object containing the map
        """
        df = self.get_data(self.source)
        lat_lon = self.plot_config.traces[0]
        label = self.plot_config.traces[1]
        extra = self.plot_config.traces[2:]

        if "id" not in extra:
            extra.append("id")

        lat = (
            df.get_data(self.data_selector(lat_lon))
            .to_series()
            .map_elements(lambda x: x[0], return_dtype=pl.Float32)
        )
        lon = (
            df.get_data(self.data_selector(lat_lon))
            .to_series()
            .map_elements(lambda x: x[1], return_dtype=pl.Float32)
        )
        custom_data = df.get_data(self.custom_data_selector(extra)).rows()
        hover_text = df.get_data(self.data_selector(label)).to_series().to_list()

        fig = go.Figure(
            go.Scattermapbox(
                lat=lat,
                lon=lon,
                mode="markers",
                customdata=custom_data,
                hovertext=hover_text,
            )
        )
        
        fig.update_layout(
            mapbox_style="carto-positron",
            margin=dict(l=10, r=10, t=40, b=10),
            title=self.plot_name,
        )

        fig.update_traces(
            hovertemplate="<b>%{hovertext}</b><br><br>"
            + "<br>".join(
                [
                    "<b>" + key.capitalize() + "</b>: %{customdata[" + str(i) + "]}"
                    for i, key in enumerate(extra)
                ]
            )
            + "<extra></extra>"
        )

        if self.area:
            try:
                fig.update_layout(
                    mapbox=dict(
                        center=self.get_map_center(self.area),
                        zoom=10,
                    )
                )
            except ValueError as e:
                logger.error(f"Error setting map center: {e}")
                
        return fig