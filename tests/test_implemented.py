import pytest
from pytest import fixture

import requests
from src.parser._parser import get_parsers

from ._helpers import expand_json_schema, get_all_keys

URLS_CONFIG = {
    "PointOfInterest": "https://raw.githubusercontent.com/smart-data-models/dataModel.PointOfInterest/master/PointOfInterest/schema.json",
}


@fixture(
    params=URLS_CONFIG.items(), ids=lambda item: item[0]
)  # ids for easier identification of tests
def schema(request):
    namespace, url = request.param
    response = requests.get(url)
    response.raise_for_status()
    return response.json(), namespace, url


def test_check_all_required_are_implemented(schema):
    poi_schema, namespace, url = schema
    full_schema = expand_json_schema(poi_schema)
    keys = get_all_keys(full_schema)[1]
    parsers = get_parsers()
    unimplemented = [key for key in keys if f"parse_{key}" not in parsers]
    if len(unimplemented) > 0:
        pytest.fail(
            f"Not all required keys are implemented: {unimplemented}. Namespace: {namespace}. URL: {url}"
        )


def test_check_everything_is_implemented(schema):
    poi_schema, namespace, url = schema
    keys = get_all_keys(expand_json_schema(poi_schema))[0]
    parsers = get_parsers()
    unimplemented = [key for key in keys if f"parse_{key}" not in parsers]
    if len(unimplemented) > 0:
        pytest.xfail(
            f"Not all keys are implemented: {unimplemented}. Namespace: {namespace}. URL: {url}"
        )
