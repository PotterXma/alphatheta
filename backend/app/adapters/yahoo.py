"""
Yahoo Finance 适配器 — 免费行情数据兜底

使用 yfinance 库直接获取 Yahoo Finance 数据:
- 实时报价 (延迟 ~15 分钟)
- VIX 指数
- RSI-14 技术指标 (自行计算)
- SMA200 距离
- 历史 K 线

限制:
- IP 限速约 2000 req/hour
- 美股延迟 ~15 分钟
- 无期权链实时行情 (需 Tradier)

用法:
    adapter = YahooFinanceAdapter()
    quote = await adapter.get_quote("SPY")
    vix = await adapter.get_vix()
    indicators = await adapter.get_indicators("SPY")
"""

import asyncio
import logging
from datetime import datetime, timezone
from functools import lru_cache

import yfinance as yf

from app.adapters.broker_base import BrokerAdapter, BrokerOrderResponse, BrokerPosition, BrokerQuote

logger = logging.getLogger("alphatheta.adapter.yahoo")


class YahooFinanceAdapter(BrokerAdapter):
    """
    Yahoo Finance 免费数据适配器

    实现 BrokerAdapter 接口的只读部分 (get_quote / get_positions)
    交易操作 (submit/cancel) 会抛出 NotImplementedError
    """

    async def get_quote(self, ticker: str) -> BrokerQuote:
        """从 Yahoo Finance 获取实时报价"""
        try:
            data = await asyncio.to_thread(self._fetch_quote, ticker)
            return data
        except Exception as e:
            logger.error(f"Yahoo quote failed for {ticker}: {e}")
            # 兜底: 返回零值而非崩溃
            return BrokerQuote(ticker=ticker, bid=0, ask=0, last=0, volume=0)

    def _fetch_quote(self, ticker: str) -> BrokerQuote:
        """同步拉取 Yahoo Finance 报价 (在 to_thread 中执行)"""
        t = yf.Ticker(ticker)
        info = t.fast_info

        last = float(info.last_price) if hasattr(info, 'last_price') else 0.0
        # Yahoo Finance 不提供实时 bid/ask, 用 last ± 0.05% 模拟
        spread = last * 0.0005
        volume = int(info.last_volume) if hasattr(info, 'last_volume') else 0

        return BrokerQuote(
            ticker=ticker,
            bid=round(last - spread, 2),
            ask=round(last + spread, 2),
            last=round(last, 2),
            volume=volume,
        )

    async def get_vix(self) -> float:
        """获取 VIX 恐慌指数"""
        try:
            vix = await asyncio.to_thread(self._fetch_vix)
            return vix
        except Exception as e:
            logger.error(f"Yahoo VIX fetch failed: {e}")
            return 18.5  # 默认中性值

    def _fetch_vix(self) -> float:
        """同步拉取 VIX"""
        t = yf.Ticker("^VIX")
        info = t.fast_info
        return round(float(info.last_price), 2) if hasattr(info, 'last_price') else 18.5

    async def get_indicators(self, ticker: str) -> dict:
        """
        计算技术指标: RSI-14, SMA200 距离

        RSI-14 使用 Wilder Smoothing (指数加权移动平均):
        1. 计算每日涨跌幅
        2. 分别计算平均涨幅和平均跌幅 (14 日 EMA)
        3. RSI = 100 - 100 / (1 + 平均涨幅/平均跌幅)
        """
        try:
            data = await asyncio.to_thread(self._compute_indicators, ticker)
            return data
        except Exception as e:
            logger.error(f"Yahoo indicators failed for {ticker}: {e}")
            return {"rsi_14": 50.0, "sma200": 0.0, "sma200_distance": 0.0}

    def _compute_indicators(self, ticker: str) -> dict:
        """同步计算指标"""
        t = yf.Ticker(ticker)
        # 拉取 250 天历史 (SMA200 需要至少 200 个交易日)
        hist = t.history(period="1y")
        if hist.empty or len(hist) < 14:
            return {"rsi_14": 50.0, "sma200": 0.0, "sma200_distance": 0.0}

        closes = hist["Close"]

        # ── RSI-14 (Wilder Smoothing) ──
        # Delta = 今日收盘 - 昨日收盘
        delta = closes.diff()
        gain = delta.where(delta > 0, 0.0)
        loss = (-delta).where(delta < 0, 0.0)

        # 初始 14 日简单平均
        avg_gain = gain.rolling(window=14).mean()
        avg_loss = loss.rolling(window=14).mean()

        # Wilder Smoothing: 后续用 EMA
        for i in range(14, len(avg_gain)):
            avg_gain.iloc[i] = (avg_gain.iloc[i - 1] * 13 + gain.iloc[i]) / 14
            avg_loss.iloc[i] = (avg_loss.iloc[i - 1] * 13 + loss.iloc[i]) / 14

        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        rsi_14 = round(float(rsi.iloc[-1]), 1) if not rsi.empty else 50.0

        # ── SMA200 ──
        sma200 = round(float(closes.tail(200).mean()), 2) if len(closes) >= 200 else 0.0
        current = float(closes.iloc[-1])
        sma200_dist = round((current - sma200) / sma200 * 100, 2) if sma200 > 0 else 0.0

        return {
            "rsi_14": rsi_14,
            "sma200": sma200,
            "sma200_distance": sma200_dist,
            "current_price": round(current, 2),
        }

    # ── 交易操作: 不支持 (Yahoo Finance 是只读数据源) ──

    async def get_option_chain(self, ticker: str, expiration: str = "") -> list[dict]:
        """
        从 yfinance 获取期权链

        yfinance 提供 15 分钟延迟的期权链数据, 包含:
        - strike, bid, ask, lastPrice
        - impliedVolatility (可近似 Delta)
        - openInterest, volume

        注意: yfinance 不直接提供 Greeks (Delta/Gamma),
        我们用 Black-Scholes 近似 Delta:
          Call Delta ≈ N(d1), 简化为 1 - (strike/price × e^(-r×T))
          实际中用 impliedVolatility 给出的 moneyness 估算
        """
        try:
            data = await asyncio.to_thread(
                self._fetch_option_chain, ticker, expiration
            )
            return data
        except Exception as e:
            logger.error(f"Yahoo option chain failed for {ticker}: {e}")
            return []

    def _fetch_option_chain(self, ticker: str, target_expiration: str = "") -> list[dict]:
        """同步拉取期权链 (在 to_thread 中执行)"""
        import math
        from datetime import datetime as dt

        t = yf.Ticker(ticker)
        expirations = t.options  # tuple of 'YYYY-MM-DD' strings
        if not expirations:
            logger.warning(f"No options expirations for {ticker}")
            return []

        # 选择到期日: 优先匹配指定日期, 否则选 20-45 DTE 范围内最近的
        if target_expiration and target_expiration in expirations:
            chosen_exp = target_expiration
        else:
            today = dt.now().date()
            best = None
            for exp_str in expirations:
                exp_date = dt.strptime(exp_str, "%Y-%m-%d").date()
                dte = (exp_date - today).days
                if 20 <= dte <= 45:
                    if best is None or dte < (dt.strptime(best, "%Y-%m-%d").date() - today).days:
                        best = exp_str
            # fallback: 取第一个 > 14 DTE 的
            if not best:
                for exp_str in expirations:
                    exp_date = dt.strptime(exp_str, "%Y-%m-%d").date()
                    if (exp_date - today).days > 14:
                        best = exp_str
                        break
            if not best:
                best = expirations[0]
            chosen_exp = best

        logger.info(f"📋 Fetching option chain for {ticker} exp={chosen_exp}")
        chain = t.option_chain(chosen_exp)

        # 获取标的当前价格 (用于 Delta 估算)
        try:
            current_price = float(t.fast_info.last_price)
        except Exception:
            current_price = 0

        results = []
        exp_date = dt.strptime(chosen_exp, "%Y-%m-%d").date()
        dte = max(1, (exp_date - dt.now().date()).days)
        T = dte / 365.0

        for option_type, df in [("call", chain.calls), ("put", chain.puts)]:
            if df is None or df.empty:
                continue
            for _, row in df.iterrows():
                strike = float(row.get("strike", 0))
                bid = float(row.get("bid", 0))
                ask = float(row.get("ask", 0))
                last_price = float(row.get("lastPrice", 0))
                iv = float(row.get("impliedVolatility", 0))
                oi = int(row.get("openInterest", 0)) if not math.isnan(row.get("openInterest", 0)) else 0
                vol = int(row.get("volume", 0)) if not math.isnan(row.get("volume", 0)) else 0

                # ── Delta 估算 (简化 Black-Scholes) ──
                # 真实 Delta 需要 r (无风险利率) 和精确 IV
                # 简化: moneyness + IV 近似
                if current_price > 0 and iv > 0 and strike > 0:
                    d1 = (math.log(current_price / strike) + (0.5 * iv**2) * T) / (iv * math.sqrt(T))
                    # N(d1) 近似 (Abramowitz & Stegun)
                    from statistics import NormalDist
                    nd1 = NormalDist().cdf(d1)
                    delta = round(nd1, 4) if option_type == "call" else round(nd1 - 1, 4)
                else:
                    delta = 0.0

                # Gamma 估算: Gamma = N'(d1) / (S × σ × √T)
                gamma = 0.0
                if current_price > 0 and iv > 0:
                    try:
                        nprime_d1 = NormalDist().pdf(d1)
                        gamma = round(nprime_d1 / (current_price * iv * math.sqrt(T)), 6)
                    except Exception:
                        pass

                # 构建 OCC symbol: SPY260403C00525000
                exp_compact = exp_date.strftime("%y%m%d")
                strike_int = int(strike * 1000)
                occ_type = "C" if option_type == "call" else "P"
                symbol = f"{ticker}{exp_compact}{occ_type}{strike_int:08d}"

                results.append({
                    "symbol": symbol,
                    "strike": strike,
                    "expiration": chosen_exp,
                    "option_type": option_type,
                    "bid": bid,
                    "ask": ask,
                    "last": last_price,
                    "delta": delta,
                    "gamma": gamma,
                    "open_interest": oi,
                    "volume": vol,
                })

        logger.info(f"📋 {ticker} chain: {len(results)} contracts (exp={chosen_exp}, DTE={dte})")
        return results

    async def submit_order(self, **kwargs) -> BrokerOrderResponse:
        raise NotImplementedError("Yahoo Finance adapter is read-only")

    async def submit_combo_order(
        self, ticker: str, legs: list[dict], net_price: float,
        order_type: str = "limit", idempotency_key: str | None = None,
    ) -> BrokerOrderResponse:
        raise NotImplementedError("Yahoo Finance adapter is read-only — combo orders require Tradier or IBKR")

    async def cancel_order(self, broker_order_id: str) -> bool:
        raise NotImplementedError("Yahoo Finance adapter is read-only")

    async def get_positions(self) -> list[BrokerPosition]:
        return []

    async def get_order_status(self, broker_order_id: str) -> BrokerOrderResponse:
        raise NotImplementedError("Yahoo Finance adapter is read-only")
