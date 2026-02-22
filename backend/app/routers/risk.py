"""Risk Engine API Router"""

from fastapi import APIRouter

from app.schemas.risk import RiskAssessment, TradeProposal
from app.services.risk_engine import RiskEngine

router = APIRouter()
_engine = RiskEngine()


@router.post("/evaluate", response_model=RiskAssessment)
async def evaluate_trade(proposal: TradeProposal):
    """CRO 风控评估 — 7条 Kill Switch + 执行方案"""
    return _engine.evaluate(proposal)
