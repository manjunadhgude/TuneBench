from decimal import Decimal

import pytest

from tunebench.safe_calculator import calculate


@pytest.mark.parametrize(
    ("expr", "message", "expected"),
    [
        ("45/6", "Six pouches cost 45.00.", "7.5"),
        ("2*12.40+3*4.60", "Two lanterns at 12.40 and three hooks at 4.60.", "38.60"),
        ("min(84/2,35)", "Half of 84.00 capped at 35.00.", "35"),
        ("4*17.50*(1-20/100)/2", "Four items at 17.50, paid 20% less, refund half.", "28"),
        ("100", "Propose INR100.", "100"),
    ],
)
def test_grounded_calculations(expr, message, expected):
    assert calculate(expr, message) == Decimal(expected)


@pytest.mark.parametrize(
    "expr",
    ["__import__('os').system('echo unsafe')", "x+1", "2**100", "True", "999", "1/0", "[1,2]"],
)
def test_rejects_unapproved_code_or_values(expr):
    with pytest.raises((ValueError, SyntaxError)):
        calculate(expr, "Supplied prices are 1 and 2.")


def test_order_id_cannot_supply_an_arithmetic_operand():
    with pytest.raises(ValueError):
        calculate("999", "Order TB-999 cost 10.00.", "TB-999")
