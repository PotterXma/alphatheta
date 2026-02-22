## 1. CSS: 删除旧样式 + 写入新暗黑玻璃态样式

- [x] 1.1 删除 `style.css` 中旧 Studio CSS (~340 行)
- [x] 1.2 添加 `--studio-*` CSS 变量 (accent, glow, profit, loss, bg, border, text, muted, input-bg)
- [x] 1.3 `.studio-container` CSS Grid 两栏布局 (`1fr 400px`) + `@media (max-width: 1024px)` 响应式
- [x] 1.4 `.studio-toolbar` Flexbox + 模板 select 暗色 + 主按钮青色发光 + 幽灵清空按钮
- [x] 1.5 Form Reset: `#view-signal select/input/button` 统一暗色圆角控件
- [x] 1.6 `.leg-row` Flexbox 横向卡片 + 微光边框 + `:hover` 提亮
- [x] 1.7 `.leg-action-toggle` 胶囊 Buy/Sell + `.leg-type-btn` Call/Put/Stock Toggle
- [x] 1.8 `.chart-card` 青色发光边框 + `#payoffChart` 320px
- [x] 1.9 `.metrics-grid` 2×2 网格 + `.metric-box` 毛玻璃 + Net Premium span-2 大号字
- [x] 1.10 保留 `.mini-chain-panel` 系列 CSS (已重写为 studio-token 风格)

---

## 2. HTML: 重写 view-signal 内 Strategy Studio DOM

- [x] 2.1 重写 `<section id="view-signal">` 内部 DOM
- [x] 2.2 `.studio-container` 包裹左右两栏
- [x] 2.3 左栏: `.studio-toolbar` (select#studioTemplateSelect + btn#studioAddLeg + btn#studioClearAll)
- [x] 2.4 左栏: `.studio-glass` > `.legs-header` + `div#legsContainer`
- [x] 2.5 右栏: `.chart-card` > `div#payoffChart`
- [x] 2.6 右栏: `.metrics-grid` > `.metric-box` × 5
- [x] 2.7 验证所有 DOM ID 保持不变

---

## 3. JS: renderLegs() 模板适配

- [x] 3.1 `.leg-toggle` → `.leg-action-toggle`
- [x] 3.2 `scenario-value mono bullish/bearish` → `metric-value profit/loss`
- [x] 3.3 验证事件委托正常工作 (build passes)

---

## 4. 构建验证

- [x] 4.1 `docker compose build web && docker compose up -d web`
- [x] 4.2 Curl 验证: HTML=20 class refs, CSS=29 var refs, JS=3 class refs
- [x] 4.3 47/47 engine tests passed
- [ ] 4.4 浏览器手动验证: 毛玻璃效果、颜色、布局、交互
