from __future__ import annotations

import logging
from hashlib import md5
from typing import Any, NamedTuple

import polars as pl
from dash import dcc, html
from plotly.graph_objs import Figure

from requests import get as r_get
from src.model import Config, GeoMap, Panel, Service
from src.requests import DataSources, Selector

from .exceptions import ConfigError
from .visualizations.registry import create_visualization
from .visualizations.callbacks import make_plot_with_callback


logger = logging.getLogger("dash_app")
type Url = str


class GridItem(NamedTuple):
    """Class representing a grid item in the dashboard"""

    plot: Figure | None = None  # visualization
    selector: dcc.Dropdown | None = None  # dropdown in the dashboard
    plot_id: str | None = None  # id of the plot
    with_callback: bool = False  # whether the plot has a callback


class Dashboard(NamedTuple):
    service: Service | None
    plots: list[GridItem]
    tables: list[GridItem]
    selector: html.Div | None
    hash: str


def create_dashboard(config_url: Url) -> Dashboard:
    logger.info("Initializing app...")

    app_config_str = r_get(config_url).text

    app_config: Config = Config.model_validate_json(app_config_str)

    logger.debug(f"Config file loaded: {app_config=}")

    plots = []
    tables = []
    selector = None
    hash = _calc_hash("empty")
    service = app_config.service

    try:
        DataSources.add_requests(app_config.data_sources)
        plots, selector = _parse_plots_config(
            app_config.application.visualizations)
        hash = _calc_hash(str(app_config.application.visualizations))

    except Exception as e:
        if isinstance(e, ConfigError):
            e.log()
        else:
            logger.exception(str(e))

    return Dashboard(service, plots, tables, selector, hash)


def _parse_plots_config(
    data: dict[str, Panel],
) -> tuple[list[GridItem], html.Div | None]:
    plots = []
    selectors = []

    need_dropdown_selector = any(
        plot.type in ("timeseries", "xy_chart", "bar_chart", "pie_chart")
        for plot in data.values()
    )
    need_map_selector = (
        any(isinstance(plot, GeoMap) for plot in data.values())
        and need_dropdown_selector
    )

    id_selector_added = False
    for i, (plot_name, plot) in enumerate(data.items()):
        try:
            if isinstance(plot, GeoMap):
                plot_item = _parse_plots_config_map(plot_name, plot)
            else:
                plot_item, sel = _parse_plots_config_plot(
                    plot_name, plot, i, need_map_selector
                )
                if not id_selector_added:
                    selectors.append(sel)
                    id_selector_added = True

            plots.append(plot_item)

        except KeyError as e:
            raise ConfigError(f"Missing key {e} in plot {plot_name}")

        except IndexError:
            raise ConfigError(
                f"Invalid config file. Chech if '{plot_name}.traces' has at least 2 items. {plot.traces=}",
                "Please check your config file.",
            )

    df = DataSources.get_request(next(iter(data.values())).source).df

    min_date = df["dateObserved"].min()
    max_date = df["dateObserved"].max()

    date_range_picker = html.Div(
        [
            dcc.DatePickerRange(
                id="sag-global-date-picker",
                start_date=min_date,
                end_date=max_date,
                min_date_allowed=min_date,
                max_date_allowed=max_date,
                display_format="DD-MM-YYYY",
            ),
        ],
        className="w-min",
    )
    selectors.append(date_range_picker)
    return plots, html.Div(selectors, className="w-full") if need_dropdown_selector else None


def _parse_plots_config_map(plot_name: str, plot: GeoMap) -> GridItem:
    return GridItem(
        plot=create_visualization("geomap", plot_name, plot).create(),
        plot_id="sag-map",
    )


def _parse_plots_config_plot(
    plot_name: str, plot: Panel, i: int, need_map_selector: bool
) -> tuple[GridItem, html.Div | None]:
    comp_id = "sag-selector"
    graph_id = f"sag-plot{i}"

    make_plot_with_callback(
        plot_name,
        plot,
        comp_id=comp_id,
        graph_id=graph_id,
        geo_map_id="sag-map" if need_map_selector else None,
    )
    return (
        GridItem(
            plot_id=graph_id,
            with_callback=True,
        ),
        _create_selector(comp_id, plot.source),
    )


def _calc_hash(_to_hash: str | dict[str, Any]) -> str:
    """
    Calculates the hash of visualizations config part

    :param _to_hash: config str to be hashed
    :return: MD5 hash
    """

    if isinstance(_to_hash, dict):
        _to_hash = str(_to_hash)

    return md5(_to_hash.encode()).hexdigest()


def _create_selector(comp_id: str, source: str):
    def id_selector() -> Selector:
        return lambda df: df.select(pl.col("id"))

    options = (
        DataSources.get_request(source)
        .get_data(id_selector())
        .to_series()
        .unique()
        .to_list()
    )
    return html.Div(
        [
            dcc.Dropdown(options, options[0], id=comp_id),
        ],
        className="w-3/5 mb-4"
    )
