# 接口

模块GET使用仓内样例，模块POST可传csv或rows与context，直接计算当前规则。/api/runs使用完整流水线并原子保存。每个阶段返回rows、quarantine、metrics；后续阶段还返回累计隔离。/api/upload接收multipart文件file。/api/runs/<id>/archive只导出一份带清单与证据的CSV。

## 基金分配 `/api/fund`（M8，阶段索引7）

GET 用仓内脏样例算到 M8；POST 可传 `{"sample","parameters"}` 或 `{"csv","parameters"}` 走完整流水线，也可传 `{"rows","context"}` 只预览本阶段。参数：`subsidy_fund`（日包干基金，元，默认 10.00）、`route_operators`（线路→运营方归属覆盖表）。返回 rows（每行程含 fund_due/fund_paid/fund_shortfall/fund_status/operator）与 metrics（ruling 裁决、daily 日账、operator_ledger 分账、checks 对账闸门、published 发布状态）。同源同参数重跑返回同一 run_id，不重复占用额度；上游 balanced=false 时返回 UNBALANCED 且不发布。
