from app.modules.m5_discounts.rules import evaluate
from app.errors import DomainError
from decimal import Decimal
import pytest
def ride(id,minute,route="01",base="2.50"):
    return {"event_id":str(id),"card":"0001","business_day":"2026-11-16","at":f"2026-11-16T{8+minute//60:02d}:{minute%60:02d}:00Z","route":route,"base_fare":base}
def test_real_day_cap(result): assert result["stages"][4]["metrics"]["expected_total"]=="48.00"
def test_exact_window_excluded():
    "TRAP-23 半开换乘窗"
    r=evaluate([ride(1,0),ride(2,60,"02")],{})["rows"];assert r[1]["transfer_discount"]=="0.00"
def test_within_window_discount(): assert evaluate([ride(1,0),ride(2,59,"02")],{})["rows"][1]["expected"]=="1.50"
def test_same_route_no_transfer(): assert evaluate([ride(1,0),ride(2,10)],{})["rows"][1]["expected"]=="2.50"
def test_zero_paid_not_anchor():
    r=evaluate([ride(1,0,base="1"),ride(2,30,"02",base="1"),ride(3,61,"03",base="1")],{})["rows"]
    assert r[1]["expected"]=="0.00" and r[2]["transfer_discount"]=="0.00"
def test_discount_before_cap_conservation():
    "TRAP-10 Decimal守恒"
    r=evaluate([ride(1,0),ride(2,10,"02"),ride(3,20,"03"),ride(4,90)],{})["rows"]
    assert sum(Decimal(x["expected"]) for x in r)==Decimal("6")
    assert all(Decimal(x["base_fare"])==Decimal(x["expected"])+Decimal(x["transfer_discount"])+Decimal(x["cap_discount"]) for x in r)
def test_negative_parameter_rejected():
    with pytest.raises(DomainError):evaluate([],{"parameters":{"daily_cap":"-1"}})
def test_input_order_invariant():
    rows=[ride(1,0),ride(2,10,"02")];assert evaluate(rows,{})["rows"]==evaluate(list(reversed(rows)),{})["rows"]
