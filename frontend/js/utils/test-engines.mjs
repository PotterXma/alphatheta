// ══════════════════════════════════════════════════════════════════
// Payoff Engine + Market Helpers — Smoke Tests
// Run: node js/utils/test-engines.mjs
// ══════════════════════════════════════════════════════════════════

import { calculateComboPayoff, calculateNetPremium } from "./payoff-engine.js";
import { snapToStrike, resolveTemplate } from "./market-helpers.js";
import { STRATEGY_TEMPLATES } from "./strategy-templates.js";

let passed = 0;
let failed = 0;
const ok = (label, cond) => {
    if (cond) { passed++; console.log(`  ✅ ${label}`); }
    else { failed++; console.log(`  ❌ ${label}`); }
};

// ──────────────────────────────────────────
// §1: snapToStrike
// ──────────────────────────────────────────
console.log("\n=== snapToStrike ===");
const strikes = [490, 495, 500, 505, 510, 515, 520];

ok("ATM @ 502.3 → 500", snapToStrike(502.3, 0, strikes) === 500);
ok("ATM+1 → 505", snapToStrike(502.3, +1, strikes) === 505);
ok("ATM-2 → 490", snapToStrike(502.3, -2, strikes) === 490);
ok("ATM+10 clamp → 520", snapToStrike(502.3, +10, strikes) === 520);
ok("ATM-10 clamp → 490", snapToStrike(502.3, -10, strikes) === 490);
ok("empty → round(spot)", snapToStrike(502.3, 0, []) === 502);

// ──────────────────────────────────────────
// §2: resolveTemplate (Iron Condor)
// ──────────────────────────────────────────
console.log("\n=== resolveTemplate ===");
const ic = STRATEGY_TEMPLATES.find((t) => t.id === "iron-condor");
const legs = resolveTemplate(ic, 500, strikes, "2026-04-15");

ok("IC has 4 legs", legs.length === 4);
ok("Leg 0 buy put", legs[0].action === "buy" && legs[0].right === "put");
ok("Leg 1 sell put", legs[1].action === "sell" && legs[1].right === "put");
ok("Leg 2 sell call", legs[2].action === "sell" && legs[2].right === "call");
ok("Leg 3 buy call", legs[3].action === "buy" && legs[3].right === "call");
ok("Leg 0 strike=490 (-4)", legs[0].strike === 490);
ok("Leg 1 strike=490 (-2)", legs[1].strike === 490);
ok("Leg 2 strike=510 (+2)", legs[2].strike === 510);
ok("Leg 3 strike=520 (+4)", legs[3].strike === 520);

// Calendar spread DTE offsets
const cal = STRATEGY_TEMPLATES.find((t) => t.id === "calendar-spread-put");
const calLegs = resolveTemplate(cal, 500, strikes, "2026-04-15");
ok("Cal near exp = 2026-04-15", calLegs[0].expiration === "2026-04-15");
ok("Cal far exp = 2026-05-15", calLegs[1].expiration === "2026-05-15");

// ──────────────────────────────────────────
// §3: calculateComboPayoff — Naked Sell Put
// ──────────────────────────────────────────
console.log("\n=== Payoff: Naked Sell Put ===");
const nakedPut = [
    { type: "option", right: "put", action: "sell", strike: 500, price: 5, quantity: 1, multiplier: 100 }
];
const r1 = calculateComboPayoff(nakedPut, 500);

ok("pricePoints length ~1000", r1.pricePoints.length >= 900 && r1.pricePoints.length <= 1200);
ok("maxProfit = 500 (net premium)", r1.maxProfit === 500);
ok("maxLoss = Unlimited Risk", r1.maxLoss === "Unlimited Risk");
ok("1 breakeven", r1.breakevens.length === 1);
ok("breakeven ≈ 495", Math.abs(r1.breakevens[0] - 495) < 1);

// ──────────────────────────────────────────
// §4: Long Call — Unlimited profit
// ──────────────────────────────────────────
console.log("\n=== Payoff: Long Call ===");
const longCall = [
    { type: "option", right: "call", action: "buy", strike: 500, price: 10, quantity: 1, multiplier: 100 }
];
const r2 = calculateComboPayoff(longCall, 500);

ok("maxProfit = Unlimited", r2.maxProfit === "Unlimited");
ok("maxLoss = -1000", r2.maxLoss === -1000);
ok("1 breakeven", r2.breakevens.length === 1);
ok("breakeven ≈ 510", Math.abs(r2.breakevens[0] - 510) < 1);

// ──────────────────────────────────────────
// §5: Iron Condor — Both capped
// ──────────────────────────────────────────
console.log("\n=== Payoff: Iron Condor ===");
const ironCondor = [
    { type: "option", right: "put", action: "buy", strike: 480, price: 1, quantity: 1, multiplier: 100 },
    { type: "option", right: "put", action: "sell", strike: 490, price: 3, quantity: 1, multiplier: 100 },
    { type: "option", right: "call", action: "sell", strike: 510, price: 3, quantity: 1, multiplier: 100 },
    { type: "option", right: "call", action: "buy", strike: 520, price: 1, quantity: 1, multiplier: 100 },
];
const r3 = calculateComboPayoff(ironCondor, 500);

ok("maxProfit is number (capped)", typeof r3.maxProfit === "number");
ok("maxLoss is number (capped)", typeof r3.maxLoss === "number");
ok("maxProfit = 400 (net credit)", r3.maxProfit === 400);
ok("maxLoss = -600", r3.maxLoss === -600);
ok("2 breakevens", r3.breakevens.length === 2);

// ──────────────────────────────────────────
// §6: Net Premium
// ──────────────────────────────────────────
console.log("\n=== Net Premium ===");
const np1 = calculateNetPremium(ironCondor);
ok("IC net credit = 400", np1.net === 400);
ok("IC isCredit = true", np1.isCredit === true);

const np2 = calculateNetPremium(longCall);
ok("Long call debit = -1000", np2.net === -1000);
ok("Long call isCredit = false", np2.isCredit === false);

// ──────────────────────────────────────────
// §7: Edge cases
// ──────────────────────────────────────────
console.log("\n=== Edge Cases ===");
const empty = calculateComboPayoff([], 500);
ok("empty legs → empty result", empty.pricePoints.length === 0);

const zeroQty = calculateComboPayoff(
    [{ type: "option", right: "call", action: "buy", strike: 500, price: 5, quantity: 0, multiplier: 100 }],
    500
);
ok("qty=0 → all payoff = 0", zeroQty.payoffData.every((v) => v === 0));

// ──────────────────────────────────────────
// §8: Deep OTM — Dynamic Bounding (致命 Bug 回归测试)
// ──────────────────────────────────────────
console.log("\n=== Deep OTM: Sell $40 Put on $100 stock ===");
const deepOTM = [
    { type: "option", right: "put", action: "sell", strike: 40, price: 0.5, quantity: 1, multiplier: 100 }
];
const r4 = calculateComboPayoff(deepOTM, 100);

ok("loBound covers $40 strike", r4.pricePoints[0] <= 32);        // 40 * 0.8 = 32
ok("maxProfit = 50 (0.5×100)", r4.maxProfit === 50);
ok("maxLoss = Unlimited Risk", r4.maxLoss === "Unlimited Risk");  // 旧版 Bug: 这里会误判为有限
ok("1 breakeven", r4.breakevens.length === 1);
ok("breakeven ≈ 39.5", Math.abs(r4.breakevens[0] - 39.5) < 1);

// §8b: Deep OTM Call — high strike
console.log("\n=== Deep OTM: Buy $200 Call on $100 stock ===");
const deepOTMCall = [
    { type: "option", right: "call", action: "buy", strike: 200, price: 0.3, quantity: 1, multiplier: 100 }
];
const r5 = calculateComboPayoff(deepOTMCall, 100);

ok("hiBound covers $200 strike", r5.pricePoints[r5.pricePoints.length - 1] >= 240); // 200 * 1.2
ok("maxProfit = Unlimited", r5.maxProfit === "Unlimited");
ok("maxLoss = -30 (0.3×100)", r5.maxLoss === -30);
ok("1 breakeven", r5.breakevens.length === 1);
ok("breakeven ≈ 200.3", Math.abs(r5.breakevens[0] - 200.3) < 1);

// ──────────────────────────────────────────
// Results
// ──────────────────────────────────────────
console.log(`\n${"═".repeat(50)}`);
console.log(`Results: ${passed} passed, ${failed} failed`);
console.log(`${"═".repeat(50)}\n`);
process.exit(failed > 0 ? 1 : 0);
