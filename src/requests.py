from __future__ import annotations

from src.model import Datasource
import polars as pl
from requests import get as r_get
import orjson
from .parser import parse
from typing import Any


class Datasources:
    """Class representing a request to a data_source section in the config file"""

    def __init__(self, source: Datasource) -> None:
        self.source = source

        if "id" not in self.source.query.select:
            self.source.query.select.append("id")

        self.df: pl.DataFrame = self._request()

    def _request(self) -> pl.DataFrame:
        """Get data from the data source, parse it and save it as a polars DataFrame to `self.df`"""

        params = {"type": self.source.query.type}
        params["limit"] = 1000  # type: ignore
        resp = r_get(self.source.uri, params=params)
        data = orjson.loads(resp.content)

        if not data:
            raise ValueError("No data received")

        data_list: list[list[Any]] = parse(data, self.source.query.select)

        return pl.DataFrame(data_list, schema=self.source.query.select)

    # def _convert_to_table(self) -> DataTable:
    #     return make_table(self.df)


class Requests:
    requests = {}

    @staticmethod
    def add_requests(sources: dict[str, Datasource]) -> None:
        for name, request in sources.items():
            Requests.requests[name] = Datasources(request)

    @staticmethod
    def add_request(source_name: str, source: Datasource) -> None:
        Requests.requests[source_name] = Datasources(source)

    @staticmethod
    def get_request(request_name: str) -> Datasources:
        return Requests.requests[request_name]
