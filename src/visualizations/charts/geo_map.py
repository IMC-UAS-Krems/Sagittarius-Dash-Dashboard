import logging
from typing import Optional, List
from datetime import datetime

import polars as pl
from plotly import graph_objects as go
from requests import RequestException, Response
from requests import get as r_get

from src.model import GeoMap
from ..base import BaseVisualization
from ..registry import register_visualization

logger = logging.getLogger("dash_app")

type Coordinates = dict[str, float]


@register_visualization("geomap")
class GeoMapVisualization(BaseVisualization):

    def __init__(self, plot_name: str, plot_config: GeoMap):
        super().__init__(plot_name, plot_config)
        self.area = plot_config.area

    def get_map_center(self, area: str) -> Coordinates:
        try:
            result: Response = r_get(
                "https://nominatim.openstreetmap.org/search",
                params={"city": area, "format": "json", "limit": 1},
                headers={
                    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:132.0) Gecko/20100101 Firefox/132.0"
                },
                timeout=5,
            )
            result.raise_for_status()

            result_json: list = result.json()
            if not result_json:
                raise ValueError(f"No results found for {area}")

            location: Coordinates = {
                "lat": float(result_json[0]["lat"]),
                "lon": float(result_json[0]["lon"]),
            }
            return location
        except (RequestException, ValueError) as e:
            raise ValueError(f"Could not find location for {area}")


    def create(
        self,
        filter_value: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        filter_col: str = "id",
    ) -> go.Figure:

        df = self.get_data(self.source).df

        if start_date and end_date:
            start_dt = datetime.fromisoformat(start_date)
            end_dt = datetime.fromisoformat(end_date)
            df = df.filter(pl.col("dateObserved").is_between(start_dt, end_dt))

        unique_locations_df = df.unique(
                subset=["id"], keep="first", maintain_order=True)

        lat_lon_col = self.plot_config.traces[0]
        label_col = self.plot_config.traces[1]
        extra_cols = self.plot_config.traces[2:]
        if "id" not in extra_cols:
            extra_cols.append("id")

        selected_point_df = unique_locations_df.filter(
            pl.col(filter_col) == filter_value)
        other_points_df = unique_locations_df.filter(
            pl.col(filter_col) != filter_value)

        fig = go.Figure()

        if not other_points_df.is_empty():
            fig.add_trace(go.Scattermapbox(
                lat=other_points_df.get_column(lat_lon_col).list.get(0),
                lon=other_points_df.get_column(lat_lon_col).list.get(1),
                mode="markers",
                customdata=other_points_df.select(extra_cols).to_numpy(),
                hovertext=other_points_df.get_column(label_col),
                marker=go.scattermapbox.Marker(
                    size=12, color='blue', opacity=0.7),
                name='Other Locations'
            ))

        if not selected_point_df.is_empty():
            fig.add_trace(go.Scattermapbox(
                lat=selected_point_df.get_column(lat_lon_col).list.get(0),
                lon=selected_point_df.get_column(lat_lon_col).list.get(1),
                mode="markers",
                customdata=selected_point_df.select(extra_cols).to_numpy(),
                hovertext=selected_point_df.get_column(label_col),
                marker=go.scattermapbox.Marker(
                    size=20, color='red', opacity=1.0),
                name='Selected Location'
            ))

        fig.update_layout(
            mapbox_style="carto-positron",
            margin=dict(l=10, r=10, t=40, b=10),
            title=self.plot_name,
            showlegend=False
        )
        hovertemplate = "<b>%{hovertext}</b><br><br>" + "<br>".join(
            [f"<b>{key.capitalize()}:</b> %{{customdata[{i}]}}" for i,
            key in enumerate(extra_cols)]
        ) + "<extra></extra>"
        fig.update_traces(hovertemplate=hovertemplate)


        center_coords = {}
        zoom_level = 10  # default zoom

        lat_for_center = unique_locations_df.get_column(
            lat_lon_col).list.get(0)
        lon_for_center = unique_locations_df.get_column(
            lat_lon_col).list.get(1)

        if self.area:
            try:
                center_coords = self.get_map_center(self.area)
                zoom_level = 10
            except ValueError as e:
                logger.error(
                    f"Could not find '{self.area}'. Centering on data. Error: {e}")
                if not lat_for_center.is_empty():
                    center_coords = {
                        "lat": lat_for_center.mean(), "lon": lon_for_center.mean()}
        elif not lat_for_center.is_empty():
            center_coords = {
                "lat": lat_for_center.mean(), "lon": lon_for_center.mean()}

            if lat_for_center.n_unique() > 1:
                lat_span = lat_for_center.max() - lat_for_center.min()
                lon_span = lon_for_center.max() - lon_for_center.min()
                span = max(lat_span, lon_span)
                if span > 10:
                    zoom_level = 4 # state level zoom
                elif span > 1:
                    zoom_level = 7 # county level zoom
                elif span > 0.1:
                    zoom_level = 10 # city level zoom
                elif span > 0.01:
                    zoom_level = 13 # neighborhood level zoom
                else:
                    zoom_level = 15 # street level zoom
            else:
                zoom_level = 15

        if center_coords:
            fig.update_layout(
                mapbox=dict(
                    center=center_coords,
                    zoom=zoom_level,
                )
            )

        return fig
