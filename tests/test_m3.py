from app.modules.m3_fares.rules import evaluate,select_fare,FARES
from app.values import instant,number
from app.errors import DomainError
import pytest
def test_real_fare_version(result): assert result["stages"][2]["rows"][0]["fare_version"]=="F2"
def test_new_version_boundary():
    "TRAP-23"
    assert select_fare(instant("2026-11-01T00:00:00+08:00"),FARES)["amount"]=="2.50"
def test_timezone_equal():
    "TRAP-11"
    assert select_fare(instant("2026-10-31T16:00:00Z"),FARES)["version"]=="F2"
def test_overlap_rejected():
    "TRAP-25"
    with pytest.raises(DomainError):select_fare(instant("2026-11-16T00:00:00Z"),FARES+[FARES[1]])
def test_thousands_and_fullwidth():
    "TRAP-06"
    assert number("１,２３４.５０")==number("1234.50")
def test_real_sentinel_quarantined(result):
    "TRAP-07"
    assert any(r["reason"]=="EMPTY_VALUE" for r in result["stages"][2]["quarantine"])
def test_naive_time_rejected():
    r=evaluate([{"event_time":"2026-11-16T08:00:00","reported":"2"}],{})
    assert r["quarantine"][0]["reason"]=="INVALID_TIME"
