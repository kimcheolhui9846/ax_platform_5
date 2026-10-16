"""mock_fill: JSON Schema 제약을 지키는 Mock 값과 재귀 스키마 처리."""
from datetime import date
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, Field

from app.providers.mock_fill import mock_instance


class Node(BaseModel):
    name: str
    children: list["Node"] = Field(default_factory=list)
    parent: "Node | None" = None


def test_recursive_schema_yields_minimal_instance():
    node = mock_instance(Node)
    assert node.name.startswith("[mock]")
    assert node.children == []
    assert node.parent is None


class Strings(BaseModel):
    long: str = Field(min_length=30)
    short: str = Field(max_length=3)
    exact: str = Field(min_length=4, max_length=4)


def test_string_length_constraints():
    obj = mock_instance(Strings)
    assert len(obj.long) >= 30
    assert len(obj.short) <= 3
    assert len(obj.exact) == 4


class Lists(BaseModel):
    many: list[str] = Field(min_length=3)
    none: list[str] = Field(max_length=0)
    capped: list[int] = Field(min_length=2, max_length=2)


def test_list_length_constraints():
    obj = mock_instance(Lists)
    assert len(obj.many) == 3
    assert obj.none == []
    assert len(obj.capped) == 2


class Numbers(BaseModel):
    at_least_ten: int = Field(ge=10)
    at_most_zero: int = Field(le=0)
    above_five: int = Field(gt=5)
    below_one: int = Field(lt=1)
    narrow: float = Field(gt=0, lt=0.1)
    from_two_and_half: float = Field(ge=2.5)
    between: int = Field(ge=3, le=4)


def test_number_bound_constraints():
    obj = mock_instance(Numbers)  # 제약을 어기면 model_validate가 여기서 실패한다
    assert obj.at_least_ten >= 10
    assert obj.at_most_zero <= 0
    assert obj.above_five > 5
    assert obj.below_one < 1
    assert 0 < obj.narrow < 0.1
    assert obj.from_two_and_half >= 2.5
    assert 3 <= obj.between <= 4


class Choices(BaseModel):
    fixed: Literal["only"]
    pick: Literal["a", "b"]


def test_const_and_enum():
    obj = mock_instance(Choices)
    assert (obj.fixed, obj.pick) == ("only", "a")


class Formats(BaseModel):
    day: date
    ident: UUID
    email: Annotated[str, Field(json_schema_extra={"format": "email"})]


def test_string_formats():
    obj = mock_instance(Formats)
    assert isinstance(obj.day, date)
    assert isinstance(obj.ident, UUID)
    assert "@" in obj.email
