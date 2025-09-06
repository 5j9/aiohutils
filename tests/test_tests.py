from typing import TypedDict

from pydantic import ValidationError
from pytest import raises

from aiohutils.tests import validate_typed_dict


class ParametrizedGeneric(TypedDict):
    key: list[int]


def test_assert_dict_type_fails():
    with raises(ValidationError):
        validate_typed_dict({'key': ['1', '2']}, ParametrizedGeneric)


def test_assert_dict_type_parametrized_generic():
    validate_typed_dict({'key': [1, 2]}, ParametrizedGeneric)
