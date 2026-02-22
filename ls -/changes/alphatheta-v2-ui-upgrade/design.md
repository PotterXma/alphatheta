## Context

AlphaTheta v1.0: 纯 HTML/CSS/JS 单页仪表盘，暗黑 glassmorphism 设计。v7.0 重构为侧边栏 SPA 架构，5 个功能视图，i18n 全覆盖，保持零外部依赖。

## Goals / Non-Goals

**Goals:**
- 纯 JS SPA 路由（hash-based `#view`），无框架
- 侧边栏 + 主工作区布局，视图切换无刷新
- `t(key)` i18n + `data-i18n` 声明式绑定 + `renderAll()` 全局重渲染
- Canvas 微型趋势图（净值 + 10% 基准线）
- 沙盒参数实时联动计算
- 持仓表 < 768px 响应式降级为卡片流
- 所有新组件复用 `.glass-card` + CSS 自定义属性

**Non-Goals:**
- 不接入真实 API/WebSocket
- 不实现用户认证
- 不做 PWA 或构建工具
- 展期计算仅弹出提示框，不实现完整展期交易流

## Decisions

### 1. SPA 路由：Hash-based 路由

**选择**: `window.location.hash` 驱动视图切换。5 个视图容器 (`#view-dashboard`, `#view-signal`, etc.) 通过 `display: none/block` 切换可见性。`hashchange` 事件监听路由变化。

**替代方案**: History API (`pushState`) — 需要服务端路由配置支持，hash 路由对纯静态文件更友好。

### 2. 侧边栏：固定宽度 glassmorphic 面板

**选择**: `width: 240px`，`position: fixed`，`height: 100vh`，glassmorphism 样式。菜单项带 SVG 图标 + 文字，活动项用 `accent-cyan` 左侧边条高亮。主工作区 `margin-left: 240px`。

**移动端**: `< 900px` 侧边栏折叠为图标模式 (`width: 64px`)，hover 展开。

### 3. Kill Switch：全局状态切换

**选择**: `APP_STATE.isHalted` 控制。按钮点击切换状态，halted 时按钮从红色变为闪烁琥珀色，全局覆盖半透明遮罩层并禁用执行按钮。

### 4. 保证金使用率进度条

**选择**: CSS `linear-gradient` + `width` 百分比动态设置。`< 60%` 翠绿，`≥ 60%` 琥珀色。使用 CSS `transition` 动画过渡。

### 5. 策略沙盒计算（同 v6.0）

- 净成本 = strike × 100 − premium × 100
- 盈亏平衡 = strike − premium
- 最大收益 = premium × 100
- 年化收益率 = (premium / strike) × (365 / DTE) × 100
- 年化收益率用发光高亮显示

### 6. 持仓表卡片流响应式降级

**选择**: `@media (max-width: 768px)` 隐藏 `<table>`，显示 `.card-view` 容器。JS 同时渲染表格和卡片两套 DOM，CSS 控制可见性。

**替代方案**: JS 动态切换 DOM — CSS-only 切换更简洁，避免 resize 事件监听开销。

### 7. 一键展期

**选择**: 每行持仓的操作列增加"展期"按钮。点击弹出 `alert()` 模拟展期计算结果（显示建议的新到期日和预估权利金）。Non-goal: 不实现真实交易流。

### 8. 绩效报告面板

**选择**: 两个指标卡（自动化次数 + 累计权利金）+ Canvas 趋势图。复用 `.glass-card` 样式。

### 9. API 密钥保险箱

**选择**: `<input type="password">` 默认遮蔽显示 (`****-ABCD`)，旁边带 toggle-visibility 按钮（👁️图标）。权限标签 "读写模式" 用徽章样式。

### 10. 系统终端（移入 Settings 视图）

**选择**: 固定高度 200px，黑底 `#0a0a0a`，绿字 `#4ade80`，monospace。自动滚底。

## Risks / Trade-offs

- **5 个视图 DOM 全部预渲染** → 简单但增加初始 DOM 大小。可接受（纯静态页面，无性能瓶颈）
- **Hash 路由不支持嵌套** → v7.0 扁平路由足够，无嵌套需求
- **侧边栏在极窄屏（<600px）占用过多空间** → 折叠为底部 tab bar 或完全隐藏+汉堡菜单
- **Canvas 图表 HiDPI 模糊** → `devicePixelRatio` 缩放
- **Kill Switch 仅前端状态** → 标注为模拟功能，真实实现需后端支持
