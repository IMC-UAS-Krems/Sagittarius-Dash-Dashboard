import logging
from typing import Optional, Dict, Any

from dash import Input, Output, callback
from plotly import graph_objects as go

from src.model import Panel
from .registry import create_visualization

logger = logging.getLogger("dash_app")

def make_plot_with_callback(
    plot_name: str,
    plot_config: Panel,
    comp_id: str,
    graph_id: str,
    geo_map_id: Optional[str] = None,
    filter_key: str = "id",
):
    """
    Makes a plot with callbacks to update it based on user interactions.
    
    Creates two potential callbacks:
    1. Updates when a component (like dropdown) value changes
    2. Updates when a point on a map is clicked (if geo_map_id is provided)
    
    Args:
        plot_name: Title of the plot
        plot_config: Configuration object for the plot
        comp_id: ID of the component that triggers updates (e.g., dropdown)
        graph_id: ID of the graph to update
        geo_map_id: Optional ID of a map that can trigger updates on click
        
    See:
        https://dash.plotly.com/basic-callbacks
    """
    visualization = create_visualization(plot_config.type, plot_name, plot_config)
    
    @callback(
        Output(component_id=graph_id, component_property="figure"),
        Input(component_id=comp_id, component_property="value"),
    )
    def update_from_input(input_value: str) -> go.Figure:
        """
        Update visualization when input component value changes.
        """
        if input_value:
            return visualization.create(filter_col=filter_key, filter_value=input_value)


        fig = go.Figure()
        return visualization.apply_default_layout(fig)

    if geo_map_id:
        @callback(
            Output(
                component_id=graph_id, component_property="figure", allow_duplicate=True
            ),
            Input(component_id=geo_map_id, component_property="clickData"),
            prevent_initial_call=True,
        )
        def update_from_map_click(geomap_input: Dict[str, Any]) -> go.Figure:
            """U
            pdate visualization when a point on the map is clicked.
            """
            if geomap_input and "points" in geomap_input and len(geomap_input["points"]) > 0:
                try:
                    filter_value = geomap_input["points"][0]["customdata"][-1]
                    return visualization.create(filter_col=filter_key, filter_value=filter_value)

                except (IndexError, KeyError) as e:
                    logger.warning(f"Error extracting filter value from map click: {e}")

            fig = go.Figure()
            return visualization.apply_default_layout(fig)