// ================================================================
// AlphaTheta v7.0 – Master Dashboard Logic
// ================================================================

// ── i18n Dictionary ──────────────────────────────────────────────
const I18N = {
  zh: {
    nav_status_synced: "数据已同步",
    nav_dashboard: "大盘概览",
    nav_signal: "信号与执行",

    nav_tracking: "全程跟踪与报告",
    nav_settings: "系统设置",
    kill_switch: "紧急暂停",
    halt_msg: "交易引擎已暂停",
    portfolio_net: "账户总净值",
    portfolio_cash: "可用购买力",
    margin_util: "保证金使用率",
    radar_vix: "恐慌指数与波动率",
    radar_spy: "标普500 状态",
    radar_qqq: "纳指100 状态",
    signal_title: "建议操作指令",
    signal_rationale: "AI 策略执行理由",
    signal_btn: "通过 API 自动执行",
    sig_ticker: "交易标的",
    sig_strike: "行权价",
    sig_expiry: "到期日",
    sig_quantity: "数量",
    sig_capital: "资金变动",

    pos_title: "当前活跃持仓",
    pos_col_ticker: "交易标的",
    pos_col_type: "类型",
    pos_col_strike: "行权价",
    pos_col_expiry: "到期日",
    pos_col_dte: "剩余天数",
    pos_col_premium: "初始权利金",
    pos_col_current: "当前价值",
    pos_col_pnl: "盈亏比例",
    pos_col_actions: "操作",
    report_title: "自动化运行绩效报告",
    report_saved_ops: "本月系统自动执行次数",
    report_premium: "累计收取权利金",
    settings_api: "API 密钥保险箱",
    settings_permission: "读写模式",
    terminal_title: "系统健康终端",
    roll_btn: "展期",
    cro_approved: "✓ 风控通过",
    cro_rejected: "✗ 风控否决",
    cro_plan_title: "执行方案",
    cro_order_type: "订单类型",
    cro_start_price: "起始限价",
    cro_floor_price: "底线限价",
    cro_gross_yield: "毛年化收益",
    cro_net_yield: "税后净年化",
    cro_bull_title: "📈 暴涨应对 (+15%)",
    cro_bear_title: "📉 暴跌防守 (-20%)",
    cro_whipsaw_title: "🌊 宽幅震荡陷阱",
    timing_title: "推荐操作",
    timing_buy_stock: "仅买入正股",
    timing_sell_call: "仅卖出看涨期权",
    timing_sell_put: "仅卖出看跌期权",
    timing_buy_write: "组合建仓 (Buy-Write)",
    timing_hold: "观望",
    timing_rsi: "RSI",
    timing_vix: "VIX",
    timing_pos_holding: "已持仓",
    timing_pos_cash: "纯现金",
    ticker_news: [
      "美联储会议纪要公布，暗示年内可能维持当前利率水平",
      "标普500指数突破历史新高，科技股领涨",
      "VIX 恐慌指数回落至 18 以下，市场情绪趋于稳定",
      "最新非农就业数据超出预期，经济韧性依旧强劲",
    ],
  },
  en: {
    nav_status_synced: "API Synced",
    nav_dashboard: "Dashboard",
    nav_signal: "Signal & Execute",

    nav_tracking: "Lifecycle & Reports",
    nav_settings: "Settings",
    kill_switch: "Halt Trading",
    halt_msg: "Trading Engine Halted",
    portfolio_net: "Total Net Value",
    portfolio_cash: "Buying Power",
    margin_util: "Margin Utilization",
    radar_vix: "VIX & IV Rank",
    radar_spy: "SPY Status",
    radar_qqq: "QQQ Status",
    signal_title: "Actionable Signal",
    signal_rationale: "Execution Rationale",
    signal_btn: "Execute via API",
    sig_ticker: "Ticker",
    sig_strike: "Strike",
    sig_expiry: "Expiry",
    sig_quantity: "Quantity",
    sig_capital: "Capital Impact",

    pos_title: "Active Positions",
    pos_col_ticker: "Ticker",
    pos_col_type: "Type",
    pos_col_strike: "Strike",
    pos_col_expiry: "Expiry",
    pos_col_dte: "DTE",
    pos_col_premium: "Init Premium",
    pos_col_current: "Current",
    pos_col_pnl: "P&L",
    pos_col_actions: "Actions",
    report_title: "Automated Performance Report",
    report_saved_ops: "Automated Ops this Month",
    report_premium: "Total Premium Collected",
    settings_api: "API Key Vault",
    settings_permission: "Read-Write",
    terminal_title: "System Terminal",
    roll_btn: "Roll",
    cro_approved: "✓ Risk Approved",
    cro_rejected: "✗ Risk Rejected",
    cro_plan_title: "Execution Plan",
    cro_order_type: "Order Type",
    cro_start_price: "Starting Limit",
    cro_floor_price: "Floor Limit",
    cro_gross_yield: "Gross Annualized",
    cro_net_yield: "Net After Tax",
    cro_bull_title: "📈 Bullish Surge (+15%)",
    cro_bear_title: "📉 Bearish Crash (-20%)",
    cro_whipsaw_title: "🌊 Whipsaw / Gamma Trap",
    timing_title: "Recommended Action",
    timing_buy_stock: "Buy Stock ONLY",
    timing_sell_call: "Sell Call ONLY",
    timing_sell_put: "Sell Put ONLY",
    timing_buy_write: "Buy-Write",
    timing_hold: "Hold",
    timing_rsi: "RSI",
    timing_vix: "VIX",
    timing_pos_holding: "Holding",
    timing_pos_cash: "Cash Only",
    ticker_news: [
      "Fed minutes released, hinting rates may hold steady this year",
      "S&P 500 breaks all-time high, tech stocks lead the charge",
      "VIX drops below 18, market sentiment stabilizes",
      "Non-farm payrolls beat expectations, economy remains resilient",
    ],
  },
};

// ── Mock Data ────────────────────────────────────────────────────
// $100,000 初始空仓状态 — API 返回真实数据后在 fetchDashboardData() 中覆盖
const MOCK_DATA = {
  portfolio: { totalValue: 100000, cash: 100000, marginUsed: 0 },
  radar: {
    vix: 0,
    ivRank: { qqq: 0, spy: 0 },
    spy: { price: 0, sma200: 0, trend: "--" },
    qqq: { price: 0, sma200: 0, trend: "--" },
  },
  currentSignal: {
    actionType: "",
    action: "等待扫描引擎信号...",
    ticker: "--",
    strike: 0,
    limitPrice: 0,
    expiration: "--",
    quantity: "--",
    capitalImpact: "$0.00",
    isBuy: false,
    dte: 0,
    actionTypeSell: false,
    rationale: ["全天候扫描引擎运行中，等待 LEAPS 黄金坑信号..."],
  },
  marketContext: {
    vix: 0,
    dataLatency: 0,
    bid: 0,
    ask: 0,
    projectedMarginUtil: 0,
    daysToExDividend: 0,
    delta: 0,
    gamma: 0,
    isITM: false,
    actionType: "Hold",
    hv_30d: 0,
    iv_rank: 0,
    is_wash_sale_risk: false,
    estTaxDrag: 0,
    rsi_14: 50,
    distance_to_sma200: 0,
    current_position: "Cash Only",
    available_cash: 100000,
    put_strike: 0,
    put_premium: 0,
  },
  activePositions: [],
  tracking: { automatedOps: 0, totalPremiumCollected: 0 },
  systemLogs: [
    "[System] AlphaTheta v2 初始化完成",
    "[Engine] 扫描引擎已启动，监控核心票池",
    "[Portfolio] 初始资金 $100,000 已就绪",
  ],
  equityCurve: [100000],
};

// ── State ────────────────────────────────────────────────────────
const APP_STATE = {
  lang: "zh",
  currentView: "dashboard",
  isHalted: false,
  globalActiveTicker: sessionStorage.getItem("globalActiveTicker") || "SPY",
};

// ══════════════════════════════════════════════════════════════════
// GLOBAL TICKER STATE — 跨页面标的联动
// ══════════════════════════════════════════════════════════════════

function setGlobalTicker(ticker) {
  APP_STATE.globalActiveTicker = ticker;
  sessionStorage.setItem("globalActiveTicker", ticker);
  window.dispatchEvent(new CustomEvent("ticker-changed", { detail: { ticker } }));
  // Update all ticker badges
  const display = $("globalTickerDisplay");
  if (display) display.textContent = ticker;

  console.log(`[GlobalTicker] → ${ticker}`);
}

function getGlobalTicker() {
  return APP_STATE.globalActiveTicker;
}

// ── Helpers ──────────────────────────────────────────────────────
function $(id) {
  return document.getElementById(id);
}
function pad(n) {
  return String(n).padStart(2, "0");
}
function formatMoney(v) {
  return (
    "$" +
    Number(v).toLocaleString("en-US", {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    })
  );
}
function pctDiff(price, sma) {
  return (((price - sma) / sma) * 100).toFixed(2);
}
function t(key) {
  const dict = I18N[APP_STATE.lang];
  return dict && dict[key] !== undefined ? dict[key] : key;
}

// ── i18n Apply ───────────────────────────────────────────────────
function applyI18n() {
  document.querySelectorAll("[data-i18n]").forEach((el) => {
    const key = el.getAttribute("data-i18n");
    const val = t(key);
    if (typeof val === "string") el.textContent = val;
  });
}

// ── Clock ────────────────────────────────────────────────────────
function updateClock() {
  const now = new Date();
  $("navClock").textContent = `${now.getFullYear()}-${pad(
    now.getMonth() + 1
  )}-${pad(now.getDate())} ${pad(now.getHours())}:${pad(now.getMinutes())}`;
}

// ── SPA Routing ──────────────────────────────────────────────────
const VIEWS = ["dashboard", "signal", "lifecycle", "settings"];

function navigateTo(viewId) {
  if (!VIEWS.includes(viewId)) viewId = "dashboard";
  APP_STATE.currentView = viewId;

  // Hide all views
  VIEWS.forEach((v) => {
    const el = $(`view-${v}`);
    if (el) el.classList.toggle("hidden", v !== viewId);
  });

  // Update sidebar
  document.querySelectorAll(".sidebar-item").forEach((item) => {
    item.classList.toggle("active", item.dataset.view === viewId);
  });

  location.hash = viewId;

  // Render canvas if switching to lifecycle
  if (viewId === "lifecycle") {
    setTimeout(renderEquityChart, 50);
  }
}

function initRouting() {
  // Sidebar clicks
  document.querySelectorAll(".sidebar-item").forEach((item) => {
    item.addEventListener("click", () => navigateTo(item.dataset.view));
  });

  // Hash change
  window.addEventListener("hashchange", () => {
    const hash = location.hash.replace("#", "");
    navigateTo(hash);
  });

  // Initial route
  const hash = location.hash.replace("#", "");
  navigateTo(VIEWS.includes(hash) ? hash : "dashboard");
}

// ── Ticker ───────────────────────────────────────────────────────
function renderTicker() {
  const news = t("ticker_news");
  if (!Array.isArray(news)) return;
  const items = news
    .map(
      (n) =>
        `<span class="ticker-dot">●</span><span>${n}</span>`
    )
    .join("");
  // Duplicate for seamless loop
  $("tickerTrack").innerHTML = items + items;
}

// ── Kill Switch ──────────────────────────────────────────────────
function setupKillSwitch() {
  $("killSwitchBtn").addEventListener("click", () => {
    APP_STATE.isHalted = !APP_STATE.isHalted;
    $("killSwitchBtn").classList.toggle("halted", APP_STATE.isHalted);
    $("haltOverlay").classList.toggle("active", APP_STATE.isHalted);
    const btn = $("executeBtn");
    if (btn) btn.disabled = APP_STATE.isHalted;
  });
}

// ── Dashboard ────────────────────────────────────────────────────

// 从后端 /dashboard/sync 拉取真实行情 + AI 策略信号, 全量替换 MOCK_DATA
async function fetchDashboardData() {
  try {
    const resp = await fetch("/api/v1/dashboard/sync");
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    const data = await resp.json();

    if (data.error) {
      console.warn("⚠ Backend error:", data.error);
    }

    // ── 1. 覆盖市场行情 ──
    const mkt = data.market || {};
    MOCK_DATA.radar.vix = mkt.vix || MOCK_DATA.radar.vix;
    MOCK_DATA.radar.spy.price = mkt.spy?.price || MOCK_DATA.radar.spy.price;
    MOCK_DATA.radar.spy.sma200 = mkt.spy?.sma200 || MOCK_DATA.radar.spy.sma200;
    MOCK_DATA.radar.spy.trend = (mkt.spy?.sma200_distance || 0) >= 0 ? "bullish" : "bearish";
    MOCK_DATA.radar.qqq.price = mkt.qqq?.price || MOCK_DATA.radar.qqq.price;
    MOCK_DATA.radar.ivRank.spy = Math.round(mkt.spy?.rsi_14 || 50);

    // ── 2. 覆盖市场上下文 (策略引擎输入) ──
    MOCK_DATA.marketContext.vix = mkt.vix || MOCK_DATA.marketContext.vix;
    MOCK_DATA.marketContext.rsi_14 = mkt.spy?.rsi_14 || 50;
    MOCK_DATA.marketContext.distance_to_sma200 = mkt.spy?.sma200_distance || 0;

    // ── 3. 覆盖投资组合 ──
    if (data.portfolio) {
      MOCK_DATA.portfolio.totalValue = data.portfolio.totalValue || MOCK_DATA.portfolio.totalValue;
      MOCK_DATA.portfolio.cash = data.portfolio.cash || MOCK_DATA.portfolio.cash;
      MOCK_DATA.portfolio.marginUsed = data.portfolio.marginUsed || MOCK_DATA.portfolio.marginUsed;
    }

    // ── 4. 覆盖 AI 策略信号 (来自 evaluate_market_entry) ──
    if (data.signal && data.signal.action_type !== "Hold") {
      const sig = data.signal;
      const isZh = APP_STATE.lang === "zh";
      // 映射策略引擎输出到前端信号卡片
      MOCK_DATA.currentSignal.actionType = sig.action_type;
      MOCK_DATA.currentSignal.action = sig.reasoning || MOCK_DATA.currentSignal.action;
      if (sig.execution?.strike) MOCK_DATA.currentSignal.strike = sig.execution.strike;
      if (sig.execution?.expiration) MOCK_DATA.currentSignal.expiration = sig.execution.expiration;
    }

    // ── 5. 覆盖基本面 + 情景推演 (新增) ──
    if (data.fundamentals) {
      MOCK_DATA.fundamentals = data.fundamentals;
    }
    if (data.scenario) {
      MOCK_DATA.scenario = data.scenario;
    }
    if (data.signal?.ai_reasons) {
      MOCK_DATA.signal = MOCK_DATA.signal || {};
      MOCK_DATA.signal.ai_reasons = data.signal.ai_reasons;
    }
    if (data.risk) {
      MOCK_DATA.risk = data.risk;
    }

    console.log("📊 Dashboard synced with real data + AI signal", data);
    renderAll();
  } catch (err) {
    console.warn("⚠ Dashboard sync failed, using cached data:", err.message);
    // 显示错误提示 (非阻塞)
    const toast = document.createElement("div");
    toast.className = "toast toast-error";
    toast.textContent = "⚠ 真实行情获取失败，当前显示缓存数据";
    toast.style.cssText = "position:fixed;top:80px;right:20px;background:#ff4757;color:#fff;padding:12px 20px;border-radius:8px;z-index:9999;font-size:14px;animation:fadeIn 0.3s;";
    document.body.appendChild(toast);
    setTimeout(() => toast.remove(), 5000);
  }
}

function renderDashboard() {
  const { portfolio, radar } = MOCK_DATA;

  // Portfolio
  $("portfolioNet").textContent = formatMoney(portfolio.totalValue);
  $("portfolioCash").textContent = formatMoney(portfolio.cash);

  // Margin
  const marginPct = portfolio.marginUsed;
  const marginBar = $("marginBar");
  marginBar.style.width = marginPct + "%";
  marginBar.classList.toggle("warning", marginPct >= 60);
  $("marginValue").textContent = marginPct + "%";

  // VIX
  const vixCard = $("cardVix");
  $("vixValue").textContent = radar.vix.toFixed(1);
  vixCard.classList.remove("vix-low", "vix-mid", "vix-high");
  if (radar.vix < 15) {
    vixCard.classList.add("vix-low");
    $("vixSub").textContent =
      APP_STATE.lang === "zh" ? "低波动 (< 15)" : "Low Vol (< 15)";
    $("vixSub").className = "radar-card-sub trend-bull";
  } else if (radar.vix <= 25) {
    vixCard.classList.add("vix-mid");
    $("vixSub").textContent =
      APP_STATE.lang === "zh" ? "常态波动 (15-25)" : "Normal (15-25)";
    $("vixSub").className = "radar-card-sub";
  } else {
    vixCard.classList.add("vix-high");
    $("vixSub").textContent =
      APP_STATE.lang === "zh" ? "⚠ 高波动 (> 25)" : "⚠ High Vol (> 25)";
    $("vixSub").className = "radar-card-sub trend-bear";
  }
  $("ivRankDisplay").textContent = `IV Rank: QQQ ${radar.ivRank.qqq}% | SPY ${radar.ivRank.spy}%`;

  // SPY
  const spyPct = pctDiff(radar.spy.price, radar.spy.sma200);
  $("spyPrice").textContent = formatMoney(radar.spy.price);
  const spyArrow = spyPct >= 0 ? "▲" : "▼";
  const spyClass =
    radar.spy.trend === "bullish" ? "trend-bull" : "trend-bear";
  $("spySma").innerHTML = `SMA200 ${formatMoney(
    radar.spy.sma200
  )} &nbsp;|&nbsp; <span class="${spyClass}">${spyArrow} ${spyPct > 0 ? "+" : ""
    }${spyPct}%</span>`;

  // QQQ
  const qqqPct = pctDiff(radar.qqq.price, radar.qqq.sma200);
  $("qqqPrice").textContent = formatMoney(radar.qqq.price);
  const qqqArrow = qqqPct >= 0 ? "▲" : "▼";
  const qqqClass =
    radar.qqq.trend === "bullish" ? "trend-bull" : "trend-bear";
  $("qqqSma").innerHTML = `SMA200 ${formatMoney(
    radar.qqq.sma200
  )} &nbsp;|&nbsp; <span class="${qqqClass}">${qqqArrow} ${qqqPct > 0 ? "+" : ""
    }${qqqPct}%</span>`;

  // ── Render Charts (delegated to renderCharts.js) ──
  if (typeof initDashboardCharts === "function") {
    initDashboardCharts();
  }
}

// ── Signal ───────────────────────────────────────────────────────
// 全局信号数据 (从 /dashboard/sync 提取)
let SIGNAL_DATA = null;

async function fetchSignalData() {
  try {
    const resp = await fetch("/api/v1/dashboard/sync");
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    const data = await resp.json();

    // 转换 dashboard 响应为统一信号数据格式
    const fund = data.fundamentals || {};
    const scen = data.scenario || {};
    const risk = data.risk || {};
    const sig = data.signal || {};
    const mkt = data.market || {};

    SIGNAL_DATA = {
      ticker: sig.target_ticker || "SPY",
      current_price: mkt.spy?.price || 0,
      signal: {
        action_type: sig.action_type || "hold",
        confidence: sig.confidence || 0.5,
        reasoning: sig.reasoning || sig.scene_label || "",
        scene_label: sig.scene_label || "",
        execution: {
          contract_symbol: sig.execution_details?.contract_symbol || null,
          strike: sig.execution_details?.strike_price || 0,
          expiration_date: sig.execution_details?.expiration || null,
          premium: sig.execution_details?.estimated_premium || 0,
          delta: sig.execution_details?.actual_delta || 0,
          dte: sig.execution_details?.dte || 30,
          quantity_stock: 100,
          quantity_option: 1,
          net_cost: sig.execution_details?.strike_price
            ? (mkt.spy?.price || 0) * 100 - (sig.execution_details?.estimated_premium || 0) * 100
            : 0,
          open_interest: sig.execution_details?.open_interest || 0,
          volume: sig.execution_details?.volume || 0,
        },
      },
      ai_reasons: {
        fundamental: {
          pe_ratio: fund.trailing_pe || fund.forward_pe || null,
          market_cap: _formatCap(fund.market_cap),
          market_cap_label: fund.market_cap_label || "N/A",
          earnings_date: fund.earnings_date || null,
          ex_dividend_date: fund.ex_dividend_date || null,
          dividend_yield: fund.dividend_yield || 0,
          recommendation: fund.recommendation_label || "N/A",
          diagnosis: fund.diagnosis || [],
        },
        technical: {
          rsi_14: mkt.spy?.rsi_14 || 50,
          sma200: mkt.spy?.sma200 || null,
          sma200_status: mkt.spy?.sma200_distance >= 0
            ? `高于 200 日均线 +${(mkt.spy?.sma200_distance || 0).toFixed(1)}%`
            : `低于 200 日均线 ${(mkt.spy?.sma200_distance || 0).toFixed(1)}%`,
          sma200_distance: mkt.spy?.sma200_distance || 0,
          vix: mkt.vix || 0,
        },
        scenario: {
          strategy: scen.strategy || "N/A",
          break_even: scen.break_even || 0,
          max_profit: scen.max_profit || 0,
          annualized_roi: scen.annualized_roi || 0,
          summary: scen.summary || "",
          scenarios: scen.scenarios || [],
          up_scenario: scen.scenarios?.[0]?.description || "",
          down_scenario: scen.scenarios?.[scen.scenarios?.length - 1]?.description || "",
        },
      },
      risk_scenarios: (risk.scenarios || []).map((s) => ({
        title: s.scenario_name || s.title || "",
        trigger: s.trigger_condition || s.trigger || "",
        action: s.action_plan || s.action || "",
        tag_type: s.tag_type || "info",
        threshold_price: s.threshold_price || null,
        priority: s.priority || 5,
      })),
      risk_summary: {
        implied_move_1sigma: risk.implied_move_1sigma || 0,
        implied_move_2sigma: risk.implied_move_2sigma || 0,
        atr_stop_loss: risk.atr_stop_loss || 0,
        upside_1sigma: risk.upside_1sigma || 0,
        downside_1sigma: risk.downside_1sigma || 0,
      },
    };

    console.log("🎯 Signal data synced from dashboard", SIGNAL_DATA);
    renderSignal();
  } catch (err) {
    console.warn("⚠ Signal data fetch failed:", err.message);
  }
}

function _formatCap(cap) {
  if (!cap) return "N/A";
  if (cap >= 1e12) return `$${(cap / 1e12).toFixed(1)}T`;
  if (cap >= 1e9) return `$${(cap / 1e9).toFixed(1)}B`;
  if (cap >= 1e6) return `$${(cap / 1e6).toFixed(0)}M`;
  return `$${cap.toLocaleString()}`;
}

function renderSignal() {
  const sig = MOCK_DATA.currentSignal;
  const sd = SIGNAL_DATA; // unified signal data (may be null on first load)

  // ── 左侧: 信号卡片 ──
  const badge = $("signalBadge");
  if (badge) badge.textContent = sd?.signal?.reasoning || sig.action || "--";

  const tickerEl = $("sigTicker");
  if (tickerEl) tickerEl.textContent = sd?.ticker || sig.ticker || "--";

  const strikeEl = $("sigStrike");
  if (strikeEl) strikeEl.textContent = formatMoney(sd?.signal?.execution?.strike || sig.strike || 0);

  const expiryEl = $("sigExpiry");
  if (expiryEl) expiryEl.textContent = sd?.signal?.execution?.expiration_date || sig.expiration || "--";

  const qtyEl = $("sigQuantity");
  if (qtyEl) qtyEl.textContent = sig.quantity || "100 股 + 1 张合约";

  const capEl = $("sigCapital");
  if (capEl) capEl.textContent = formatMoney(sd?.signal?.execution?.net_cost || 49850);

  // ── Net Debit ──
  const netDebitEl = $("sigNetDebit");
  if (netDebitEl) {
    const netCost = sd?.signal?.execution?.net_cost || 0;
    if (netCost > 0) {
      netDebitEl.textContent = formatMoney(netCost);
      netDebitEl.classList.add("glow-text");
    }
  }

  // ── 按钮状态 ──
  const btn = $("executeBtn");
  if (btn) {
    btn.classList.remove("btn-buy", "btn-sell");
    const isHold = sd?.signal?.action_type === "hold";
    btn.classList.add(isHold ? "btn-sell" : "btn-buy");
    btn.disabled = APP_STATE.isHalted || isHold;
  }

  // ── 三段式分析面板 (安全渲染) ──
  renderAnalysisPanelSafe();

  // ── 动态风控面板 (安全渲染) ──
  renderRiskPanelSafe();

  // ── Timing + CRO (保持原有逻辑) ──
  const timingResult = evaluateTimingDecision();
  renderTimingPanel(timingResult);
  const croResult = evaluateTradeProposal();
  renderCRO(croResult);
}

// ── 安全版三段式分析面板 ──
function renderAnalysisPanelSafe() {
  const sd = SIGNAL_DATA;
  const fund = sd?.ai_reasons?.fundamental;
  const tech = sd?.ai_reasons?.technical;
  const scen = sd?.ai_reasons?.scenario;

  // ── 区块 A: 基本面 ──
  const fundTagsEl = document.getElementById("fundamentalTags");
  if (fundTagsEl) {
    const tags = [];
    if (fund?.market_cap && fund.market_cap !== "N/A") {
      tags.push({ text: `市值 ${fund.market_cap} (${fund.market_cap_label || ""})`, cls: "" });
    }
    if (fund?.pe_ratio != null) {
      const peWarn = fund.pe_ratio > 100 ? " tag-warn" : fund.pe_ratio < 15 ? " tag-good" : "";
      tags.push({ text: `PE: ${fund.pe_ratio}`, cls: peWarn });
    }
    if (fund?.recommendation && fund.recommendation !== "N/A") {
      const recCls = fund.recommendation.includes("Buy") ? " tag-good" : fund.recommendation.includes("Sell") ? " tag-danger" : "";
      tags.push({ text: `华尔街评级: ${fund.recommendation}`, cls: recCls });
    }
    if (fund?.dividend_yield && fund.dividend_yield > 0) {
      tags.push({ text: `股息率: ${(fund.dividend_yield * 100).toFixed(2)}%`, cls: "" });
    }
    if (fund?.earnings_date) tags.push({ text: `📅 财报日: ${fund.earnings_date}`, cls: "" });
    if (fund?.ex_dividend_date) tags.push({ text: `📅 除息日: ${fund.ex_dividend_date}`, cls: "" });

    if (tags.length > 0) {
      fundTagsEl.innerHTML = tags
        .map((t) => `<span class="analysis-tag${t.cls}">${t.text}</span>`)
        .join("");
    } else {
      fundTagsEl.innerHTML = '<span class="analysis-tag">等待数据同步...</span>';
    }
  }

  // ── 区块 B: 技术面 ──
  const techTagsEl = document.getElementById("technicalTags");
  if (techTagsEl) {
    const tags = [];
    if (tech?.rsi_14 != null) {
      const rsiCls = tech.rsi_14 > 70 ? " tag-danger" : tech.rsi_14 < 30 ? " tag-good" : "";
      tags.push({ text: `RSI-14: ${tech.rsi_14}`, cls: rsiCls });
    }
    if (tech?.sma200_status && tech.sma200_status !== "N/A") {
      const smaCls = tech.sma200_distance >= 0 ? " tag-good" : " tag-warn";
      tags.push({ text: tech.sma200_status, cls: smaCls });
    }
    if (tech?.vix != null) {
      const vixCls = tech.vix > 30 ? " tag-danger" : tech.vix > 20 ? " tag-warn" : "";
      tags.push({ text: `VIX: ${tech.vix}`, cls: vixCls });
    }

    if (tags.length > 0) {
      techTagsEl.innerHTML = tags
        .map((t) => `<span class="analysis-tag${t.cls}">${t.text}</span>`)
        .join("");
    } else {
      techTagsEl.innerHTML = '<span class="analysis-tag">等待数据同步...</span>';
    }
  }

  // ── 区块 C: 情景推演 ──
  const summaryEl = document.getElementById("scenarioSummary");
  const listEl = document.getElementById("scenarioList");
  if (summaryEl) {
    summaryEl.textContent = scen?.summary || "等待信号生成情景推演...";
  }
  if (listEl && scen?.scenarios?.length > 0) {
    listEl.innerHTML = scen.scenarios
      .map((s) => {
        const colorCls = s.color === "green" ? "scenario-green" : s.color === "red" ? "scenario-red" : "";
        const pnlSign = s.pnl >= 0 ? "+" : "";
        const pnlCls = s.pnl >= 0 ? "pnl-positive" : "pnl-negative";
        return `
        <div class="scenario-item ${colorCls}">
          <div class="scenario-item-header">
            <span class="scenario-item-icon">${s.icon || ""}</span>
            <span class="scenario-item-label">${s.label || ""}</span>
            <span class="scenario-item-pnl ${pnlCls}">${pnlSign}$${Math.abs(s.pnl || 0).toLocaleString("en-US", { minimumFractionDigits: 2 })}</span>
          </div>
          <div class="scenario-item-desc">${s.description || ""}</div>
        </div>`;
      })
      .join("");
  } else if (listEl) {
    listEl.innerHTML = '<div class="scenario-item"><div class="scenario-item-desc">等待数据同步...</div></div>';
  }
}

// ── 安全版风控面板 ──
function renderRiskPanelSafe() {
  const sd = SIGNAL_DATA;
  const riskSummary = sd?.risk_summary;
  const riskScenarios = sd?.risk_scenarios;

  // Summary bar
  const im1El = document.getElementById("riskIM1");
  const im2El = document.getElementById("riskIM2");
  const atrEl = document.getElementById("riskATR");
  if (im1El) im1El.textContent = riskSummary ? `1σ: ±$${riskSummary.implied_move_1sigma?.toFixed(2) || "--"}` : "1σ: --";
  if (im2El) im2El.textContent = riskSummary ? `2σ: ±$${riskSummary.implied_move_2sigma?.toFixed(2) || "--"}` : "2σ: --";
  if (atrEl) atrEl.textContent = riskSummary ? `ATR Stop: $${riskSummary.atr_stop_loss?.toFixed(2) || "--"}` : "ATR: --";

  // Scenario cards
  const grid = document.getElementById("riskScenarioGrid");
  if (!grid) return;

  if (riskScenarios?.length > 0) {
    grid.innerHTML = riskScenarios
      .map((s) => {
        const tagCls = `risk-${s.tag_type || "info"}`;
        const priceCls = `price-${s.tag_type || "info"}`;
        const priceHtml = s.threshold_price
          ? `<span class="risk-scenario-price ${priceCls}">$${s.threshold_price.toFixed(2)}</span>`
          : "";
        return `
        <div class="risk-scenario-card ${tagCls}">
          <div class="risk-scenario-header">
            <span class="risk-scenario-name">${s.title || ""}</span>
            ${priceHtml}
          </div>
          <div class="risk-scenario-trigger">${s.trigger || ""}</div>
          <div class="risk-scenario-action">${s.action || ""}</div>
        </div>`;
      })
      .join("");
  } else {
    grid.innerHTML = '<div class="risk-scenario-card risk-info"><div class="risk-scenario-name">等待风控数据...</div></div>';
  }
}

// ── 执行按钮: 防连点 + 异步轮询 ──
function setupExecuteButton() {
  const btn = $("executeBtn");
  if (!btn || btn._bound) return;
  btn._bound = true;

  btn.addEventListener("click", async () => {
    if (btn.disabled) return;
    if (!SIGNAL_DATA?.signal?.execution) return;

    // 生成幂等键
    const idempotencyKey = (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function")
      ? crypto.randomUUID()
      : "10000000-1000-4000-8000-100000000000".replace(/[018]/g, c =>
        (+c ^ (crypto.getRandomValues(new Uint8Array(1))[0] & (15 >> (+c / 4)))).toString(16));

    // UI 锁定
    btn.disabled = true;
    const origText = btn.innerHTML;
    btn.innerHTML = '<span>🔄 订单路由中 (Routing)...</span>';

    try {
      const resp = await fetch("/api/v1/strategy/execute", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Idempotency-Key": idempotencyKey,
        },
        body: JSON.stringify({
          ticker: SIGNAL_DATA.ticker,
          action_type: SIGNAL_DATA.signal.action_type,
          strike: SIGNAL_DATA.signal.execution.strike,
          premium: SIGNAL_DATA.signal.execution.premium,
          quantity: 1,
        }),
      });

      if (resp.status === 409) {
        btn.innerHTML = '<span>⚠️ 订单已提交 (去重)</span>';
        setTimeout(() => { btn.innerHTML = origText; btn.disabled = false; }, 3000);
        return;
      }

      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);

      const result = await resp.json();
      const orderId = result.order_id;

      btn.innerHTML = '<span>⏳ 执行中...</span>';

      // 异步轮询
      let pollCount = 0;
      const poller = setInterval(async () => {
        pollCount++;
        try {
          const statusResp = await fetch(`/api/v1/strategy/order/${orderId}`);
          const order = await statusResp.json();

          if (order.status === "filled") {
            clearInterval(poller);
            btn.innerHTML = '<span>✅ 执行成功</span>';
            btn.classList.remove("btn-buy");
            btn.classList.add("btn-sell");
            setTimeout(() => { btn.innerHTML = origText; btn.disabled = false; }, 5000);
          } else if (pollCount > 30) {
            clearInterval(poller);
            btn.innerHTML = '<span>⏱ 超时 — 请手动检查</span>';
            setTimeout(() => { btn.innerHTML = origText; btn.disabled = false; }, 5000);
          }
        } catch (e) {
          console.warn("Polling error:", e);
        }
      }, 2000);

    } catch (err) {
      console.error("Execute error:", err);
      btn.innerHTML = '<span>❌ 提交失败</span>';
      setTimeout(() => { btn.innerHTML = origText; btn.disabled = false; }, 3000);
    }
  });
}

// ── Timing Decision Tree ─────────────────────────────────────────
function evaluateTimingDecision() {
  const mkt = MOCK_DATA.marketContext;
  const sig = MOCK_DATA.currentSignal;
  const isZh = APP_STATE.lang === "zh";
  const hasPosition = mkt.current_position && !mkt.current_position.includes("0");

  const factors = {
    rsi: mkt.rsi_14,
    vix: MOCK_DATA.radar.vix,
    position: hasPosition ? mkt.current_position : "0 (cash)",
  };

  // Priority 0: VIX extreme fear
  if (MOCK_DATA.radar.vix > 35) {
    return {
      action_type: "Hold",
      target_ticker: sig.ticker,
      execution_details: isZh
        ? `VIX 达 ${MOCK_DATA.radar.vix}，极端恐慌，暂停一切卖出策略，空仓观望`
        : `VIX at ${MOCK_DATA.radar.vix}, extreme fear — suspend all option selling, stand aside`,
      scene_label: "VIX Override",
      scene_factors: factors,
    };
  }

  // Priority 1 (Scene A): Oversold + no position
  if (mkt.rsi_14 < 40 && !hasPosition) {
    return {
      action_type: "Sell Put ONLY",
      target_ticker: sig.ticker,
      execution_details: isZh
        ? `RSI=${mkt.rsi_14} 极度超卖，卖出 $${mkt.put_strike} Put 收取 $${mkt.put_premium} 权利金，等待接货或到期作废`
        : `RSI=${mkt.rsi_14} oversold — sell $${mkt.put_strike} put for $${mkt.put_premium} premium, wait for assignment or expiry`,
      scene_label: "A",
      scene_factors: factors,
    };
  }

  // Priority 2 (Scene B): Overbought + has position
  if (mkt.rsi_14 > 60 && hasPosition) {
    return {
      action_type: "Sell Call ONLY",
      target_ticker: sig.ticker,
      execution_details: isZh
        ? `RSI=${mkt.rsi_14} 多头亢奋，持仓 ${mkt.current_position}，趁高波卖出 $${sig.strike} Call 收取溢价权利金`
        : `RSI=${mkt.rsi_14} overbought — holding ${mkt.current_position}, sell $${sig.strike} call to harvest elevated premium`,
      scene_label: "B",
      scene_factors: factors,
    };
  }

  // Priority 3 (Scene C): Overbought + no position
  if (mkt.rsi_14 > 60 && !hasPosition) {
    return {
      action_type: "Hold",
      target_ticker: sig.ticker,
      execution_details: isZh
        ? `RSI=${mkt.rsi_14} 超买但无仓位，拒绝高位追涨买股。可考虑卖出极深虚值 Put 作为替代`
        : `RSI=${mkt.rsi_14} overbought with no position — refuse to chase. Consider selling deep OTM put instead`,
      scene_label: "C",
      scene_factors: factors,
    };
  }

  // Priority 4 (Scene D): Range-bound + no position
  if (mkt.rsi_14 >= 40 && mkt.rsi_14 <= 60 && !hasPosition) {
    return {
      action_type: "Buy-Write",
      target_ticker: sig.ticker,
      execution_details: isZh
        ? `RSI=${mkt.rsi_14} 震荡区间，同步买入 100 股 + 卖出 $${sig.strike} Call，组合建仓降低成本`
        : `RSI=${mkt.rsi_14} range-bound — buy 100 shares + sell $${sig.strike} call simultaneously to reduce cost basis`,
      scene_label: "D",
      scene_factors: factors,
    };
  }

  // Fallback: Range-bound + has position
  return {
    action_type: "Hold",
    target_ticker: sig.ticker,
    execution_details: isZh
      ? `RSI=${mkt.rsi_14} 震荡区间，已持仓 ${mkt.current_position}，等待更极端信号再操作`
      : `RSI=${mkt.rsi_14} range-bound with position ${mkt.current_position} — wait for stronger signal`,
    scene_label: "Fallback",
    scene_factors: factors,
  };
}

function renderTimingPanel(result) {
  const panel = $("timingPanel");
  if (!panel) return;
  if (!result) { panel.style.display = "none"; return; }

  panel.style.display = "";

  // Action badge
  const badge = $("timingBadge");
  const actionMap = {
    "Buy Stock ONLY": { key: "timing_buy_stock", cls: "timing-buy" },
    "Sell Call ONLY": { key: "timing_sell_call", cls: "timing-sell-call" },
    "Sell Put ONLY": { key: "timing_sell_put", cls: "timing-sell-put" },
    "Buy-Write": { key: "timing_buy_write", cls: "timing-buy" },
    "Hold": { key: "timing_hold", cls: "timing-hold" },
  };
  const info = actionMap[result.action_type] || actionMap["Hold"];
  badge.textContent = t(info.key);
  badge.className = "timing-badge " + info.cls;

  // Details
  $("timingDetails").textContent = result.execution_details;

  // Scene factors
  const f = result.scene_factors;
  const posLabel = f.position.includes("0") ? t("timing_pos_cash") : `${t("timing_pos_holding")} ${f.position}`;
  $("timingFactors").innerHTML =
    `<span class="factor-tag">${t("timing_rsi")} ${f.rsi}</span>` +
    `<span class="factor-tag">${t("timing_vix")} ${f.vix}</span>` +
    `<span class="factor-tag">${posLabel}</span>`;
}

// ── CRO Risk Evaluator v2 ────────────────────────────────────────
function evaluateTradeProposal() {
  const sig = MOCK_DATA.currentSignal;
  const mkt = MOCK_DATA.marketContext;
  const price = MOCK_DATA.radar.spy.price;
  const isZh = APP_STATE.lang === "zh";

  // Rule 1: Data freshness
  if (mkt.dataLatency > 15) {
    return reject(isZh
      ? `[规则1·数据失真] 行情延迟 ${mkt.dataLatency}s，超过15秒阈值，严禁盲目发单`
      : `[Rule 1·Stale Data] Latency ${mkt.dataLatency}s exceeds 15s threshold`);
  }

  // Rule 2: Liquidity black hole
  const spread = mkt.ask - mkt.bid;
  const spreadPct = (spread / mkt.bid * 100).toFixed(1);
  if (spread > mkt.bid * 0.15) {
    return reject(isZh
      ? `[规则2·流动性黑洞] 买卖价差 ${spreadPct}%，超过15%上限，滑点成本过高`
      : `[Rule 2·Liquidity Black Hole] Spread ${spreadPct}% exceeds 15% cap`);
  }

  // Rule 3: Margin / margin call
  if (mkt.projectedMarginUtil > 60) {
    return reject(isZh
      ? `[规则3·爆仓预警] 模拟保证金占用 ${mkt.projectedMarginUtil}%，超60%防线，拒绝Margin Call风险`
      : `[Rule 3·Margin Breach] Projected util ${mkt.projectedMarginUtil}% exceeds 60% defense line`);
  }

  // Rule 4: Early assignment + dividend
  if (mkt.daysToExDividend < 5 && mkt.isITM && mkt.actionType.includes("Covered Call")) {
    return reject(isZh
      ? `[规则4·提前行权与分红雷] 距除息日仅 ${mkt.daysToExDividend} 天且为ITM备兑，提前行权风险极高`
      : `[Rule 4·Early Assignment] ${mkt.daysToExDividend}d to ex-div + ITM covered call`);
  }

  // Rule 5: Wash sale tax trap
  if (mkt.is_wash_sale_risk) {
    return reject(isZh
      ? "[规则5·洗售税务雷] 该标的30天内有亏损平仓记录，重新建仓将触发洗售规则，亏损无法抵税"
      : "[Rule 5·Wash Sale] Loss realized within 30 days, re-entry triggers wash sale — loss non-deductible");
  }

  // Rule 6: Gamma whipsaw trap (HV >> IV && DTE < 10)
  if (mkt.hv_30d > mkt.iv_rank * 1.5 && sig.dte < 10) {
    return reject(isZh
      ? `[规则6·Gamma双杀陷阱] HV(${mkt.hv_30d}%) 大幅高于 IV Rank(${mkt.iv_rank}%)，DTE仅${sig.dte}天，期权定价过低，强制空仓观望`
      : `[Rule 6·Gamma Trap] HV(${mkt.hv_30d}%) >> IV Rank(${mkt.iv_rank}%) with DTE=${sig.dte}, option mispriced — forced standby`);
  }

  // Yield calculation
  const midPrice = (mkt.bid + mkt.ask) / 2;
  const estSlippage = spread * 0.15;
  const effectivePremium = midPrice - estSlippage;
  const grossAnnualized = (midPrice / sig.strike) * (365 / sig.dte) * 100;
  const netAnnualized = grossAnnualized * (1 - mkt.estTaxDrag);

  // Rule 7: Net yield compliance (5%-15% after tax+slippage)
  if (netAnnualized < 5 || netAnnualized > 15) {
    return reject(isZh
      ? `[规则7·收益不匹配] 扣税扣滑点后净年化 ${netAnnualized.toFixed(2)}%，不在5%-15%合规区间`
      : `[Rule 7·Yield Mismatch] Net annualized ${netAnnualized.toFixed(2)}% outside 5%-15% range after tax & slippage`);
  }

  // All 7 rules passed — generate execution plan
  const startingLimit = midPrice;
  const floorLimit = mkt.bid + spread * 0.2;
  const bullTarget = (price * 1.15).toFixed(0);
  const bearTarget = (price * 0.80).toFixed(0);

  return {
    is_approved: true,
    rejection_reason: null,
    execution_plan: {
      recommended_order_type: "Limit_Price_Chaser",
      starting_limit_price: startingLimit,
      floor_limit_price: floorLimit,
      gross_annualized_yield_est: grossAnnualized.toFixed(2) + "%",
      net_annualized_yield_after_tax: netAnnualized.toFixed(2) + "%",
    },
    scenario_playbooks: {
      bullish_surge: isZh
        ? `若 ${sig.ticker} 暴涨至 $${bullTarget} (+15%)：期权浮亏达80%时触发提前平仓止盈，或执行 Roll Up 将行权价上移至 $${(sig.strike * 1.05).toFixed(0)} 并 Roll Out +30天，锁定更高时间价值。允许部分让利保留上涨空间。`
        : `If ${sig.ticker} surges to $${bullTarget} (+15%): Close at 80% profit target or Roll Up to $${(sig.strike * 1.05).toFixed(0)} + Roll Out 30d. Accept reduced premium to retain upside.`,
      bearish_crash: isZh
        ? `若 ${sig.ticker} 暴跌至 $${bearTarget} (-20%)：执行 Roll Down，将行权价下移至 $${(sig.strike * 0.90).toFixed(0)}，Roll Out +30天赚取时间价值弥补现货浮亏。持续降低成本基础。若跌破200日均线 ($${MOCK_DATA.radar.spy.sma200.toFixed(0)})，立即暂停所有新开仓。`
        : `If ${sig.ticker} crashes to $${bearTarget} (-20%): Roll Down to $${(sig.strike * 0.90).toFixed(0)} + Roll Out 30d. Collect time value to offset equity loss. If below SMA200 ($${MOCK_DATA.radar.spy.sma200.toFixed(0)}), halt all new positions.`,
      whipsaw_gamma_trap: isZh
        ? `若市场进入宽幅震荡 (日波幅>2%)：暂停一切展期操作，等待 IV Rank 回升至 50% 以上再行动。当前 HV(${mkt.hv_30d}%) vs IV Rank(${mkt.iv_rank}%)，若 HV 持续高于 IV 则说明期权定价不足，卖权性价比极低，强制观望。`
        : `If whipsaw (daily range >2%): Suspend all rolls, wait for IV Rank >${50}% before acting. Current HV(${mkt.hv_30d}%) vs IV Rank(${mkt.iv_rank}%) — if HV persists above IV, options are mispriced for sellers. Forced standby.`,
    },
    ui_rationale: isZh
      ? [`净年化 ${netAnnualized.toFixed(1)}%（扣税30%后）`, `IV Rank ${mkt.iv_rank}%，权利金溢价丰厚`, `避开除息与洗售，无税务地雷`]
      : [`Net ann. ${netAnnualized.toFixed(1)}% after 30% tax`, `IV Rank ${mkt.iv_rank}%, rich premium`, `Clear of ex-div & wash sale traps`],
  };
}

function reject(reason) {
  return {
    is_approved: false,
    rejection_reason: reason,
    execution_plan: null,
    scenario_playbooks: null,
    ui_rationale: null,
  };
}

// ── 三段式分析面板渲染 ──────────────────────────────────────────
function renderAnalysisPanel() {
  const fundamentals = MOCK_DATA.fundamentals || {};
  const scenario = MOCK_DATA.scenario || {};
  const signal = MOCK_DATA.signal || {};

  // ── 区块 A: 基本面标签 ──
  const fundTagsEl = document.getElementById("fundamentalTags");
  if (fundTagsEl) {
    const diagItems = fundamentals.diagnosis || signal.ai_reasons || [];
    const fundDiag = diagItems.filter(
      (d) =>
        d.includes("市值") ||
        d.includes("PE") ||
        d.includes("评级") ||
        d.includes("股息") ||
        d.includes("Cap")
    );
    if (fundDiag.length > 0) {
      fundTagsEl.innerHTML = fundDiag
        .map((d) => {
          let cls = "analysis-tag";
          if (d.includes("⚠")) cls += " tag-warn";
          else if (d.includes("🚨") || d.includes("🚫")) cls += " tag-danger";
          else if (d.includes("Strong Buy") || d.includes("强买") || d.includes("合理"))
            cls += " tag-good";
          return `<span class="${cls}">${d}</span>`;
        })
        .join("");
    } else {
      fundTagsEl.innerHTML = '<span class="analysis-tag">暂无基本面数据</span>';
    }
  }

  // ── 区块 B: 技术面标签 ──
  const techTagsEl = document.getElementById("technicalTags");
  if (techTagsEl) {
    const diagItems = fundamentals.diagnosis || signal.ai_reasons || [];
    const techDiag = diagItems.filter(
      (d) =>
        d.includes("RSI") ||
        d.includes("SMA") ||
        d.includes("VIX") ||
        d.includes("财报") ||
        d.includes("除息")
    );
    if (techDiag.length > 0) {
      techTagsEl.innerHTML = techDiag
        .map((d) => {
          let cls = "analysis-tag";
          if (d.includes("🚨")) cls += " tag-danger";
          else if (d.includes("⚠")) cls += " tag-warn";
          return `<span class="${cls}">${d}</span>`;
        })
        .join("");
    } else {
      techTagsEl.innerHTML = '<span class="analysis-tag">暂无技术面数据</span>';
    }
  }

  // ── 区块 C: 情景推演 ──
  const summaryEl = document.getElementById("scenarioSummary");
  const listEl = document.getElementById("scenarioList");
  if (summaryEl) {
    summaryEl.textContent = scenario.summary || "--";
  }
  if (listEl && scenario.scenarios) {
    listEl.innerHTML = scenario.scenarios
      .map((s) => {
        const colorCls = s.color === "green" ? "scenario-green" : s.color === "red" ? "scenario-red" : "";
        const pnlSign = s.pnl >= 0 ? "+" : "";
        const pnlCls = s.pnl >= 0 ? "pnl-positive" : "pnl-negative";
        return `
        <div class="scenario-item ${colorCls}">
          <div class="scenario-item-header">
            <span class="scenario-item-icon">${s.icon}</span>
            <span class="scenario-item-label">${s.label}</span>
            <span class="scenario-item-pnl ${pnlCls}">${pnlSign}$${Math.abs(s.pnl).toLocaleString("en-US", { minimumFractionDigits: 2 })}</span>
          </div>
          <div class="scenario-item-desc">${s.description}</div>
        </div>`;
      })
      .join("");
  } else if (listEl) {
    listEl.innerHTML = '<div class="scenario-item"><div class="scenario-item-desc">等待信号生成情景推演...</div></div>';
  }
}


// ── 动态风控面板渲染 ──────────────────────────────────────────
function renderRiskPanel() {
  const risk = MOCK_DATA.risk || {};
  if (!risk.scenarios) return;

  // Summary bar
  const im1El = document.getElementById("riskIM1");
  const im2El = document.getElementById("riskIM2");
  const atrEl = document.getElementById("riskATR");
  if (im1El) im1El.textContent = `1σ: ±$${(risk.implied_move_1sigma || 0).toFixed(2)}`;
  if (im2El) im2El.textContent = `2σ: ±$${(risk.implied_move_2sigma || 0).toFixed(2)}`;
  if (atrEl) atrEl.textContent = `ATR Stop: $${(risk.atr_stop_loss || 0).toFixed(2)}`;

  // Scenario cards
  const grid = document.getElementById("riskScenarioGrid");
  if (!grid) return;

  grid.innerHTML = risk.scenarios
    .map((s) => {
      const tagCls = `risk-${s.tag_type}`;
      const priceCls = `price-${s.tag_type}`;
      const priceHtml = s.threshold_price
        ? `<span class="risk-scenario-price ${priceCls}">$${s.threshold_price.toFixed(2)}</span>`
        : "";
      return `
      <div class="risk-scenario-card ${tagCls}">
        <div class="risk-scenario-header">
          <span class="risk-scenario-name">${s.scenario_name}</span>
          ${priceHtml}
        </div>
        <div class="risk-scenario-trigger">${s.trigger_condition}</div>
        <div class="risk-scenario-action">${s.action_plan}</div>
      </div>`;
    })
    .join("");
}



function renderCRO(result) {
  const badge = $("croBadge");
  const rejection = $("croRejection");
  const plan = $("croPlan");
  const playbookRow = $("playbookRow");

  badge.classList.remove("cro-approved", "cro-rejected");

  if (result.is_approved) {
    badge.textContent = t("cro_approved");
    badge.classList.add("cro-approved");
    rejection.classList.remove("visible");
    plan.style.display = "";
    playbookRow.style.display = "";

    // Execution plan
    $("croOrderType").textContent = result.execution_plan.recommended_order_type;
    $("croStartPrice").textContent = formatMoney(result.execution_plan.starting_limit_price);
    $("croFloorPrice").textContent = formatMoney(result.execution_plan.floor_limit_price);
    $("croGrossYield").textContent = result.execution_plan.gross_annualized_yield_est;
    $("croNetYield").textContent = result.execution_plan.net_annualized_yield_after_tax;

    // Playbooks (3-way)
    $("playbookBull").textContent = result.scenario_playbooks.bullish_surge;
    $("playbookBear").textContent = result.scenario_playbooks.bearish_crash;
    $("playbookWhipsaw").textContent = result.scenario_playbooks.whipsaw_gamma_trap;
  } else {
    badge.textContent = t("cro_rejected");
    badge.classList.add("cro-rejected");
    rejection.textContent = result.rejection_reason;
    rejection.classList.add("visible");
    plan.style.display = "none";
    playbookRow.style.display = "none";
  }
}

function setupExecuteBtn() {
  $("executeBtn").addEventListener("click", () => {
    if (APP_STATE.isHalted) return;
    const btn = $("executeBtn");
    const origText = btn.querySelector("span")?.textContent || "";
    btn.querySelector("span").textContent =
      APP_STATE.lang === "zh" ? "指令已发送 ✓" : "Order Sent ✓";
    btn.style.filter = "brightness(1.2)";
    setTimeout(() => {
      btn.querySelector("span").textContent = t("signal_btn");
      btn.style.filter = "";
    }, 2000);
  });
}

// ── Lifecycle ────────────────────────────────────────────────────
function renderPositions() {
  const positions = MOCK_DATA.activePositions;
  const tbody = $("positionsBody");
  const cardsContainer = $("posCardsContainer");
  tbody.innerHTML = "";
  cardsContainer.innerHTML = "";

  positions.forEach((pos) => {
    // === Table Row ===
    const tr = document.createElement("tr");
    const dteWarn = pos.dte <= 14;
    if (dteWarn) tr.classList.add("row-warn");

    const isCall =
      pos.type === "Call" || pos.type.includes("Call") || (pos.typeCn && pos.typeCn.includes("看涨"));
    const typeClass = isCall ? "tag-call" : "tag-put";
    const typeText =
      APP_STATE.lang === "zh" ? pos.typeCn || pos.type : pos.type;

    const pnlClass = pos.pnl >= 0 ? "pnl-positive" : "pnl-negative";
    const pnlSign = pos.pnl >= 0 ? "+" : "";

    let dteHtml;
    if (pos.dte <= 14) {
      dteHtml = `<span class="dte-indicator"><span class="warn-icon">⚠</span><span class="dte-warn">${pos.dte}</span></span>`;
    } else {
      dteHtml = `${pos.dte}`;
    }

    const rollText = t("roll_btn");
    tr.innerHTML = `
      <td>${pos.ticker}</td>
      <td><span class="type-tag ${typeClass}">${typeText}</span></td>
      <td>${formatMoney(pos.strike)}</td>
      <td>${pos.expiry}</td>
      <td>${dteHtml}</td>
      <td>${formatMoney(pos.initialPremium)}</td>
      <td>${formatMoney(pos.currentValue)}</td>
      <td class="${pnlClass}">${pnlSign}${pos.pnl.toFixed(1)}%</td>
      <td><button class="roll-btn" data-ticker="${pos.ticker}" data-expiry="${pos.expiry}" data-strike="${pos.strike}">${rollText}</button></td>
    `;
    tbody.appendChild(tr);

    // === Card (mobile) ===
    const card = document.createElement("div");
    card.className = `glass-card pos-card ${dteWarn ? "row-warn" : ""}`;
    card.innerHTML = `
      <div class="pos-card-header">
        <span class="pos-card-ticker">${pos.ticker}</span>
        <span class="type-tag ${typeClass}">${typeText}</span>
      </div>
      <div class="pos-card-field">
        <span class="pos-card-label">${t("pos_col_strike")}</span>
        <span class="pos-card-value">${formatMoney(pos.strike)}</span>
      </div>
      <div class="pos-card-field">
        <span class="pos-card-label">${t("pos_col_dte")}</span>
        <span class="pos-card-value ${dteWarn ? "dte-warn" : ""}">${pos.dte}</span>
      </div>
      <div class="pos-card-field">
        <span class="pos-card-label">${t("pos_col_pnl")}</span>
        <span class="pos-card-value ${pnlClass}">${pnlSign}${pos.pnl.toFixed(1)}%</span>
      </div>
      <div class="pos-card-field">
        <span class="pos-card-label">${t("pos_col_current")}</span>
        <span class="pos-card-value">${formatMoney(pos.currentValue)}</span>
      </div>
      <div class="pos-card-actions">
        <button class="roll-btn" data-ticker="${pos.ticker}" data-expiry="${pos.expiry}" data-strike="${pos.strike}">${rollText}</button>
      </div>
    `;
    cardsContainer.appendChild(card);
  });

  // Roll button handlers
  document.querySelectorAll(".roll-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      RollManager.openModal({
        ticker: btn.dataset.ticker,
        expiry: btn.dataset.expiry,
        strike: parseFloat(btn.dataset.strike),
        currentValue: parseFloat(btn.dataset.currentvalue) || 1.20,
        orderId: btn.dataset.orderid || null,
      });
    });
  });
}

function renderReport() {
  const { tracking } = MOCK_DATA;
  $("reportOps").textContent = tracking.automatedOps;
  $("reportPremium").textContent = formatMoney(tracking.totalPremiumCollected);
}

function renderEquityChart() {
  // Legacy stub — replaced by EquityCurveManager
  EquityCurveManager.fetchAndRender();
}

// ══════════════════════════════════════════════════════════════════
// EQUITY CURVE MANAGER — 盯市净值 ECharts
// ══════════════════════════════════════════════════════════════════

const EquityCurveManager = {
  _chart: null,

  init() {
    const container = $("equityCurveChart");
    if (!container || typeof echarts === "undefined") return;

    this._chart = echarts.init(container, "dark");
    this._chart.setOption({
      backgroundColor: "transparent",
      tooltip: {
        trigger: "axis",
        backgroundColor: "rgba(15,23,42,0.92)",
        borderColor: "rgba(6,182,212,0.3)",
        textStyle: { color: "#e2e8f0", fontSize: 12 },
        formatter: (params) => {
          const p = params[0];
          if (!p || !p.data) return "";
          const d = p.data;
          return `<div style="font-weight:600;margin-bottom:4px">${d.date}</div>
            <div>Total Equity: <span style="color:#06b6d4;font-weight:700">$${d.value.toLocaleString()}</span></div>
            <div>现金占比: <span style="color:#94a3b8">${d.cashRatio}%</span></div>
            <div>浮动市值: <span style="color:#f59e0b">$${d.positionsValue.toLocaleString()}</span></div>`;
        },
      },
      grid: { top: 20, right: 20, bottom: 30, left: 65 },
      xAxis: {
        type: "category",
        boundaryGap: false,
        axisLine: { lineStyle: { color: "#334155" } },
        axisLabel: { color: "#64748b", fontSize: 10 },
      },
      yAxis: {
        type: "value",
        axisLine: { lineStyle: { color: "#334155" } },
        axisLabel: { color: "#64748b", formatter: (v) => `$${(v / 1000).toFixed(0)}k` },
        splitLine: { lineStyle: { color: "#1e293b" } },
      },
      series: [{
        name: "Total Equity",
        type: "line",
        smooth: true,
        symbol: "none",
        lineStyle: {
          color: "#06b6d4",
          width: 2.5,
          shadowBlur: 10,
          shadowColor: "rgba(6,182,212,0.5)",
        },
        areaStyle: {
          color: {
            type: "linear",
            x: 0, y: 0, x2: 0, y2: 1,
            colorStops: [
              { offset: 0, color: "rgba(6,182,212,0.25)" },
              { offset: 1, color: "rgba(6,182,212,0)" },
            ],
          },
        },
        data: [],
      }],
    });

    window.addEventListener("resize", () => this._chart?.resize());
  },

  async fetchAndRender() {
    if (!this._chart) this.init();
    if (!this._chart) return;

    try {
      const resp = await fetch("/api/v1/portfolio/equity-curve?days=90");
      if (!resp.ok) throw new Error("API error");
      const data = await resp.json();

      if (!data.curve || data.curve.length === 0) {
        // Fallback: 用 MOCK_DATA
        this._renderMockData();
        return;
      }

      // 渲染真实数据
      const xData = data.curve.map(c => c.date.slice(5)); // MM-DD
      const seriesData = data.curve.map(c => ({
        value: c.total_equity,
        date: c.date,
        cashRatio: c.cash_ratio,
        positionsValue: c.positions_value,
      }));

      this._chart.setOption({
        xAxis: { data: xData },
        series: [{ data: seriesData }],
      });

      // 更新 summary
      if (data.summary) this._renderSummary(data.summary);
    } catch (err) {
      console.warn("[EquityCurve] API failed, using mock:", err.message);
      this._renderMockData();
    }
  },

  _renderMockData() {
    const mockData = MOCK_DATA.equityCurve || [];
    if (!mockData.length) return;

    const xData = mockData.map((_, i) => `D${i + 1}`);
    const seriesData = mockData.map((v, i) => ({
      value: v,
      date: `Day ${i + 1}`,
      cashRatio: (70 + Math.random() * 20).toFixed(1),
      positionsValue: Math.round(v * 0.25),
    }));

    this._chart.setOption({
      xAxis: { data: xData },
      series: [{ data: seriesData }],
    });
  },

  _renderSummary(s) {
    const container = $("equitySummary");
    if (!container) return;
    container.style.display = "flex";

    const retEl = $("eqReturn");
    const ddEl = $("eqDrawdown");
    const shEl = $("eqSharpe");

    if (retEl) {
      retEl.textContent = `${s.total_return_pct >= 0 ? "+" : ""}${s.total_return_pct}%`;
      retEl.style.color = s.total_return_pct >= 0 ? "#10b981" : "#ef4444";
    }
    if (ddEl) {
      ddEl.textContent = `${s.max_drawdown_pct}%`;
      ddEl.style.color = "#ef4444";
    }
    if (shEl) {
      shEl.textContent = s.sharpe_ratio.toFixed(2);
      shEl.style.color = s.sharpe_ratio >= 1 ? "#10b981" : "#f59e0b";
    }
  },
};

// ══════════════════════════════════════════════════════════════════
// TOP PICKS MANAGER — 智能推荐 Top 3
// ══════════════════════════════════════════════════════════════════

const TopPicksManager = {
  _TIMEOUT_MS: 15000, // 前端超时值 (后端单标的10s + 缓冲)

  async fetchTopPicks() {
    const container = $("topPicksContainer");
    if (!container) return;

    // ── 1. 设置 Loading 状态 ──
    container.innerHTML = '<div style="text-align:center;color:#64748b;padding:20px;">⏳ 正在扫描票池...</div>';

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), this._TIMEOUT_MS);

    try {
      // ── 2. HTTP 状态墙 ──
      const resp = await fetch("/api/v1/strategy/top-picks", {
        signal: controller.signal,
      });

      if (!resp.ok) {
        throw new Error(`HTTP ${resp.status}: ${resp.statusText}`);
      }

      const data = await resp.json();

      // ── 3. 分支处理 ──
      if (!data.picks || data.picks.length === 0) {
        // 空结果 — 优雅降级
        const msg = data.message || "暂无符合极高性价比或近期避开财报的推荐标的，建议观望。";
        container.innerHTML = `
          <div style="text-align:center;padding:24px;">
            <div style="font-size:28px;margin-bottom:8px;">📭</div>
            <div style="color:#94a3b8;font-size:13px;">${msg}</div>
            ${data.scanned ? `<div style="color:#475569;font-size:11px;margin-top:6px;">已扫描 ${data.scanned} 个标的</div>` : ""}
          </div>`;
        return;
      }

      this.renderCards(data.picks, container);

    } catch (err) {
      // ── 4. 异常 UI 渲染 ──
      const isTimeout = err.name === "AbortError";
      const errMsg = isTimeout
        ? "⚠️ 扫描超时 (>15s)，yfinance 可能拥堵，请稍后重试。"
        : `⚠️ 扫描异常: ${err.message || "未知错误"}，请检查后端网络后重试。`;

      container.innerHTML = `
        <div style="text-align:center;padding:20px;">
          <div style="color:#ef4444;font-size:13px;margin-bottom:10px;">${errMsg}</div>
          <button onclick="TopPicksManager.fetchTopPicks()"
            style="background:rgba(239,68,68,0.15);color:#ef4444;border:1px solid rgba(239,68,68,0.3);
                   padding:6px 16px;border-radius:6px;cursor:pointer;font-size:12px;">
            🔄 重试
          </button>
        </div>`;
      console.warn("[TopPicks] fetchTopPicks failed:", err);

    } finally {
      // ── 5. 强制释放 ──
      clearTimeout(timeoutId);
    }
  },

  renderCards(picks, container) {
    if (picks.length === 0) {
      container.innerHTML = '<div style="text-align:center;color:#64748b;padding:20px;">暂无推荐 (所有标的在财报窗口内)</div>';
      return;
    }

    container.innerHTML = picks.map((p, i) => `
      <div class="tp-card" onclick="setGlobalTicker('${p.ticker}')" title="点击切换全局标的">
        <div class="tp-rank">#${i + 1}</div>
        <div class="tp-ticker">${p.ticker}</div>
        <div class="tp-price">$${p.current_price}</div>
        <div class="tp-yield">
          <span class="tp-yield-val">${p.premium_yield}%</span>
          <span class="tp-yield-label">Premium Yield</span>
        </div>
        <div class="tp-meta">
          ${p.next_earnings ? `<span class="tp-safe">✅ 财报安全</span>` : '<span class="tp-safe">ℹ️ 无财报数据</span>'}
          <span class="tp-dte">DTE ${p.dte || "—"}</span>
        </div>
      </div>
    `).join("");
  },
};


// ══════════════════════════════════════════════════════════════════
// ROLL MANAGER — 展期组合单交互
// ══════════════════════════════════════════════════════════════════

const RollManager = {
  _orderId: null,
  _oldBid: 0,
  _newAsk: 0,

  /**
   * 打开展期 Modal
   * @param {Object} pos - position data from MOCK_DATA or API
   */
  openModal(pos) {
    this._orderId = pos.orderId || pos.id || null;

    // 填充旧仓信息
    const setText = (id, v) => { const el = $(id); if (el) el.textContent = v; };
    setText("rollOldTicker", pos.ticker);
    setText("rollOldStrike", `$${parseFloat(pos.strike).toFixed(2)}`);
    setText("rollOldExpiry", pos.expiry || pos.expiration);

    // 模拟 bid/ask (实际应从API获取)
    this._oldBid = pos.currentValue || pos.bid || 1.20;
    this._newAsk = (this._oldBid * 2.5).toFixed(2); // 模拟: 新仓 ask ≈ 2.5x 旧仓 bid

    setText("rollOldBid", `$${parseFloat(this._oldBid).toFixed(2)}`);
    setText("rollNewAsk", `$${parseFloat(this._newAsk).toFixed(2)}`);

    // 自动填充新仓参数 (默认 +30天, 同 strike)
    const newExpiry = $("rollNewExpiry");
    if (newExpiry) {
      const d = new Date();
      d.setDate(d.getDate() + 30);
      newExpiry.value = d.toISOString().split("T")[0];
    }
    const newStrike = $("rollNewStrike");
    if (newStrike) newStrike.value = pos.strike;

    // 自动填限价
    const limitInput = $("rollLimitPrice");
    if (limitInput) limitInput.value = (this._newAsk - this._oldBid).toFixed(2);

    // 绑定输入事件
    ["rollNewStrike", "rollNewExpiry", "rollLimitPrice"].forEach(id => {
      const el = $(id);
      if (el) el.addEventListener("input", () => this._recalcNet());
    });

    this._recalcNet();

    // 显示 modal
    const modal = $("rollModal");
    if (modal) modal.style.display = "flex";
  },

  close() {
    const modal = $("rollModal");
    if (modal) modal.style.display = "none";
    this._orderId = null;
  },

  _recalcNet() {
    const limitPrice = parseFloat($("rollLimitPrice")?.value) || 0;
    const netEl = $("rollNetValue");
    const typeEl = $("rollNetType");
    if (!netEl || !typeEl) return;

    const netAmount = limitPrice * 100; // per contract
    netEl.textContent = `$${Math.abs(netAmount).toFixed(2)}`;

    if (limitPrice > 0) {
      netEl.style.color = "#10b981";
      typeEl.textContent = "Net Credit ✅";
      typeEl.style.color = "#10b981";
    } else if (limitPrice < 0) {
      netEl.style.color = "#ef4444";
      typeEl.textContent = "Net Debit ⚠️";
      typeEl.style.color = "#ef4444";
    } else {
      netEl.style.color = "#94a3b8";
      typeEl.textContent = "Even";
      typeEl.style.color = "#94a3b8";
    }
  },

  async submit() {
    const limitPrice = parseFloat($("rollLimitPrice")?.value);
    if (!limitPrice && limitPrice !== 0) {
      alert("请填写 Net Limit Price");
      return;
    }
    if (!this._orderId) {
      alert("未选择旧仓");
      return;
    }

    const btn = $("rollSubmitBtn");
    if (btn) { btn.disabled = true; btn.textContent = "提交中..."; }

    try {
      const resp = await fetch("/api/v1/orders/roll_combo", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          old_order_id: this._orderId,
          new_strike: parseFloat($("rollNewStrike")?.value) || 0,
          new_expiration: $("rollNewExpiry")?.value || "",
          net_limit_price: limitPrice,
          quantity: 1,
        }),
      });

      const data = await resp.json();
      if (!resp.ok) {
        alert(`展期失败: ${data.detail || "未知错误"}`);
        return;
      }

      // 成功
      this.close();
      console.log("[Roll] Success:", data);
      // Toast 通知
      if (typeof WatchlistManager !== "undefined" && WatchlistManager._toast) {
        WatchlistManager._toast(data.message || "展期成功", "success");
      }
    } catch (err) {
      alert(`展期请求失败: ${err.message}`);
    } finally {
      if (btn) { btn.disabled = false; btn.textContent = "确认展期"; }
    }
  },
};

// ══════════════════════════════════════════════════════════════════
// WATCHLIST MANAGER — 核心票池 CRUD
// ══════════════════════════════════════════════════════════════════

const WatchlistManager = {
  _base: "/api/v1/settings/watchlist",
  _data: [],
  _debounceTimer: null,

  // ── Debounced Search ──
  _onSearchInput(e) {
    clearTimeout(this._debounceTimer);
    const q = e.target.value.trim();
    if (q.length < 1) { this._hideDropdown(); return; }
    this._debounceTimer = setTimeout(() => this._doSearch(q), 300);
  },

  async _doSearch(q) {
    try {
      const resp = await fetch(`/api/v1/strategy/search?q=${encodeURIComponent(q)}`);
      if (!resp.ok) return;
      const data = await resp.json();
      this._showDropdown(data.results || []);
    } catch (err) {
      console.warn("Search failed:", err);
    }
  },

  _showDropdown(results) {
    let dd = document.querySelector(".wl-dropdown");
    if (!dd) {
      dd = document.createElement("div");
      dd.className = "wl-dropdown";
      const addBar = document.querySelector(".wl-quick-add");
      if (addBar) addBar.style.position = "relative";
      addBar?.appendChild(dd);
    }
    if (results.length === 0) {
      dd.innerHTML = '<div class="wl-dd-empty">未找到匹配标的</div>';
    } else {
      dd.innerHTML = results.map(r => `
        <div class="wl-dd-item" data-ticker="${r.ticker}">
          <span class="wl-dd-ticker">${r.ticker}</span>
          <span class="wl-dd-name">${r.name || ""}</span>
          ${r.price ? `<span class="wl-dd-price">$${r.price}</span>` : ""}
        </div>
      `).join("");
      dd.querySelectorAll(".wl-dd-item").forEach(el => {
        el.addEventListener("click", () => {
          const input = $("wlTickerInput");
          if (input) input.value = el.dataset.ticker;
          this._hideDropdown();
          this.addTicker();
        });
      });
    }
    dd.style.display = "block";
  },

  _hideDropdown() {
    const dd = document.querySelector(".wl-dropdown");
    if (dd) dd.style.display = "none";
  },

  // ── Toast Notification ──
  toast(msg, type = "success") {
    const container = $("wlToastContainer");
    if (!container) return;
    const el = document.createElement("div");
    el.className = `wl-toast ${type}`;
    el.textContent = msg;
    container.appendChild(el);
    setTimeout(() => el.remove(), 3200);
  },

  // ── Fetch All & Render ──
  async fetchAll() {
    try {
      const resp = await fetch(this._base);
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const data = await resp.json();
      this._data = data.tickers || [];
      this.renderTable();
    } catch (err) {
      console.error("Watchlist fetch failed:", err);
      this.toast(`加载失败: ${err.message}`, "error");
    }
  },

  // ── Render Table ──
  renderTable() {
    const body = $("wlTableBody");
    const empty = $("wlEmptyState");
    if (!body) return;

    if (this._data.length === 0) {
      body.innerHTML = "";
      if (empty) empty.style.display = "block";
      return;
    }
    if (empty) empty.style.display = "none";

    body.innerHTML = this._data
      .map(
        (t) => `
      <div class="wl-row ${t.is_active ? "" : "inactive"}" data-ticker="${t.ticker}">
        <span class="wl-ticker-name">${t.ticker}</span>
        <span>${t.supports_options ? '<span class="wl-opt-badge">OPT</span>' : ""}</span>
        <span class="wl-score" data-ticker="${t.ticker}" data-score="${t.min_liquidity_score}">
          Score: ${(t.min_liquidity_score * 100).toFixed(0)}
        </span>
        <label class="wl-toggle">
          <input type="checkbox" ${t.is_active ? "checked" : ""}
                 onchange="WatchlistManager.toggleActive('${t.ticker}', this)" />
          <span class="wl-toggle-track"></span>
          <span class="wl-toggle-thumb"></span>
        </label>
        <button class="wl-delete-btn" onclick="WatchlistManager.deleteTicker('${t.ticker}')">🗑️</button>
      </div>`,
      )
      .join("");

    // Bind inline edit clicks
    body.querySelectorAll(".wl-score").forEach((el) => {
      el.addEventListener("click", () => this._startInlineEdit(el));
    });
  },

  // ── Add Ticker ──
  async addTicker() {
    const input = $("wlTickerInput");
    const btn = $("wlAddBtn");
    const ticker = input?.value?.trim()?.toUpperCase();

    if (!ticker || !/^[A-Z\^]{1,10}$/.test(ticker)) {
      this.toast("请输入有效的 Ticker (1-10 位大写字母)", "error");
      return;
    }

    btn.disabled = true;
    btn.innerHTML = '<span class="wl-add-icon">⏳</span> 添加中...';

    try {
      const resp = await fetch(this._base, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ticker }),
      });
      const data = await resp.json();

      if (!resp.ok) {
        throw new Error(data.detail || `HTTP ${resp.status}`);
      }

      // Check options support warning
      if (data.supports_options === false) {
        this.toast("该标的不支持期权交易", "error");
      } else {
        this.toast(data.message || `${ticker} 已添加`, "success");
      }

      input.value = "";
      await this.fetchAll();
    } catch (err) {
      this.toast(`添加失败: ${err.message}`, "error");
    } finally {
      btn.disabled = false;
      btn.innerHTML = '<span class="wl-add-icon">➕</span> 添加至监控';
    }
  },

  // ── Toggle Active ──
  async toggleActive(ticker, checkbox) {
    const toggle = checkbox.closest(".wl-toggle");
    toggle.classList.add("disabled");

    try {
      const resp = await fetch(`${this._base}/${ticker}/toggle`, { method: "PUT" });
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const data = await resp.json();
      const row = checkbox.closest(".wl-row");
      if (row) row.classList.toggle("inactive", !data.ticker?.is_active);
      this.toast(data.message, "info");
    } catch (err) {
      checkbox.checked = !checkbox.checked; // revert
      this.toast(`切换失败: ${err.message}`, "error");
    } finally {
      toggle.classList.remove("disabled");
    }
  },

  // ── Inline Edit Score ──
  _startInlineEdit(el) {
    const ticker = el.dataset.ticker;
    const currentScore = parseFloat(el.dataset.score) || 0.5;

    const input = document.createElement("input");
    input.type = "number";
    input.className = "wl-score-input";
    input.value = currentScore;
    input.min = 0;
    input.max = 1;
    input.step = 0.05;

    const save = async () => {
      const newVal = parseFloat(input.value);
      if (isNaN(newVal) || newVal < 0 || newVal > 1) {
        this.fetchAll(); // revert
        return;
      }
      try {
        const resp = await fetch(`${this._base}/${ticker}`, {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ min_liquidity_score: newVal }),
        });
        if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
        this.toast(`${ticker} 流动性阈值已更新`, "success");
      } catch (err) {
        this.toast(`更新失败: ${err.message}`, "error");
      }
      this.fetchAll();
    };

    input.addEventListener("blur", save);
    input.addEventListener("keydown", (e) => {
      if (e.key === "Enter") { e.preventDefault(); input.blur(); }
      if (e.key === "Escape") { e.preventDefault(); this.fetchAll(); }
    });

    el.replaceWith(input);
    input.focus();
    input.select();
  },

  // ── Delete Ticker ──
  async deleteTicker(ticker) {
    if (!confirm(`确定要从监控池中移除 ${ticker} 吗？`)) return;

    const row = document.querySelector(`.wl-row[data-ticker="${ticker}"]`);
    if (row) row.classList.add("fade-out");

    try {
      const resp = await fetch(`${this._base}/${ticker}`, { method: "DELETE" });
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      this.toast(`${ticker} 已移除`, "success");
      setTimeout(() => this.fetchAll(), 300); // wait for fade-out
    } catch (err) {
      if (row) row.classList.remove("fade-out");
      this.toast(`删除失败: ${err.message}`, "error");
    }
  },
};

function setupWatchlistManager() {
  // Quick Add: button click + Enter key
  $("wlAddBtn")?.addEventListener("click", () => WatchlistManager.addTicker());
  $("wlTickerInput")?.addEventListener("keydown", (e) => {
    if (e.key === "Enter") { WatchlistManager._hideDropdown(); WatchlistManager.addTicker(); }
    if (e.key === "Escape") WatchlistManager._hideDropdown();
  });
  // Debounced search on input
  $("wlTickerInput")?.addEventListener("input", (e) => WatchlistManager._onSearchInput(e));
  // Click outside to close dropdown
  document.addEventListener("click", (e) => {
    if (!e.target.closest(".wl-quick-add")) WatchlistManager._hideDropdown();
  });
  // Initial fetch
  WatchlistManager.fetchAll();
}

// ── Settings ─────────────────────────────────────────────────────
function setupApiToggle() {
  const input = $("apiKeyInput");
  const btn = $("apiToggleBtn");
  let visible = false;
  btn.addEventListener("click", () => {
    visible = !visible;
    input.type = visible ? "text" : "password";
    btn.textContent = visible ? "🔒" : "👁️";
  });
}

function renderTerminal() {
  const terminal = $("systemTerminal");
  terminal.innerHTML = "";
  MOCK_DATA.systemLogs.forEach((log) => {
    const line = document.createElement("div");
    line.className = "terminal-line";
    line.textContent = log;
    terminal.appendChild(line);
  });
  terminal.scrollTop = terminal.scrollHeight;
}

// ── Language Toggle ──────────────────────────────────────────────
function setupLangToggle() {
  $("langToggle").addEventListener("click", () => {
    APP_STATE.lang = APP_STATE.lang === "zh" ? "en" : "zh";
    renderAll();
  });
}

// ── Render All ───────────────────────────────────────────────────
function renderAll() {
  applyI18n();
  renderTicker();
  renderDashboard();
  renderSignal();
  calculateProjections();
  renderPositions();
  renderReport();
  renderTerminal();
  if (APP_STATE.currentView === "lifecycle") {
    setTimeout(renderEquityChart, 50);
  }
}

// ── Init ─────────────────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", () => {
  updateClock();
  setInterval(updateClock, 10000);

  initRouting();
  setupKillSwitch();
  setupLangToggle();
  setupExecuteBtn();

  setupApiToggle();
  setupWatchlistManager();
  TopPicksManager.fetchTopPicks();


  renderAll();

  // 首次加载 + 每 30 秒自动刷新行情数据
  fetchDashboardData();
  setInterval(fetchDashboardData, 30000);

  // 信号页专属数据 (全量 /strategy/signal)
  fetchSignalData();
  setInterval(fetchSignalData, 30000);

  // 执行按钮防连点
  setupExecuteButton();
});

// ══════════════════════════════════════════════════════════════════
// Signal Toast — 控制台模拟触发器 (Legacy Fallback)
// ESM 版在 js/components/signal-toast.js, 此处为降级保证
// ══════════════════════════════════════════════════════════════════

(function () {
  if (window.triggerMockSignal) return; // ESM 版已注册

  const DEFAULT_SIGNAL = {
    ticker: "AAPL",
    type: "LEAPS_CALL",
    dte: 365,
    reason: "RSI 超卖且 IVR 极低",
  };

  function showSignalToast(payload) {
    // 移除旧 toast
    document.querySelector(".signal-toast")?.remove();

    const p = { ...DEFAULT_SIGNAL, ...payload };
    const typeLabel =
      p.type === "LEAPS_CALL" ? "LEAPS 看涨" :
        p.type === "LEAPS_PUT" ? "LEAPS 看跌" : p.type;

    const el = document.createElement("div");
    el.className = "signal-toast signal-toast--visible";
    el.innerHTML = `
      <button class="signal-toast-close" onclick="this.parentElement.remove()">×</button>
      <div class="signal-toast-header">
        <span class="signal-toast-badge">📡 SIGNAL</span>
        <span class="signal-toast-ticker">${p.ticker}</span>
      </div>
      <div class="signal-toast-type">${typeLabel} · DTE ${p.dte}d</div>
      <div class="signal-toast-reason">${p.reason}</div>
      <button class="signal-toast-cta" id="btnSignalCTA">⚡ 立即前往组装</button>
    `;
    document.body.appendChild(el);

    el.querySelector("#btnSignalCTA").addEventListener("click", () => {
      // 切换标的
      if (typeof setGlobalTicker === "function") setGlobalTicker(p.ticker);
      // 路由到策略工作室
      if (typeof navigateTo === "function") navigateTo("signal");
      // 关闭 toast
      el.remove();
      console.log("[SignalToast] → Studio with:", p);
    });
  }

  window.triggerMockSignal = function (overrides) {
    const payload = { ...DEFAULT_SIGNAL, ...overrides };
    console.log("[SignalToast] 🔔 Mock signal:", payload);
    showSignalToast(payload);
    return payload;
  };

  window.showSignalToast = showSignalToast;
})();
