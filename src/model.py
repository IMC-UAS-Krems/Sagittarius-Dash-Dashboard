from typing import Annotated, Literal, TypeAlias

from pydantic import BaseModel, ConfigDict, Field


class Version(BaseModel):
    major: int
    minor: int
    patch: int

    def __str__(self):
        return f"{self.major}.{self.minor}.{self.patch}"


class Service(BaseModel):
    name: str
    scope: str  # Fiware scope
    version: Version


class Query(BaseModel):
    type: str
    select: list[str]


class Datasource(BaseModel):
    provider: str  # Fiware
    type: str  # ignore
    uri: str
    query: Query


class GeoMap(BaseModel):
    type: Literal["geomap"]
    source: str
    traces: list[str] = Field(alias="data")  # TODO: fix this
    area: str | None = Field(None)  # center coordinates (https://nominatim.org/)
    color_by: str | None = Field(None)  # color by field


class PieChart(BaseModel):
    type: Literal["pie_chart"]
    source: str
    traces: list[str]
    pie_chart_type: str | None = Field(None)


class BarChart(BaseModel):
    type: Literal["bar_chart"]
    source: str
    traces: list[str]  # first trace is x axis


class TimeSeries(BaseModel):
    type: Literal["timeseries"]
    source: str
    traces: list[str]  # first trace is x axis


class XYChart(BaseModel):
    type: Literal["xy_chart"]
    source: str
    traces: list[str]  # first trace is x axis


Panel: TypeAlias = PieChart | TimeSeries | BarChart | GeoMap | XYChart


class Application(BaseModel):
    type: str
    layout: str
    roles: list[str]
    visualizations: dict[str, Annotated[Panel, Field(discriminator="type")]]


class Deployment(BaseModel):
    uri: str
    port: int
    type: str


class Config(BaseModel):
    model_config = ConfigDict(strict=True)
    service: Service
    data_sources: dict[str, Datasource]
    application: Application
    deployment: dict[str, dict[str, Deployment]]
