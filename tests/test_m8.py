from decimal import Decimal
import pytest
from app.errors import DomainError
from app.modules.m8_fund.rules import evaluate, RULING, largest_remainder
from app import store
from app.pipeline import calculate, execute, load_sample


def claim(event_id, route="01", due="1.00", day="2026-11-16", operator=None):
    mapping={"01":"东城公交", "02":"西城巴士", "03":"南城客运"}
    return {"event_id":event_id, "card":"0001", "route":route, "business_day":day,
            "transfer_discount":due, "operator":operator or mapping.get(route, "未裁决运营方")}


def test_real_sample_busy_day_proportional(result):
    m=result["stages"][7]["metrics"]
    assert m["ruling"]["selected"]=="proportional_shortfall"
    assert m["ruling"]["rejected"]=="first_come_first_served"
    assert m["busy_days"]==1 and m["published"] is True
    assert m["fund_due_total"]=="16.00" and m["fund_paid_total"]=="10.00"
    assert m["fund_shortfall_total"]=="6.00" and m["clawback_total"]=="0.00"


def test_real_sample_operators_share_gap_by_due(result):
    ledger=result["stages"][7]["metrics"]["operator_ledger"]
    # 两家运营方各应得 8 元，按同比例 0.625 共担缺口，各补 5 元
    assert {o["operator"]:(o["fund_due"],o["fund_paid"],o["fund_shortfall"]) for o in ledger}=={
        "西城巴士":("8.00","5.00","3.00"), "南城客运":("8.00","5.00","3.00")}
    assert all(o["share_ratio"]=="0.6250" for o in ledger)


def test_cent_conservation_real_sample(result):
    rows=result["stages"][7]["rows"]
    assert all(Decimal(r["fund_due"])==Decimal(r["fund_paid"])+Decimal(r["fund_shortfall"]) for r in rows)
    assert sum((Decimal(r["fund_paid"]) for r in rows), Decimal(0))==Decimal("10.00")
    assert sum((Decimal(r["fund_shortfall"]) for r in rows), Decimal(0))==Decimal("6.00")


def test_shortfall_trips_kept_and_no_clawback(result):
    rows=result["stages"][7]["rows"]
    short=[r for r in rows if r["fund_status"]=="部分补偿"]
    assert len(short)==result["stages"][7]["metrics"]["shortfall_count"]==16
    assert all(Decimal(r["fund_paid"])>0 and Decimal(r["fund_shortfall"])>0 for r in short)
    assert all(Decimal(r["fund_paid"])>=0 for r in rows)


def test_largest_remainder_uniqueness_and_exhaust():
    # 预算 10 分、三家各应得 10 分（共 30）-> 3.33/3.33/3.33，余 1 分按键升序给 a -> 4/3/3
    out=largest_remainder([("a",10),("b",10),("c",10)], 10)
    assert out=={"a":4,"b":3,"c":3} and sum(out.values())==10


def test_largest_remainder_uniqueness_and_exhaust():
    # 预算 10 分、三家各应得 10 分（共 30）-> 3.33/3.33/3.33，余 1 分按键升序给 a -> 4/3/3
    out=largest_remainder([("a",10),("b",10),("c",10)], 10)
    assert out=={"a":4,"b":3,"c":3} and sum(out.values())==10


def test_largest_remainder_tie_break_deterministic():
    # 预算 1 分、两家各应得 1 分 -> 0.5/0.5 同余量，按键升序给 a，与输入次序无关
    out1=largest_remainder([("a",1),("b",1)], 1)
    out2=largest_remainder([("b",1),("a",1)], 1)
    assert out1==out2=={"a":1,"b":0}


def test_fund_sufficient_pays_in_full():
    rows=[claim("e1","01","1.00"), claim("e2","02","1.00")]
    m=evaluate(rows, {"parameters":{"subsidy_fund":"50.00"},"quarantine":[]})["metrics"]
    assert m["fund_paid_total"]=="2.00" and m["fund_shortfall_total"]=="0.00"
    assert m["busy_days"]==0 and m["published"] is True


def test_fund_zero_all_shortfall_but_retained():
    rows=[claim("e1","01","1.00"), claim("e2","02","1.00")]
    out=evaluate(rows, {"parameters":{"subsidy_fund":"0.00"},"quarantine":[]})
    assert all(r["fund_paid"]=="0.00" and r["fund_status"]=="部分补偿" for r in out["rows"])
    assert out["metrics"]["fund_paid_total"]=="0.00" and out["metrics"]["published"] is True


def test_input_order_invariant():
    rows=[claim(f"e{i:02d}", "01" if i%2 else "02", "1.00") for i in range(10)]
    a=evaluate(rows, {"parameters":{},"quarantine":[]})["rows"]
    b=evaluate(list(reversed(rows)), {"parameters":{},"quarantine":[]})["rows"]
    assert sorted((r["event_id"],r["fund_paid"]) for r in a)==sorted((r["event_id"],r["fund_paid"]) for r in b)


def test_rerun_same_batch_does_not_reconsume(sample):
    a=execute(sample); b=execute(sample)
    assert a["run_id"]==b["run_id"] and len(store.history())==1
    assert a["stages"][7]["metrics"]["fund_paid_total"]==b["stages"][7]["metrics"]["fund_paid_total"]


def test_multi_day_fund_is_per_day_cap():
    rows=[claim("e1","01","6.00","2026-11-16"), claim("e2","01","6.00","2026-11-17")]
    m=evaluate(rows, {"parameters":{"subsidy_fund":"10.00"},"quarantine":[]})["metrics"]
    assert len(m["daily"])==2
    assert all(d["fund_paid_total"]=="6.00" and d["over_cap"] is False for d in m["daily"])
    assert m["fund_paid_total"]=="12.00"


def test_non_claim_rows_preserved():
    rows=[{**claim("e1","01","0.00"), "transfer_discount":"0.00"}]
    out=evaluate(rows, {"parameters":{},"quarantine":[]})["rows"]
    assert out[0]["fund_status"]=="无申领" and out[0]["fund_paid"]=="0.00"


def test_unknown_route_operator_blocked():
    with pytest.raises(DomainError) as e:
        evaluate([claim("e1","99","1.00")], {"parameters":{},"quarantine":[]})
    assert e.value.code=="UNKNOWN_OPERATOR"


def test_duplicate_claim_rejected():
    rows=[claim("e1","01","1.00"), {**claim("e1","02","1.00")}]
    with pytest.raises(DomainError) as e:
        evaluate(rows, {"parameters":{},"quarantine":[]})
    assert e.value.code=="FUND_DUPLICATE"


def test_negative_fund_rejected():
    with pytest.raises(DomainError):
        evaluate([], {"parameters":{"subsidy_fund":"-1"},"quarantine":[]})


def test_unbalanced_upstream_blocks_publication():
    ctx={"parameters":{},"quarantine":[],"reconcile":{"metrics":{"balanced":False}}}
    with pytest.raises(DomainError) as e:
        evaluate([claim("e1","01","1.00")], ctx)
    assert e.value.code=="UNBALANCED"


def test_operator_override_via_parameters():
    rows=[claim("e1","01","1.00")]
    out=evaluate(rows, {"parameters":{"route_operators":{"01":"定制专线"}},"quarantine":[]})
    assert out["rows"][0]["operator"]=="定制专线"


def test_fund_api_entrances(client):
    assert client.get("/api/fund").status_code==200
    assert client.get("/fund").status_code==200


def test_unique_allocation_via_run_digest(client):
    p1=client.post("/api/runs",json={"sample":"dirty.csv"}).get_json()
    p2=client.post("/api/runs",json={"sample":"dirty.csv"}).get_json()
    assert p1["run_id"]==p2["run_id"]
    assert p1["stages"][7]["rows"]==p2["stages"][7]["rows"]
