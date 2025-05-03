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


class Grid(Component):
    """A Grid component.


Keyword arguments:

- id (string; optional):
    Unique ID to identify this component in Dash callbacks.

- graths (list of a list of or a singular dash component, string or numbers; required)

- hash (string; required)

- selector (a list of or a singular dash component, string or number; required)"""
    _children_props = ['graths', 'selector']
    _base_nodes = ['graths', 'selector', 'children']
    _namespace = 'my_dash_component'
    _type = 'Grid'


    def __init__(
        self,
        graths: typing.Optional[typing.Sequence[ComponentType]] = None,
        selector: typing.Optional[ComponentType] = None,
        hash: typing.Optional[str] = None,
        id: typing.Optional[typing.Union[str, dict]] = None,
        **kwargs
    ):
        self._prop_names = ['id', 'graths', 'hash', 'selector']
        self._valid_wildcard_attributes =            []
        self.available_properties = ['id', 'graths', 'hash', 'selector']
        self.available_wildcard_properties =            []
        _explicit_args = kwargs.pop('_explicit_args')
        _locals = locals()
        _locals.update(kwargs)  # For wildcard attrs and excess named props
        args = {k: _locals[k] for k in _explicit_args}

        for k in ['graths', 'hash', 'selector']:
            if k not in args:
                raise TypeError(
                    'Required argument `' + k + '` was not specified.')

        super(Grid, self).__init__(**args)

setattr(Grid, "__init__", _explicitize_args(Grid.__init__))
