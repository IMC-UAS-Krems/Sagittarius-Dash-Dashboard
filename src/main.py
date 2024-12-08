import logging

from asgiref.wsgi import WsgiToAsgi
from dash import Input, Output, dcc, html
from flask import redirect
from werkzeug.wrappers import Response as WerkzeugResponse

import my_dash_component

from . import env
from .config import Dashboard, create_dashboard
from .init_dash import app, server, setup

dashboard: Dashboard = None  # type: ignore


def create_grid() -> list[my_dash_component.Container | dcc.Graph]:
    """Create the html grid for the dashboard. This grid contains all visualizations"""

    grid = []
    for grid_item in dashboard.plots:
        if grid_item.with_callback:
            grid.append(
                my_dash_component.Container(
                    [
                        dcc.Graph(
                            className="w-full h-1/2 flex-1", id=grid_item.plot_id
                        ),
                    ]
                )
            )
        else:
            grid.append(
                dcc.Graph(
                    className="w-full h-full",
                    figure=grid_item.plot,
                    responsive=True,
                    id=grid_item.plot_id,
                )
            )

    for grid_item in dashboard.tables:
        grid.append(html.Div(className="w-full h-full pb-1.5", children=grid_item))

    return grid


def create_layout() -> list[my_dash_component.Container | dcc.Graph]:
    """Create the layout for the dashboard"""

    return html.Div(
        [
            dcc.Location(id="sag_url", refresh=False),
            html.Div(
                id="dummy-div", style={"visibility": "hidden", "whiteSpace": "nowrap"}
            ),
            my_dash_component.Navbar(
                id="sag_navbar",
                dashboard_name=dashboard.service.name,
                dashboard_picture="https://www.fh-krems.ac.at/fileadmin/imc/images/logos/imc-logo-web-preview.png",
                dashboard_version=str(dashboard.service.version),
            ),
            my_dash_component.Grid(
                create_grid(),
                hash=dashboard.hash,
                id="sag_grid",
                selector=dashboard.selector,
            ),
        ]
    )


def init_dash() -> None:
    """Initialize the dash app"""

    global dashboard
    dashboard = create_dashboard(env.URL_CONFIG)
    app.layout = create_layout

    # fit the longest selector
    app.clientside_callback(
        """
    function(options) {
        var longestText = '';
        options.forEach(option => {
            if (option.length > longestText.length) {
                longestText = option;
            }
        });

        var dummyDiv = document.getElementById('dummy-div');
        dummyDiv.innerText = longestText;
        var width = dummyDiv.offsetWidth;

        var dropdown = document.getElementById("sag-selector");
        dropdown.style.width = (width + 32) + 'px';  // Adding some padding
    }
    """,
        Output("dummy-div", "children"),
        [Input("sag-selector", "options")],
        prevent_initial_call=True,
    )


@server.route("/")
def index() -> WerkzeugResponse:
    return redirect("/dash/")


def create_server() -> WsgiToAsgi:
    """Entry point aka main function to create the server"""
    setup()
    init_dash()

    logger = logging.getLogger("dash_app")

    logger.info("Starting server on http://localhost:8000 ...")

    return WsgiToAsgi(server)  # this tries to make stuff async
