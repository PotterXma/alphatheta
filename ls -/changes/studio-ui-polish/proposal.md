## Why

Strategy Studio 底层 JS 数据逻辑已跑通 (47/47 测试通过)，但当前 UI 极其原始简陋——使用原生浏览器控件、无毛玻璃效果、缺乏视觉层次。这破坏了 AlphaTheta v2 整体的"华尔街量化终端"高级感。需要将 Strategy Studio 的 HTML 骨架和 CSS 彻底重构为**暗黑玻璃态 (Dark Glassmorphism)** 设计语言，与系统其他页面保持一致的美学水准。

## What Changes

- 重构 `index.html` 中 `view-signal` 的 Strategy Studio 内部 DOM 结构，采用语义化 class 命名的 CSS Grid 两栏布局
- 左栏 (构建区): 毛玻璃工具栏 + 发光按钮 + Flexbox 横向腿卡片 + Buy/Sell & Call/Put Toggle 切换器
- 右栏 (推演区): 深邃发光边框图表卡片 + 2×2 资金/风控 Metric 网格
- 彻底重写 `style.css` 中 Strategy Studio 相关样式: 暗黑背景色、`backdrop-filter: blur(12px)` 毛玻璃、青色 `#06b6d4` 发光强调色、`rgba(255,255,255,0.08)` 微光边框
- 重置 `<select>`, `<button>`, `<input>` 为圆角暗色高级控件
- 调整 `js/views/strategy_studio.js` 中 `renderLegs()` 模板字符串以匹配新 class 命名，保持双向绑定不变

## Capabilities

### New Capabilities
- `studio-glassmorphism`: Strategy Studio 暗黑玻璃态视觉重构——HTML 骨架、CSS 样式、控件美化、响应式布局

### Modified Capabilities
_(无现有 spec 需修改)_

## Impact

- **前端文件**: `index.html` (DOM 结构), `style.css` (样式), `js/views/strategy_studio.js` (renderLegs 模板)
- **无后端变更**: 纯 UI 层改动
- **无 breaking changes**: 所有 DOM ID 保持不变 (`legsContainer`, `payoffChart`, `studioMaxProfit` 等)，JS 双向绑定无需修改
- **Dockerfile**: 无变更 (已 COPY `js/` 和 `style.css`)
