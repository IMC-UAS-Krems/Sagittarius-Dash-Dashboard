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


class Container(Component):
    """A Container component.


Keyword arguments:

- children (a list of or a singular dash component, string or number; required)

- id (string; optional):
    Unique ID to identify this component in Dash callbacks."""
    _children_props = []
    _base_nodes = ['children']
    _namespace = 'my_dash_component'
    _type = 'Container'


    def __init__(
        self,
        children: typing.Optional[ComponentType] = None,
        id: typing.Optional[typing.Union[str, dict]] = None,
        **kwargs
    ):
        self._prop_names = ['children', 'id']
        self._valid_wildcard_attributes =            []
        self.available_properties = ['children', 'id']
        self.available_wildcard_properties =            []
        _explicit_args = kwargs.pop('_explicit_args')
        _locals = locals()
        _locals.update(kwargs)  # For wildcard attrs and excess named props
        args = {k: _locals[k] for k in _explicit_args if k != 'children'}

        if 'children' not in _explicit_args:
            raise TypeError('Required argument children was not specified.')

        super(Container, self).__init__(children=children, **args)

setattr(Container, "__init__", _explicitize_args(Container.__init__))
