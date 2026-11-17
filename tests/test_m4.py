from app.modules.m4_journeys.rules import evaluate
def tap(id="1",at="2026-11-16T16:30:00Z",state="success"):return {"event_id":id,"card":"0001","at":at,"result":state}
def test_real_failed_not_journey(result): assert any(r["reason"]=="FAILED_TAP" for r in result["stages"][3]["quarantine"])
def test_real_business_day(result): assert result["stages"][3]["rows"][0]["business_day"]=="2026-11-16"
def test_local_midnight(): assert evaluate([tap()],{})["rows"][0]["business_day"]=="2026-11-17"
def test_same_card_same_time_conflict(): assert evaluate([tap("1"),tap("2")],{})["quarantine"][0]["reason"]=="SIMULTANEOUS_TAP"
def test_failed_cannot_anchor(): assert evaluate([tap(state="failed")],{})["rows"]==[]
def test_real_journeys_count(result): assert result["stages"][3]["metrics"]["journeys"]==32
def test_empty_journey(): assert evaluate([],{})["metrics"]["cards"]==0
