from app.values import instant,number
from app.errors import DomainError
from app.reasons import reject
from decimal import Decimal
FARES=[{"start":"2026-01-01T00:00:00+08:00","end":"2026-11-01T00:00:00+08:00","version":"F1","amount":"2.00"},{"start":"2026-11-01T00:00:00+08:00","end":"2027-01-01T00:00:00+08:00","version":"F2","amount":"2.50"}]
def select_fare(at,fares):
    hits=[r for r in fares if instant(r["start"])<=at<instant(r["end"])]
    if len(hits)!=1:raise DomainError("FARE_CONFLICT","票价无效或生效窗重叠")
    return hits[0]
def evaluate(rows,context):
    good=[];bad=[]
    for row in rows:
        try:
            at=instant(row["event_time"]);rule=select_fare(at,context.get("parameters",{}).get("fares",FARES));reported=number(row["reported"])
            if reported<0:raise DomainError("NEGATIVE_FARE","实扣金额不能为负")
            good.append({**row,"at":at.isoformat(),"base_fare":rule["amount"],"fare_version":rule["version"],"reported":str(reported)})
        except (DomainError,KeyError) as e:bad.append(reject(row,getattr(e,"code","MISSING_FIELD"),str(e)))
    return {"rows":good,"quarantine":bad,"metrics":{"accepted":len(good),"versions":sorted(set(r["fare_version"] for r in good))}}
