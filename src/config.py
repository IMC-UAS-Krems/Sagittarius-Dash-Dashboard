from __future__ import annotations

import logging
from hashlib import md5
from typing import Any, NamedTuple
from datetime import datetime, date

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
    plots: list[GridItem] = []

    df = DataSources.get_request(next(iter(data.values())).source).df

    if df.is_empty() or "dateObserved" not in df.columns or df["dateObserved"].null_count() == df.height:
        logger.error(
            "'dateObserved' column is empty or missing. Cannot set up DatePickerRange correctly.")
        current_d = date.today()
        initial_start_date = current_d
        initial_end_date = current_d
        min_date_allowed_for_picker = current_d
        max_date_allowed_for_picker = current_d

    else:
        min_datetime = df["dateObserved"].min()
        max_datetime = df["dateObserved"].max()

    min_date_allowed_for_picker = min_datetime.date()
    max_date_allowed_for_picker = max_datetime.date()
    initial_start_date = min_datetime.date()
    initial_end_date = max_datetime.date()

    date_range_picker = html.Div(
        dcc.DatePickerRange(
            id="sag-global-date-picker",
            start_date=initial_start_date,
            end_date=initial_end_date,
            min_date_allowed=min_date_allowed_for_picker,
            max_date_allowed=max_date_allowed_for_picker,
            display_format="YYYY-MM-DD",
            minimum_nights=0  # <-- Add this line
        ),
        className="flex-shrink basis-1/4",
    )

    for i, (plot_name, plot) in enumerate(data.items()):
        if isinstance(plot, GeoMap):
            plots.append(_parse_plots_config_map(plot_name, plot))
        else:
            plot_item, _ = _parse_plots_config_plot(
                plot_name, plot, i, need_map_selector=False
            )
            plots.append(plot_item)

    return plots, date_range_picker


def _parse_plots_config_map(plot_name: str, plot: GeoMap) -> GridItem:
    return GridItem(
        plot=create_visualization("geomap", plot_name, plot).create(),
        plot_id="sag-map",
    )


def _parse_plots_config_plot(
    plot_name: str, plot: Panel, i: int, need_map_selector: bool
) -> tuple[GridItem, html.Div | None]:
    filter_col = getattr(plot, "filter_by", None)
    has_filter = bool(filter_col)
    comp_id = f"sag-selector-{i}" if has_filter else None

    graph_id = f"sag-plot{i}"

    make_plot_with_callback(
        plot_name,
        plot,
        comp_id=comp_id,
        graph_id=graph_id,
        geo_map_id="sag-map" if need_map_selector else None,
        filter_key=filter_col or "id",
    )

    if filter_col:
        plot_selector = _create_selector(comp_id, plot.source, filter_col)
        return (
            GridItem(
                plot_id=graph_id,
                with_callback=True,
                selector=plot_selector,
            ),
            None,
        )
    else:
        return (
            GridItem(
                plot_id=graph_id,
                with_callback=True,
                selector=None,
            ),
            None,
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


def _create_selector(comp_id: str, source: str, filter_col: str):
    def selector() -> Selector:
        return lambda df: df.select(pl.col(filter_col))

    options = (
        DataSources.get_request(source)
        .get_data(selector())
        .to_series()
        .unique()
        .to_list()
    )
    return html.Div(
        dcc.Dropdown(options, options[0], id=comp_id),
        className="flex-shrink basis-1/4",
    )
