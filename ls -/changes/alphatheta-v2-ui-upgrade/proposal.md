## Why

AlphaTheta v1.0 是单一平铺式仪表盘，随着功能扩展（资讯、沙盒、监控、报告），平铺布局不可扩展。v7.0 将其重构为侧边栏驱动的 SPA 架构，按功能模块解耦为 5 个视图，实现企业级量化交易中枢的完整工作流：从宏观感知 → 信号执行 → 策略推演 → 生命周期跟踪 → 系统运维。i18n 国际化覆盖全部视图。

## What Changes

- **重构** 全局布局从平铺式改为侧边栏 (Sidebar) + 主工作区 (Main Content) SPA 路由结构
- **新增** 5 个路由视图：Dashboard、Signal & Execution、Sandbox、Lifecycle & Reports、Settings
- **新增** 纯前端 i18n 国际化系统（EN/ZH 动态切换）
- **新增** 顶部跑马灯 + 全局熔断按钮 (Kill Switch)
- **新增** 保证金使用率进度条（60% 阈值警戒）
- **新增** 策略推演沙盒（参数实时联动计算）
- **新增** 期权生命周期跟踪 + 一键展期 (1-Click Roll) + 响应式卡片流降级
- **新增** 运行绩效报告（自动化次数、累计权利金、微型趋势图）
- **新增** Settings 视图：API 密钥保险箱 + 系统日志终端
- **保持** 宏观雷达 (VIX/SPY/QQQ)、信号引擎 + Rationale 的核心功能

## Capabilities

### New Capabilities

- `spa-layout`: 侧边栏路由 + 主工作区视图切换的 SPA 布局系统
- `i18n-system`: 纯前端 i18n——`t(key)` 翻译函数、语言状态管理、全局重渲染
- `news-ticker`: 顶部跑马灯，CSS 匀速滚动，i18n 驱动
- `kill-switch`: 全局紧急暂停按钮，切换交易引擎状态
- `dashboard-view`: 大盘概览视图——资产净值、保证金使用率、宏观雷达卡片
- `signal-view`: 信号与执行视图——AI 指令面板 + 执行理由 (Rationale)
- `sandbox-view`: 策略沙盒视图——参数控制 + 实时推演计算
- `lifecycle-view`: 全程跟踪视图——持仓表格/卡片流 + 一键展期 + 绩效报告
- `settings-view`: 系统设置视图——API 密钥保险箱 + 系统日志终端

### Modified Capabilities

_无现有 specs_

## Impact

- **`index.html`**: 全面重构——侧边栏导航 + 5 个视图容器 + 跑马灯 + Kill Switch
- **`style.css`**: 全面重构——侧边栏样式、视图切换、进度条、卡片流响应式、终端样式、滑块控件
- **`app.js`**: 全面重构——SPA 路由、i18n 系统、Canvas 图表、沙盒计算、视图渲染函数
- **无外部依赖**: 保持纯 HTML/CSS/JS 零依赖架构
