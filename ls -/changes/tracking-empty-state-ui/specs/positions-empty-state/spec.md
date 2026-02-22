## ADDED Requirements

### Requirement: 空状态占位显示
当 `positions.length === 0` 时，`<tbody>` SHALL 渲染居中占位行 (跨全部 9 列)，包含:
- SVG 雷达扫描动效 (旋转动画)
- 幽蓝色提示文案: "资金已就位 ($100,000)。全天候扫描引擎运行中，等待 LEAPS 信号..."

#### Scenario: 空仓时表格显示
- **WHEN** 持仓列表为空数组
- **THEN** tbody 显示雷达占位行，表头保持可见

### Requirement: 有数据时不显示空状态
当 `positions.length > 0` 时，空状态行 SHALL 被移除，显示正常数据行。

#### Scenario: 首笔持仓加入
- **WHEN** 持仓列表从 0 变为 1
- **THEN** 空状态行消失，显示持仓数据行
