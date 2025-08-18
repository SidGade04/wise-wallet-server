import re
from ..models.safety_models import SafetyCheck
from ..core.config import settings

INVEST = re.compile(r"\b(buy|sell|short|long|option|stock|etf|crypto|coin|portfolio|dividend|ticker|AAPL|NVDA|SPY)\b", re.I)
TAX    = re.compile(r"\b(tax|deduct|write[- ]?off|irs|1040|capital gains|withholding)\b", re.I)
LEGAL  = re.compile(r"\b(law|lawsuit|attorney|legal advice)\b", re.I)

def check_safety(prompt: str) -> SafetyCheck:
    if not settings.enable_safety:
        return SafetyCheck(allowed=True)
    if INVEST.search(prompt):
        return SafetyCheck(allowed=False, reason="investment_advice")
    if TAX.search(prompt):
        return SafetyCheck(allowed=False, reason="tax_advice")
    if LEGAL.search(prompt):
        return SafetyCheck(allowed=False, reason="legal_advice")
    return SafetyCheck(allowed=True)
