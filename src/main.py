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
            children = []
            if grid_item.selector:
                children.append(grid_item.selector)
            children.append(
                dcc.Graph(className="w-full h-1/2 flex-1", id=grid_item.plot_id)
            )
            grid.append(my_dash_component.Container(children))

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
            dcc.Store(id="user-role-store"),
            html.Div(
                id="dummy-div", style={"visibility": "hidden", "whiteSpace": "nowrap"}
            ),
            my_dash_component.Navbar(
                id="sag_navbar",
                dashboard_name=dashboard.service.name,
                dashboard_picture="https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQoOIx-L--QvUSC1Q382HNcLEScprHukettiQ&s",
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
    
    @app.callback(
        Output("sag_navbar", "is_admin"),
        Input("sag_url", "pathname"),
        prevent_initial_call=True,
    )
    def update_navbar_role(_):
        from flask_login import current_user
        return current_user.is_authenticated and getattr(current_user, "role", "") == "admin"



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
