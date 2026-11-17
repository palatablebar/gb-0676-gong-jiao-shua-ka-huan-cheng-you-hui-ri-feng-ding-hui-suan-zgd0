from app.reasons import reject
ROUTES={"01":"01","1路":"01","02":"02","2路":"02","03":"03","3路":"03"}
def evaluate(rows,context):
    good=[];bad=[]
    for row in rows:
        route=ROUTES.get(row.get("route"))
        if not route:bad.append(reject(row,"UNKNOWN_ROUTE","线路未登记"));continue
        if not row.get("card"):bad.append(reject(row,"EMPTY_CARD","卡号为空"));continue
        good.append({**row,"route":route,"line_group":"city"})
    return {"rows":good,"quarantine":bad,"metrics":{"routes":len(set(r["route"] for r in good)),"accepted":len(good)}}
