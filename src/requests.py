from __future__ import annotations

import inspect
import logging
import re
from collections import namedtuple
from types import MethodType
from typing import Any, NewType, Protocol, TypeAlias

import orjson
import polars as pl
from dateutil.parser import parse as parse_date

from requests import get as r_get
from src.exceptions import ConfigError
from src.model import Datasource as Datasource_model

Url = NewType("Url", str)
Position = namedtuple("Position", ["lat", "lon"])

FiwareJson: TypeAlias = list[dict[str, Any]]

logger = logging.getLogger("dash_app")


class Filter(Protocol):
    """
    Filter will be called before any other pipeline steps and should not contain any data selection.
    DataFrame -> Filter -> Selector

    Example:
    ```
    custom_filter: Filter = lambda df: df.filter(pl.col("value") > 10)
    ```

    """

    def __call__(self, df: pl.DataFrame) -> pl.DataFrame: ...


class Selector(Protocol):
    """
    Selector will be called after the filter and should contain data selection.
    DataFrame -> Filter -> Selector

    Example:
    ```
    custom_selector: Selector = lambda df: df.select(pl.col("value"))
    ```
    """

    def __call__(self, df: pl.DataFrame) -> pl.DataFrame: ...


class FiwareDatasource:
    """Class representing a request to a data_source section in the config file"""

    def __init__(self, source: Datasource_model) -> None:
        self._source = source

        if "id" not in self._source.query.select:
            self._source.query.select.append("id")

        self._df: pl.DataFrame = self._request()
        logger.debug(self._df)
        logger.debug(self._df.columns)

    def get_data(
        self, selector: Selector, filter: Filter | None = None
    ) -> pl.DataFrame:
        df = self._df

        try:
            if filter:
                df = filter(df)

            return selector(df)

        except KeyError as e:
            logger.exception(e)

            sp = str(e).split("\n")
            column_name = sp[0].strip()
            df = sp[3].split(";")[0].strip()

            raise ConfigError(
                f"Column '{column_name}' not found in dataframe {df}",
                "Check if 'data_sources.measurements.<name>.query.select' has this key",
            )
        except Exception as e:
            logger.exception(e)

            raise ConfigError("An error occurred", str(e))

    @property
    def df(self) -> pl.DataFrame:
        return self._df

    def _request(self) -> pl.DataFrame:
        """Get data from the data source, parse it and save it as a polars DataFrame to `self.df`"""

        params = {"type": self._source.query.type}
        limit = 1000
        all_data = []
        offset = 0
        while True:
            params["limit"] = limit
            params["offset"] = offset
            resp = r_get(self._source.uri, params=params)
            chunk = orjson.loads(resp.content)
            if not chunk:
                break
            all_data.extend(chunk)
            offset += limit

        if not all_data:
            raise ValueError("No data received")

        data_list: list[list[Any]] = self._parse(all_data, self._source.query.select)
        df = pl.DataFrame(data_list, schema=self._source.query.select, orient="row", infer_schema_length=None)

        return df
    

    def _parse(self, data: FiwareJson, keys: list[str]) -> list[list[Any]]:
        """Parses data from the Fiware with the given data keys"""
        to_return = []
        parsers = self._get_parsers()

        for d in data:
            parsed = []
            for key in keys:
                item = d.get(key, None)

                if (
                    f"_parse_{key}" in parsers
                ):  # If there is a custom parser to parse an object
                    parsed.append(parsers[f"_parse_{key}"](item))

                elif isinstance(item, str):
                    parsed.append(item)

                elif (
                    isinstance(item, dict)
                    and "value" in item
                    and not isinstance(item["value"], dict)
                ):
                    parsed.append(self._parse_value(item["value"]))

                else:
                    parsed.append(None)
                    # raise ParserException(f"Parser for {key} not found\nValue: {item}")

            to_return.append(parsed)

        return to_return

    def _parse_location(
        self,
        location: dict[str, Any],
    ) -> Position | list[Position] | list[list[Position]]:
        match location["value"]["type"]:
            case "Point":
                return Position(
                    lon=location["value"]["coordinates"][0],
                    lat=location["value"]["coordinates"][1],
                )
            case "LineString":
                return [
                    Position(lon=lon, lat=lat)
                    for lon, lat in location["value"]["coordinates"]
                ]
            case "Polygon":
                return [
                    Position(lon=lon, lat=lat)
                    for lon, lat in location["value"]["coordinates"][0]
                ]
            # case "MultiPolygon":
            #     return [
            #         [Position(lon=p[0], lat=p[1]) for p in polygon[0]]
            #         for polygon in location["value"]["coordinates"]
            #     ]
            case "MultiPolygon":
                return [
                    [
                        [Position(lon=p[0], lat=p[1]) for p in ring]
                        for ring in polygon  # Iterate over ALL rings in this polygon
                    ]
                    for polygon in location["value"]["coordinates"]
                ]
            case "MultiPoint":
                return [
                    Position(lon=lon, lat=lat)
                    for lon, lat in location["value"]["coordinates"]
                ]
            case "MultiLineString":
                return [
                    [Position(lon=p[0], lat=p[1]) for p in line_string]
                    for line_string in location["value"]["coordinates"]
                ]
            case _:
                raise NotImplementedError

    def _parse_address(self, address: dict[str, Any]) -> str:
        return_address = ""
        address = address["value"]

        if "streetAddress" in address:
            return_address += (
                f"{address['streetAddress']}, "
                if "streerNr" not in address
                else f"{address['streetAddress']} {address['streetNr']}, "
            )

        if "postalCode" in address:
            return_address += address["postalCode"] + ", "

        if "addressLocality" in address:
            return_address += address["addressLocality"] + ", "

        if "addressRegion" in address:
            return_address += address["addressRegion"] + ", "

        if "addressCountry" in address:
            return_address += address["addressCountry"]

        return return_address

    def _parse_id(self, id_str: str) -> str:
        return re.sub(r"-(?:\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}|latest)", "", id_str)

    def _parse_dateObserved(self, date: str) -> str:
        return parse_date(date["value"])

    def _parse_value(self, value: Any) -> Any:
        """parse a generic value"""

        return value

    def _get_parsers(self) -> dict[str, MethodType]:
        """Get all non standard parsers"""

        return {
            name: obj
            for name, obj in inspect.getmembers(self)
            if isinstance(obj, MethodType) and name.startswith("_parse_")
        }


class DataSources:
    requests = {}

    @staticmethod
    def add_requests(sources: dict[str, Datasource_model]) -> None:
        for name, request in sources.items():
            DataSources.requests[name] = FiwareDatasource(request)

    @staticmethod
    def add_request(source_name: str, source: Datasource_model) -> None:
        DataSources.requests[source_name] = FiwareDatasource(source)

    @staticmethod
    def get_request(request_name: str) -> FiwareDatasource:
        return DataSources.requests[request_name]
