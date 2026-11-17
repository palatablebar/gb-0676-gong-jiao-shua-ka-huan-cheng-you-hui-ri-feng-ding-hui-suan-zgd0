from app.modules.m2_routes.rules import evaluate
def test_real_routes(result): assert result["stages"][1]["metrics"]["routes"]==3
def test_real_alias_normalized(result): assert result["stages"][1]["rows"][0]["route"]=="01"
def test_unknown_route_quarantine(result): assert any(r["reason"]=="UNKNOWN_ROUTE" for r in result["stages"][1]["quarantine"])
def test_alias_has_same_group(): assert evaluate([{"route":"1路","card":"01"},{"route":"01","card":"02"}],{})["rows"][0]["line_group"]=="city"
def test_missing_card(): assert evaluate([{"route":"01","card":""}],{})["quarantine"][0]["reason"]=="EMPTY_CARD"
def test_all_unknown(): assert evaluate([{"route":"X","card":"a"}],{})["rows"]==[]
def test_input_order_preserved(): assert [r["card"] for r in evaluate([{"route":"01","card":"02"},{"route":"01","card":"01"}],{})["rows"]]==["02","01"]
