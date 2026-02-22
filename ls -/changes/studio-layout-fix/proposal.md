## Why

Strategy Studio (`view-signal`) 在融合了智能推荐 Top 3、T+n 模拟滑块和组合 Greeks 面板后，出现三个严重的布局塌陷：
1. `.recommendation-panel` 被困在 `.studio-container` 两栏布局内，被左侧期权腿表格挤压错位
2. `.sim-controls` 滑块与 `.chart-card-title` 重叠，控件标签难以辨识
3. `.greeks-grid` 四张卡片纵向块级堆叠，浪费大量水平空间

## What Changes

- **DOM 重排**：将 `.recommendation-panel` 从 `.studio-container` 内部提取至其正上方，成为全宽独立模块
- **新增控制台容器**：在右侧 `.chart-card` 内新增 `.chart-controls` 容器，将两个模拟滑块归入其中，与图表标题隔离
- **Greeks Grid 改为 2D 网格**：废弃 `.greeks-grid` 的块级堆叠，改用 `grid-template-columns: repeat(4, 1fr)` 横向一排
- **滑块样式重写**：隐藏原生 range 外观，使用 `#06b6d4` 青色轨道和 thumb，统一极客风格

## Capabilities

### New Capabilities
- `studio-layout-restructure`: Strategy Studio 的 DOM 重排、控制台容器化和 Greeks Grid 紧凑化

### Modified Capabilities
_(无)_

## Impact

- **HTML**: `index.html` — `view-signal` section (lines 176-301) DOM 结构调整
- **CSS**: `style.css` — `.recommendation-panel`、`.chart-controls`、`.sim-controls`、`.greeks-grid` 样式重写
- **JS**: 无变更 — 不改动任何业务逻辑，所有 `getElementById` 引用保持不变
