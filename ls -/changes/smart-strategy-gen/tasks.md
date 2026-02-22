## 1. 核心生成器模块 `strategy-generator.js`

- [x] 1.1 创建 `js/utils/strategy-generator.js`
- [x] 1.2 实现 `findClosestStrike(chain, targetPrice)` — 离散寻址
- [x] 1.3 实现 `validateQuote(contract, side)` — Bid/Ask 验证
- [x] 1.4 实现 `generateIronCondor(spotPrice, optionChainData)` — 4 步构建
- [x] 1.5 实现 `autoSuggestNeutralStrategy(tickerData, optionChainData)` — 环境分发
- [x] 1.6 导出所有函数 (ESM)

---

## 2. UI 联动 `strategy_studio.js`

- [x] 2.1 在 `index.html` toolbar 添加 `[⚡ 智能组装]` 按钮 + `#studioStatusBar`
- [x] 2.2 在 `style.css` 添加 `.studio-btn-ai` 紫色渐变 + `.studio-status-bar` loading/success/warning 态
- [x] 2.3 在 `strategy_studio.js` 添加 `onAutoSuggest()` 异步流程
- [x] 2.4 接入 `fetchExpirations` + `fetchOptionChainMini` 获取真实数据
- [x] 2.5 成功: 覆写 `currentLegs` + `renderLegs()` + `recalcPayoff()` + 成功提示
- [x] 2.6 失败: 黄色警告提示 + 保留空白构建器

---

## 3. 测试与验证

- [ ] 3.1 引擎测试通过 (47/47)
- [ ] 3.2 Docker build + deploy
- [ ] 3.3 浏览器验证: 点击智能组装按钮
