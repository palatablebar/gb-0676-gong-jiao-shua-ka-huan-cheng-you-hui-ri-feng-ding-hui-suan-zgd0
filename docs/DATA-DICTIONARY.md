# 数据定义

刷卡事件以event_id去重，card保留前导零。route支持1路/01等别名。event_time必须带偏移；业务日为Asia/Shanghai。result仅success可作为行程，失败刷卡隔离。reported为实扣人民币元。票价F1至2026-11-01前为2元，F2为2.50元。

跨线路换乘必须在上一次实际付费行程后60分钟内，恰好60分钟排除。同线路无优惠；零付费行程不能延长换乘锚点。先扣1元换乘优惠，再对卡号业务日施加6元封顶。每条基本票价=实算扣费+换乘优惠+封顶优惠。

业务ID和超大整数按文本保形；Decimal参与数量金额计算，对外序列化为字符串。哨兵集合定义在app/values.py，缺失值不能当零。所有时间带UTC偏移，先转UTC比较，业务日按指定地区划分。区间统一[start,end)。重复业务键保留第一条、完全相同行计重复；值冲突行隔离且保留原值。空文件、全空白、仅表头分开拒绝。

## 基金分配（M8）字段

线路归属默认表：01→东城公交、02→西城巴士、03→南城客运，可由参数 `route_operators` 整体覆盖；未登记线路报 UNKNOWN_OPERATOR。日包干基金参数 `subsidy_fund` 默认 10.00 元/业务日，负值报 BAD_FUND。

每条行程输出：`operator`（线路归属运营方）、`fund_due`（应补=换乘优惠，元）、`fund_paid`（基金实补）、`fund_shortfall`（未补缺口=应补-实补）、`fund_status`（足额/部分补偿/无申领）。日汇总 `daily` 含 fund_cap/fund_due_total/fund_paid_total/fund_shortfall_total/fund_remaining/over_cap/claim_count/shortfall_count；运营方分账 `operator_ledger` 含 fund_due/fund_paid/fund_shortfall/share_ratio。顶层 metrics 含 ruling（裁决与否决理由）、clawback_total（恒 0.00，乘客减免不追回）、busy_days、published 与 checks 闸门明细。金额均为字符串、保留两位小数；分币守恒关系 fund_due=fund_paid+fund_shortfall 在行程、运营方、日三个层级同时成立。

运行清单包括输入sha256、规则版本、参数、生成时刻与耗时。源行编号以CSV解析器的物理结束行号表示，引号内换行不增加记录数。输入超过4MB返回413，非法表头和类型返回422，失效版本复核返回409。