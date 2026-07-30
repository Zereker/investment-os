# Transition Plan（2026–2028）

## 目标

渐进迁移至：

\[
\text{Cash }(15\%+U)+\text{QQQM }28\%+\text{SPYM }(57\%-A_{basis})+\text{SOXX }A_{actual}
\]

其中 `A_stage=6%` 为当前治理上限，`U=max(A_stage-A_actual,0)`。

## 三条资金通道

1. `Routine DCA`：只使用已到账 `F`，Core买入 `D=min(F,G0)`。
2. `Strategic Baseline`：`B=min(S/R,G)`，其中 `S`扣除结构性现金与SOXX阶段储备。
3. `Tactical Acceleration`：仅在价格、估值和完整IC通过时增加Core部署。

SOXX不使用以上三条Core通道；任何追加都走独立完整IC。

## SOXX阶段

- 当前阶段上限6%；3%与4.5%为阶段内执行检查点，不是自动买入档位。
- 超过6%前仍须逐笔IC。
- 6%→10%→12.5%→15%的每次推进都需季度治理、同日穿透和Registry更新。
- 15%是长期上限与最终治理阶段，不是完成日期承诺。
- 护栏或数据门未通过时，储备继续留在现金；不转投SPYM，也不强制买SOXX。

## 完成

2028-12是Core战略基线的计划完成月，不是SOXX必须达到15%的日期。SOXX是否推进只由治理与风险条件决定。
