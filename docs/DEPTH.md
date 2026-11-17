# 深度登记 公交刷卡换乘优惠与日封顶回算

规模：中型。使用者：公交清分中心复核员。核心规则：换乘按上次有效付费行程的时间窗计算，优惠与日封顶按确定顺序裁决并保留分币守恒。

## 功能模块

| 模块 | 使用者动作 | 入口 | 核心文件 | 测试 |
|---|---|---|---|---|
| M1 刷卡采信 | 查看并运行刷卡采信 | `/api/taps` | `app/modules/m1_taps/rules.py` | `tests/test_m1.py` |
| M2 线路换乘 | 查看并运行线路换乘 | `/api/routes` | `app/modules/m2_routes/rules.py` | `tests/test_m2.py` |
| M3 票价版本 | 查看并运行票价版本 | `/api/fares` | `app/modules/m3_fares/rules.py` | `tests/test_m3.py` |
| M4 行程配对 | 查看并运行行程配对 | `/api/journeys` | `app/modules/m4_journeys/rules.py` | `tests/test_m4.py` |
| M5 优惠回算 | 查看并运行优惠回算 | `/api/discounts` | `app/modules/m5_discounts/rules.py` | `tests/test_m5.py` |
| M6 清分对账 | 查看并运行清分对账 | `/api/clearing` | `app/modules/m6_clearing/rules.py` | `tests/test_m6.py` |
| M7 日结归档 | 查看并运行日结归档 | `/api/settlement` | `app/modules/m7_settlement/rules.py` | `tests/test_m7.py` |
| M8 基金分配 | 查看并运行基金分配 | `/api/fund` | `app/modules/m8_fund/rules.py` | `tests/test_m8.py` |

## 陷阱登记

| TRAP | 现象 | 朴素实现 | 本项目处理 | 处理位置 | 测试 |
|---|---|---|---|---|---|
| TRAP-01 | 旧编码 | 默认解码失败 | 回退GB18030 | `app/modules/m1_taps/rules.py` | `tests/test_m1.py::test_legacy_encoding_real_sample` |
| TRAP-02 | BOM | 首列名多字符 | utf-8-sig | `app/modules/m1_taps/rules.py` | `tests/test_m1.py::test_bom_real_sample` |
| TRAP-03 | 带引号换行 | 拆成两条 | csv逻辑行 | `app/modules/m1_taps/rules.py` | `tests/test_m1.py::test_quoted_newline_is_one_record` |
| TRAP-05 | 列数不匹配 | 静默错列 | 隔离原行 | `app/modules/m1_taps/rules.py` | `tests/test_m1.py::test_bad_columns_real_sample` |
| TRAP-08 | 前导零ID | 编码变形 | 全程字符串 | `app/modules/m1_taps/rules.py` | `tests/test_m1.py::test_identifier_preserved_real_sample` |
| TRAP-14 | 重复键冲突 | 后写覆盖 | 保留首条并隔离冲突行 | `app/modules/m1_taps/rules.py` | `tests/test_m1.py::test_duplicate_conflict_real_sample` |
| TRAP-18 | 空态三态 | 一律成功 | 分别错误码 | `app/modules/m1_taps/rules.py` | `tests/test_m1.py::test_three_empty_states` |
| TRAP-26 | 旧版本提交 | 覆盖新结果 | 版本条件更新 | `app/store.py` | `tests/test_e2e.py::test_stale_review_409` |
| TRAP-06 | 全角数字 | 转换失败 | NFKC与Decimal | `app/values.py` | `tests/test_m3.py::test_thousands_and_fullwidth` |
| TRAP-07 | 金额哨兵 | 零参与扣费 | 空值隔离 | `app/values.py` | `tests/test_m3.py::test_real_sentinel_quarantined` |
| TRAP-11 | 混合偏移 | 落错版本 | UTC归整 | `app/values.py` | `tests/test_m3.py::test_timezone_equal` |
| TRAP-23 | 换乘截止点 | 重复优惠 | 截止点排除 | `app/modules/m5_discounts/rules.py` | `tests/test_m5.py::test_exact_window_excluded` |
| TRAP-25 | 票价重叠 | 随意取版 | 冲突隔离 | `app/modules/m3_fares/rules.py` | `tests/test_m3.py::test_overlap_rejected` |
| TRAP-30 | 基金忙日缺口 | 先到先得、运营方补偿直接相加超额度 | 按应得比例共担+两级最大余数 | `app/modules/m8_fund/rules.py` | `tests/test_m8.py::test_real_sample_busy_day_proportional` |
| TRAP-31 | 分币取整漂移 | 浮点比例导致总额与基金差几分 | 整数分最大余数、余量按键裁决 | `app/modules/m8_fund/rules.py` | `tests/test_m8.py::test_cent_conservation_real_sample` |
| TRAP-32 | 重跑重复占额 | 每次运行累加占用基金 | 摘要+规则版本+参数决定同一批次 | `app/manifest.py`、`app/store.py` | `tests/test_m8.py::test_rerun_same_batch_does_not_reconsume` |
| TRAP-33 | 对账未平即发布 | 闸门缺失直接出结算 | 平衡检查失败阻断发布 | `app/modules/m8_fund/rules.py` | `tests/test_m8.py::test_unbalanced_upstream_blocks_publication` |

## 对账规则

输入原始逻辑行=最终采纳来源行+隔离来源行+重复行+空白行+分段表头。派生记录用_sources保存完整来源，因此分组不丢行。业务预期合计与上游申报合计之差等于逐行差异之和。结果按输入摘要、规则版本及参数产生唯一批次，事务写入；同源重跑只复用已有批次。

## 基金分配规则（M8）

基金只补偿换乘优惠（transfer_discount），封顶减免不在基金口径内。每业务日独立包干：应得合计不超过当日基金时足额支付；超过时先按线路归属把应得汇总到运营方，运营方之间用最大余数法按应得比例共担缺口，再在运营方内部对行程用同一方法二次分配。全程整数分运算，余数相同按业务键升序裁决，因此结果与输入顺序无关、唯一可复算，实补合计恒等于 min(当日基金, 应得合计)。乘客已享减免不追回，`clawback_total` 恒为 0；部分补偿行程不删除、不补足，保留 fund_due/fund_paid/fund_shortfall 三栏。发布闸门校验分币守恒、额度不超限、缺口留痕、不追回、运营方分账平衡，任一不过即不发布。先到先得方案因结果依赖批次到达次序、同源重跑不唯一且对晚到运营方不公，被裁决否决。

## 已知不覆盖

4MB以上文件需预先按业务键分批；不模拟生产支付与外部回调。人工复核只变更批次状态，不改写原始记录。
