from decimal import Decimal as D

import pytest

from app.inventory.models import MockOutcome, OrderLine, RejectReason, Supplier
from app.inventory.supplier import MockSupplier, ReplyStatus, get_supplier_provider
from app.main import create_app
from app.providers.mock import MockProvider

LINES = [OrderLine(item_id="it_a", quantity=D(10), unit_price=D("1000")), OrderLine(item_id="it_b", quantity=D(1), unit_price=D("15.50"))]


def supplier(outcome: MockOutcome) -> Supplier:
    return Supplier(name="상회", mock_outcome=outcome)


@pytest.mark.parametrize(
    ("outcome", "placed", "looked_up"),
    [
        (MockOutcome.ACCEPT, ReplyStatus.ACCEPTED, ReplyStatus.ACCEPTED),
        (MockOutcome.PRICE_CHANGED, ReplyStatus.REJECTED, ReplyStatus.REJECTED),
        (MockOutcome.OUT_OF_STOCK, ReplyStatus.REJECTED, ReplyStatus.REJECTED),
        (MockOutcome.UNKNOWN_THEN_ACCEPT, ReplyStatus.UNKNOWN, ReplyStatus.ACCEPTED),
    ],
)
def test_mock_outcomes(outcome, placed, looked_up):
    mock = MockSupplier()
    assert mock.place(supplier(outcome), "req-00000001", LINES, "서울").status is placed
    assert mock.lookup(supplier(outcome), "req-00000001", LINES).status is looked_up


def test_price_changed_reports_ten_percent_higher_prices():
    reply = MockSupplier().place(supplier(MockOutcome.PRICE_CHANGED), "req-00000001", LINES, "서울")
    assert reply.reason is RejectReason.PRICE_CHANGED
    assert reply.current_prices == {"it_a": D("1100.00"), "it_b": D("17.05")}


def test_out_of_stock_reason_and_accept_reference():
    mock = MockSupplier()
    assert mock.place(supplier(MockOutcome.OUT_OF_STOCK), "req-00000001", LINES, "서울").reason is RejectReason.OUT_OF_STOCK
    accepted = mock.place(supplier(MockOutcome.ACCEPT), "req-00000001", LINES, "서울")
    assert accepted.supplier_ref == "mock-req-00000001"  # 같은 요청은 같은 번호(결정적)
    assert accepted.reason is None and accepted.current_prices == {}


def test_factory_and_app_wiring():
    assert isinstance(get_supplier_provider("mock"), MockSupplier)
    with pytest.raises(ValueError):
        get_supplier_provider("real-shop")
    app = create_app(provider=MockProvider())
    assert isinstance(app.state.supplier, MockSupplier)
    assert app.state.llm is not None
    custom = MockSupplier()
    assert create_app(provider=MockProvider(), supplier=custom).state.supplier is custom
