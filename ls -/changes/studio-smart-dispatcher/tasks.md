## 1. 推荐面板 UI

- [x] 1.1 在 `index.html` `.studio-container` 上方添加推荐面板 HTML
- [x] 1.2 在 `style.css` 添加 `.recommendation-*` 样式 (暗黑玻璃态 + 方向色发光)

---

## 2. 策略路由引擎

- [x] 2.1 在 `strategy-generator.js` 添加 `validateLiquidity(bid, ask)` 熔断
- [x] 2.2 添加 `generateBullPutSpread(spot, puts, exp)` — 2 腿
- [x] 2.3 添加 `generateBearCallSpread(spot, calls, exp)` — 2 腿
- [x] 2.4 添加 `autoAssembleStrategy(ticker, direction, currentBP, chainData, exp)` 路由 + 资金熔断

---

## 3. 视图联动

- [x] 3.1 在 `strategy_studio.js` 添加 `loadRecommendations()` 获取+渲染推荐面板
- [x] 3.2 添加 `onRecommendationCardClick(ticker, direction)` 事件流
- [x] 3.3 事件委托绑定到推荐面板

---

## 4. 验证

- [x] 4.1 引擎测试通过 (47/47)
- [x] 4.2 Docker build + deploy
- [ ] 4.3 浏览器验证
