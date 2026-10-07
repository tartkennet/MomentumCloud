from audit_corporate_action_basis import adjustment_factor, convert_stock_row
import pytest


def test_successor_future_reverse_split_preserves_legal_one_to_one_ratio():
    # BREA basis excludes SLMT's later 1:10 reverse split.
    result = convert_stock_row({"open": 114.10}, 1.0, 0.0, 1.0, 10.0)
    assert result["open"] == pytest.approx(11.41)


def test_cash_and_stock_are_both_in_original_adjusted_units():
    result = convert_stock_row({"open": 100.0}, 0.5, 9.0, 2.0, 4.0)
    assert result["open"] == pytest.approx(43.0)


def test_equal_basis_preserves_price():
    assert convert_stock_row({"open": 80.0}, 1.0, 0.0, 0.5, 0.5)["open"] == 80.0


@pytest.mark.parametrize("price", [0.0, -1.0, float("nan")])
def test_invalid_basis_fails_closed(price):
    with pytest.raises(RuntimeError):
        adjustment_factor(price, 1.0)
