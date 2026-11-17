from app.reasons import reject
from app.values import instant
from datetime import timezone,timedelta
def evaluate(rows,context):
    good=[];bad=[];seen=set()
    for row in sorted(rows,key=lambda r:(r.get("card",""),r["at"],r.get("event_id",""))):
        if row.get("result")!="success":bad.append(reject(row,"FAILED_TAP","失败刷卡不构成行程"));continue
        key=(row["card"],row["at"])
        if key in seen:bad.append(reject(row,"SIMULTANEOUS_TAP","同卡同刻多行程"));continue
        seen.add(key);at=instant(row["at"])
        good.append({**row,"business_day":at.astimezone(timezone(timedelta(hours=8))).date().isoformat(),"journey":row["card"]+"-"+row["event_id"]})
    return {"rows":good,"quarantine":bad,"metrics":{"journeys":len(good),"cards":len(set(r["card"] for r in good))}}
