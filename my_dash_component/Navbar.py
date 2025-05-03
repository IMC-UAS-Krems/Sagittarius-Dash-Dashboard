# AUTO GENERATED FILE - DO NOT EDIT

import typing  # noqa: F401
from typing_extensions import TypedDict, NotRequired, Literal # noqa: F401
from dash.development.base_component import Component, _explicitize_args

ComponentType = typing.Union[
    str,
    int,
    float,
    Component,
    None,
    typing.Sequence[typing.Union[str, int, float, Component, None]],
]

NumberType = typing.Union[
    typing.SupportsFloat, typing.SupportsInt, typing.SupportsComplex
]


class Navbar(Component):
    """A Navbar component.


Keyword arguments:

- id (string; optional):
    Unique ID to identify this component in Dash callbacks.

- dashboard_name (string; required)

- dashboard_picture (string; required)

- dashboard_version (string; required)

- is_admin (boolean; default False)"""
    _children_props = []
    _base_nodes = ['children']
    _namespace = 'my_dash_component'
    _type = 'Navbar'


    def __init__(
        self,
        dashboard_name: typing.Optional[str] = None,
        dashboard_picture: typing.Optional[str] = None,
        dashboard_version: typing.Optional[str] = None,
        is_admin: typing.Optional[bool] = None,
        id: typing.Optional[typing.Union[str, dict]] = None,
        **kwargs
    ):
        self._prop_names = ['id', 'dashboard_name', 'dashboard_picture', 'dashboard_version', 'is_admin']
        self._valid_wildcard_attributes =            []
        self.available_properties = ['id', 'dashboard_name', 'dashboard_picture', 'dashboard_version', 'is_admin']
        self.available_wildcard_properties =            []
        _explicit_args = kwargs.pop('_explicit_args')
        _locals = locals()
        _locals.update(kwargs)  # For wildcard attrs and excess named props
        args = {k: _locals[k] for k in _explicit_args}

        for k in ['dashboard_name', 'dashboard_picture', 'dashboard_version']:
            if k not in args:
                raise TypeError(
                    'Required argument `' + k + '` was not specified.')

        super(Navbar, self).__init__(**args)

setattr(Navbar, "__init__", _explicitize_args(Navbar.__init__))
