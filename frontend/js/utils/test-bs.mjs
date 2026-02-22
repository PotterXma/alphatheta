// Quick BS benchmark — run with: node js/utils/test-bs.mjs
import {
    normCDF, normPDF,
    blackScholes, bsDelta, bsGamma, bsTheta, bsVega,
    calculatePortfolioGreeks, calculateComboPayoffDualCurve, legPayoffBS,
} from "./payoff-engine.js";

let pass = 0, fail = 0;
function assert(label, cond) {
    if (cond) { pass++; console.log(`  ✅ ${label}`); }
    else { fail++; console.log(`  ❌ ${label}`); }
}

console.log("\n═══ normCDF Sanity ═══");
assert("normCDF(0) ≈ 0.5", Math.abs(normCDF(0) - 0.5) < 1e-7);
assert("normCDF(1) ≈ 0.8413", Math.abs(normCDF(1) - 0.8413) < 0.001);
assert("normCDF(-1) ≈ 0.1587", Math.abs(normCDF(-1) - 0.1587) < 0.001);
assert("normCDF(3) ≈ 0.9987", Math.abs(normCDF(3) - 0.9987) < 0.001);

console.log("\n═══ Black-Scholes Pricing ═══");
// S=100, K=100, T=1yr, r=0.05, σ=0.20 → C ≈ 10.4506
const c1 = blackScholes(100, 100, 1, 0.05, 0.20, "call");
console.log(`  Call price: ${c1.toFixed(4)}`);
assert("ATM Call ≈ 10.45", Math.abs(c1 - 10.4506) < 0.05);

const p1 = blackScholes(100, 100, 1, 0.05, 0.20, "put");
console.log(`  Put  price: ${p1.toFixed(4)}`);
// Put-Call Parity: P = C - S + K*e^(-rT)
const pParity = c1 - 100 + 100 * Math.exp(-0.05);
assert("Put-Call Parity holds", Math.abs(p1 - pParity) < 0.001);

// OTM call: S=100, K=120
const c2 = blackScholes(100, 120, 0.5, 0.05, 0.30, "call");
console.log(`  OTM Call (K=120): ${c2.toFixed(4)}`);
assert("OTM Call > 0", c2 > 0);
assert("OTM Call < ATM Call", c2 < c1);

// At expiry: T=0
assert("Call at expiry ITM", blackScholes(110, 100, 0, 0.05, 0.20, "call") === 10);
assert("Call at expiry OTM", blackScholes(90, 100, 0, 0.05, 0.20, "call") === 0);
assert("Put at expiry ITM", blackScholes(90, 100, 0, 0.05, 0.20, "put") === 10);

console.log("\n═══ Greeks ═══");
const delta = bsDelta(100, 100, 1, 0.05, 0.20, "call");
console.log(`  Delta ATM Call: ${delta.toFixed(4)}`);
assert("ATM Call Delta ≈ 0.64", Math.abs(delta - 0.6368) < 0.02);
assert("ATM Put Delta ≈ -0.36", Math.abs(bsDelta(100, 100, 1, 0.05, 0.20, "put") - (-0.3632)) < 0.02);

const gamma = bsGamma(100, 100, 1, 0.05, 0.20, "call");
console.log(`  Gamma ATM: ${gamma.toFixed(6)}`);
assert("Gamma > 0", gamma > 0);
assert("Gamma Call == Gamma Put", Math.abs(gamma - bsGamma(100, 100, 1, 0.05, 0.20, "put")) < 1e-10);

const theta = bsTheta(100, 100, 1, 0.05, 0.20, "call");
console.log(`  Theta/day ATM Call: ${theta.toFixed(4)}`);
assert("Theta < 0 (time decay)", theta < 0);

const vega = bsVega(100, 100, 1, 0.05, 0.20, "call");
console.log(`  Vega/1% ATM: ${vega.toFixed(4)}`);
assert("Vega > 0", vega > 0);
assert("Vega Call == Vega Put", Math.abs(vega - bsVega(100, 100, 1, 0.05, 0.20, "put")) < 1e-10);

console.log("\n═══ legPayoffBS ═══");
const leg = { type: "option", right: "call", action: "buy", strike: 100, price: 10.45, quantity: 1, multiplier: 100 };
const pl = legPayoffBS(leg, 110, 30 / 365, 0.20, 0.05);
console.log(`  T+30 P&L (S=110): $${pl.toFixed(2)}`);
assert("ITM leg has positive P&L", pl > 0);

console.log("\n═══ Dual Curve ═══");
const icLegs = [
    { type: "option", right: "put", action: "buy", strike: 95, price: 1.0, quantity: 1, multiplier: 100 },
    { type: "option", right: "put", action: "sell", strike: 100, price: 2.5, quantity: 1, multiplier: 100 },
    { type: "option", right: "call", action: "sell", strike: 110, price: 2.0, quantity: 1, multiplier: 100 },
    { type: "option", right: "call", action: "buy", strike: 115, price: 0.5, quantity: 1, multiplier: 100 },
];
const dual = calculateComboPayoffDualCurve(icLegs, 105, 15, 0.25);
assert("201 price points", dual.pricePoints.length === 201);
assert("expiry array matches", dual.expiryData.length === 201);
assert("T+n array matches", dual.tnData.length === 201);
// T+n curve should be smoother (less extreme) than expiry
const expiryRange = Math.max(...dual.expiryData) - Math.min(...dual.expiryData);
const tnRange = Math.max(...dual.tnData) - Math.min(...dual.tnData);
console.log(`  Expiry range: $${expiryRange.toFixed(0)}, T+n range: $${tnRange.toFixed(0)}`);
assert("T+n range < Expiry range (time value smooths)", tnRange < expiryRange);

console.log("\n═══ Portfolio Greeks ═══");
const greeks = calculatePortfolioGreeks(icLegs, 105, 30, 0.25);
console.log(`  Net Delta: ${greeks.netDelta}`);
console.log(`  Net Gamma: ${greeks.netGamma}`);
console.log(`  Net Theta: ${greeks.netTheta}`);
console.log(`  Net Vega:  ${greeks.netVega}`);
assert("IC Net Delta near 0 (delta-neutral)", Math.abs(greeks.netDelta) < 30);
assert("IC Net Theta > 0 (time decay benefits seller)", greeks.netTheta > 0);
assert("IC Net Vega < 0 (short vol)", greeks.netVega < 0);

console.log(`\n══════════════════════════════════════════════════`);
console.log(`Results: ${pass} passed, ${fail} failed`);
console.log(`══════════════════════════════════════════════════\n`);
process.exit(fail > 0 ? 1 : 0);
