from decimal import Decimal
from app.values import number, money
from app.errors import DomainError

# 线路归属裁决：线路 -> 运营方。可由 parameters.route_operators 覆盖。
DEFAULT_ROUTE_OPERATORS={"01":"东城公交", "02":"西城巴士", "03":"南城客运"}
# 城市换乘补贴基金按日包干额度（元/业务日）。可由 parameters.subsidy_fund 覆盖。
DEFAULT_DAILY_FUND="10.00"

RULING={
    "selected":"proportional_shortfall",
    "selected_label":"按应得比例共同承担缺口",
    "rejected":"first_come_first_served",
    "rejected_label":"按发生先后先到先得",
    "reasons":[
        "先到先得的结果取决于批次到达次序，同源重跑不唯一，无法形成唯一分配结果",
        "晚到运营方可能零补偿，与线路归属裁决要求的同等待遇冲突",
        "比例共担只依赖线路归属与应得金额，输入顺序不变，结果可复算、可对账",
    ],
}

CENT=Decimal("0.01")


def cents(value):
    if isinstance(value, str): value=number(value)
    return int((value*100).to_integral_value())


def yuan(total_cents):
    return str((Decimal(total_cents)/100).quantize(CENT))


def largest_remainder(claims, budget_cents):
    """按 claims[(key, due_cents)] 的应得比例把整数分预算分完，余数按小数余量降序、
    余量相同按键升序裁决，保证唯一且分币守恒。"""
    total_due=sum(due for _,due in claims)
    if total_due<=0: return {key:0 for key,_ in claims}
    if budget_cents>=total_due:
        return {key:due for key,due in claims}
    allocated={}; remainders=[]; used=0
    for key,due in claims:
        exact=Decimal(budget_cents)*Decimal(due)/Decimal(total_due)
        base=int(exact)  # 截断，base <= exact
        allocated[key]=base; used+=base
        remainders.append((exact-base, key))
    leftover=budget_cents-used
    for _,key in sorted(remainders, key=lambda x:(-x[0], str(x[1])))[:leftover]:
        allocated[key]+=1
    return allocated


def evaluate(rows, context):
    params=context.get("parameters", {})
    fund=number(params.get("subsidy_fund", DEFAULT_DAILY_FUND))
    if fund<0: raise DomainError("BAD_FUND", "日包干基金不能为负")
    mapping=dict(DEFAULT_ROUTE_OPERATORS)
    override=params.get("route_operators")
    if override is not None:
        if not isinstance(override, dict) or not override:
            raise DomainError("BAD_OPERATOR_MAP", "线路归属表需要非空对象")
        mapping={str(k):str(v) for k,v in override.items()}

    # 跨运营方对账未平前不发布结算结果：前置阶段已有平衡裁决
    prior=[v for v in context.values() if isinstance(v, dict) and "metrics" in v]
    if any(s["metrics"].get("balanced") is False for s in prior):
        raise DomainError("UNBALANCED", "上游对账未对平，基金结算不得发布")

    claim_keys=set(); enriched=[]
    for row in rows:
        due=number(row.get("transfer_discount", "0"))
        if due<0: raise DomainError("BAD_DISCOUNT", "换乘优惠不能为负")
        route=str(row.get("route", ""))
        operator=mapping.get(route)
        if not operator: raise DomainError("UNKNOWN_OPERATOR", f"线路{route}未裁决运营方归属")
        key=str(row.get("event_id", row.get("_line", "")))
        if due>0:
            if key in claim_keys: raise DomainError("FUND_DUPLICATE", "同一行程重复申领基金")
            claim_keys.add(key)
        enriched.append({**row, "operator":operator, "fund_due":money(due),
                         "fund_paid":money(Decimal(0)), "fund_shortfall":money(due),
                         "fund_status":"无申领" if due==0 else "待分配"})

    days=sorted({r.get("business_day", "") for r in enriched})
    by_day={day:[r for r in enriched if r.get("business_day", "")==day] for day in days}
    daily=[]; operator_ledger=[]
    for day in days:
        day_rows=by_day[day]
        key_of=lambda r: str(r.get("event_id", r.get("_line", "")))
        claims=[(key_of(r), cents(number(r["fund_due"])))
                for r in day_rows if cents(number(r["fund_due"]))>0]
        due_total=sum(d for _,d in claims)
        budget=min(cents(fund), due_total)
        # 第一级：运营方按线路归属汇总应得，共同承担缺口
        op_due={}
        members={}
        for r in day_rows:
            d=cents(number(r["fund_due"]))
            if d:
                op_due[r["operator"]]=op_due.get(r["operator"], 0)+d
                members.setdefault(r["operator"], []).append((key_of(r), d))
        op_claims=sorted(op_due.items(), key=lambda x:x[0])
        op_share=largest_remainder(op_claims, budget)
        # 第二级：运营方内部按行程应得再分，余量确定且可复算
        paid={}
        for operator in sorted(op_due):
            paid.update(largest_remainder(members[operator], op_share[operator]))
        for r in day_rows:
            got=paid.get(key_of(r), 0); due_c=cents(number(r["fund_due"]))
            r["fund_paid"]=yuan(got)
            r["fund_shortfall"]=yuan(due_c-got)
            r["fund_status"]="无申领" if due_c==0 else ("足额" if got==due_c else "部分补偿")
        paid_total=sum(paid.values())
        short_total=due_total-paid_total
        day_info={"business_day":day, "fund_cap":money(fund), "fund_due_total":yuan(due_total),
                  "fund_paid_total":yuan(paid_total), "fund_shortfall_total":yuan(short_total),
                  "fund_remaining":yuan(cents(fund)-budget), "over_cap":due_total>cents(fund),
                  "claim_count":len(claims), "shortfall_count":sum(1 for r in day_rows if r["fund_status"]=="部分补偿")}
        daily.append(day_info)
        for operator, due_c in op_claims:
            got=sum(paid.get(k,0) for k,_ in members[operator])
            operator_ledger.append({"business_day":day, "operator":operator,
                                    "fund_due":yuan(due_c), "fund_paid":yuan(got),
                                    "fund_shortfall":yuan(due_c-got),
                                    "share_ratio":str((Decimal(got)/Decimal(due_c)).quantize(Decimal("0.0001"))) if due_c else "0"})

    # 对账闸门：分币守恒、额度不超限、乘客减免不追回、缺口行程留痕
    checks=[]
    def check(code, ok, detail):
        checks.append({"code":code, "ok":bool(ok), "detail":detail})
        if not ok: raise DomainError("FUND_NOT_BALANCED", f"基金对账未平：{code} {detail}")
    due_all=sum(cents(number(r["fund_due"])) for r in enriched)
    paid_all=sum(cents(number(r["fund_paid"])) for r in enriched)
    short_all=sum(cents(number(r["fund_shortfall"])) for r in enriched)
    check("cent_conservation", paid_all+short_all==due_all,
          f"{yuan(paid_all)} + {yuan(short_all)} = {yuan(due_all)}")
    check("cap_not_exceeded", all(cents(d["fund_paid_total"])<=cents(fund) for d in daily),
          "每日补偿不超过当日基金额度")
    check("shortfall_retained", all(r["fund_paid"]!="" and r["fund_status"] in {"足额","部分补偿","无申领"} for r in enriched),
          "未获足额补偿的行程保留记录")
    check("no_clawback", all(number(r["fund_paid"])>=0 for r in enriched) and short_all>=0,
          "乘客已享减免不追回")
    check("operator_books_balanced",
          all(cents(o["fund_due"])-cents(o["fund_paid"])==cents(o["fund_shortfall"]) for o in operator_ledger),
          "运营方分账应得=已补+缺口")
    published=all(c["ok"] for c in checks)

    metrics={"ruling":RULING, "daily_fund":money(fund),
             "fund_due_total":yuan(due_all), "fund_paid_total":yuan(paid_all),
             "fund_shortfall_total":yuan(short_all), "clawback_total":yuan(0),
             "busy_days":sum(1 for d in daily if d["over_cap"]),
             "claim_count":len(claim_keys),
             "shortfall_count":sum(1 for r in enriched if r["fund_status"]=="部分补偿"),
             "operator_count":len({o["operator"] for o in operator_ledger}),
             "published":published, "checks":checks,
             "daily":daily, "operator_ledger":operator_ledger}
    return {"rows":enriched, "quarantine":[], "metrics":metrics}
