"""Answer questions from the authenticated user's imported Plaid JSON."""
from __future__ import annotations

import json
import logging
import os
import re
from typing import Any, Dict, List, Optional

import httpx

from .plaid_service import PlaidService

logger = logging.getLogger(__name__)

LOOKBACK_DAYS = 90
MAX_TXNS = 300
MAX_JSON_CHARS = 80_000
DEFAULT_MODEL = "gemini-2.5-flash"

SYSTEM_PROMPT = """You are Maya, Wise Wallet's personal finance advisor. You work with this one user. You already have their Plaid transactions and balances. You give advice.

You are not a report generator. You are not a compliance bot. When they ask how to save, budget, cut spending, or get ahead, you coach them using their numbers.

How to answer:
- Talk like a sharp advisor: second person, warm, direct, no filler.
- Open with the one insight that matters (what's leaking money, what's healthy, what's off). Never open with a preamble.
- Then 2–4 specific actions. Each action names a category or merchant and a dollar amount. Prefer "skip 4 of the 11 Uber Eats orders (~$86/mo)" over "eat out less".
- Tie advice to their cash flow: income vs spend, leftover, biggest categories, repeating merchants.
- End with one short question that moves the plan forward.
- Keep it under ~180 words unless they asked for detail.
- Never mention Plaid, JSON, imports, APIs, "your data", or that you analyzed anything. Talk about their money as if you already know it. No "based on your transactions" throat-clearing.

Grounding:
- Use only PLAID_JSON for facts. Positive amount = money out (spend). Negative = money in.
- Never invent transactions, merchants, balances, or income.
- If a detail isn't in the JSON, skip it or say you don't see it — then still advise from what you do see.
- If the JSON is empty, say they need a synced bank connection, then give generic starter advice.

You SHOULD advise on: spending cuts, savings rate, budgets, sinking funds, subscriptions, cash-flow timing, emergency fund, debt payoff order in general terms.
You should NOT: pick stocks or crypto, promise returns, file their taxes, or give legal advice. If they ask for that, decline that slice only and steer back to cash-flow advice.

Never say you "cannot provide financial advice" or that your job is only to analyze data. Advising is the job.

Bad: "Based on your imported Plaid data, here's an analysis of your spending patterns:"
Good: "Food is $420 of $1,800 spend (23%). Cutting the $64/wk on DoorDash to twice a month frees ~$170/mo. Want that as a grocery cap or a transfer-to-savings rule?"
"""


def summarize_transactions(transactions: List[Dict[str, Any]]) -> Dict[str, Any]:
    spend = 0.0
    income = 0.0
    by_category: Dict[str, float] = {}
    by_merchant: Dict[str, float] = {}
    for tx in transactions:
        amt = float(tx.get("amount") or 0)
        cat = tx.get("category") or ["Other"]
        primary = cat[0] if isinstance(cat, list) and cat else str(cat or "Other")
        merchant = tx.get("merchant_name") or tx.get("name") or "Unknown"
        if amt > 0:
            spend += amt
            by_category[primary] = by_category.get(primary, 0.0) + amt
            by_merchant[merchant] = by_merchant.get(merchant, 0.0) + amt
        elif amt < 0:
            income += abs(amt)
    leftover = round(income - spend, 2)
    return {
        "transaction_count": len(transactions),
        "total_spend": round(spend, 2),
        "total_income": round(income, 2),
        "leftover": leftover,
        "savings_rate_pct": round((leftover / income) * 100, 1) if income else None,
        "by_category": {k: round(v, 2) for k, v in sorted(by_category.items(), key=lambda x: -x[1])[:12]},
        "top_merchants": {k: round(v, 2) for k, v in sorted(by_merchant.items(), key=lambda x: -x[1])[:8]},
    }


def build_plaid_kb(accounts: List[Dict[str, Any]], transactions: List[Dict[str, Any]]) -> Dict[str, Any]:
    txns = transactions[:MAX_TXNS]
    return {
        "amount_convention": "Plaid: positive amount = spend (money out); negative = money in.",
        "accounts": accounts,
        "transactions": txns,
        "summary": summarize_transactions(txns),
    }


def serialize_kb(kb: Dict[str, Any]) -> str:
    txns = list(kb.get("transactions") or [])
    while True:
        payload = {
            **kb,
            "transactions": txns,
            "summary": summarize_transactions(txns),
        }
        raw = json.dumps(payload, default=str, separators=(",", ":"))
        if len(raw) <= MAX_JSON_CHARS or not txns:
            return raw
        txns = txns[: max(len(txns) // 2, 0)]


def build_user_message(question: str, kb_json: str) -> str:
    return (
        "Here is this user's Plaid data. Advise them.\n\n"
        f"PLAID_JSON:\n{kb_json}\n\n"
        f"QUESTION:\n{question}"
    )


def build_contents(
    question: str,
    kb_json: str,
    previous_messages: Optional[List[Dict[str, Any]]] = None,
) -> List[Dict[str, Any]]:
    contents: List[Dict[str, Any]] = []
    for msg in (previous_messages or [])[-5:]:
        content = (msg.get("content") or "").strip()
        if not content:
            continue
        role = "user" if msg.get("role") == "user" else "model"
        contents.append({"role": role, "parts": [{"text": content}]})
    contents.append({"role": "user", "parts": [{"text": build_user_message(question, kb_json)}]})
    return contents


def _gemini(contents: List[Dict[str, Any]]) -> str:
    key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not key:
        raise RuntimeError("GEMINI_API_KEY is not set")
    model = os.getenv("GEMINI_MODEL", DEFAULT_MODEL)
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    response = httpx.post(
        url,
        params={"key": key},
        json={
            "system_instruction": {"parts": [{"text": SYSTEM_PROMPT}]},
            "contents": contents,
            "generationConfig": {
                "temperature": 0.7,
                "maxOutputTokens": 1024,
            },
        },
        timeout=60.0,
    )
    response.raise_for_status()
    data = response.json()
    parts = (
        data.get("candidates", [{}])[0]
        .get("content", {})
        .get("parts", [])
    )
    text = "".join(part.get("text", "") for part in parts).strip()
    if not text:
        raise RuntimeError("Empty model response")
    return _strip_source_talk(text)


def _strip_source_talk(text: str) -> str:
    text = re.sub(
        r"(?is)^(based on|from|using|according to)\s+(your\s+)?(imported\s+)?(plaid\s+)?(data|transactions|json)\s*[,:]?\s*"
        r"(here'?s an analysis of your spending patterns\s*[:.]?\s*)?",
        "",
        text,
        count=1,
    )
    text = re.sub(r"(?i)\bimported plaid data\b", "your spending", text)
    text = re.sub(r"(?i)\bplaid (data|json|transactions)\b", "your spending", text)
    text = re.sub(r"(?i)\bplaid\b", "", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    return text.strip()


class AssistantService:
    def __init__(self, plaid: Optional[PlaidService] = None):
        self.plaid = plaid or PlaidService()

    def load_kb(self, user_id: str) -> Dict[str, Any]:
        imported = self.plaid.get_imported_data(user_id, LOOKBACK_DAYS)
        return build_plaid_kb(imported["accounts"], imported["transactions"])

    def query(
        self,
        user_id: str,
        question: str,
        previous_messages: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        kb = self.load_kb(user_id)
        kb_json = serialize_kb(kb)
        answer = _gemini(build_contents(question, kb_json, previous_messages))
        return {
            "answer": answer,
            "citations": [],
            "used_tools": [],
            "metadata": {
                "user_id": user_id,
                "model": os.getenv("GEMINI_MODEL", DEFAULT_MODEL),
                "transaction_count": len(kb["transactions"]),
                "account_count": len(kb["accounts"]),
                "source": "plaid-json",
            },
        }


def _self_check() -> None:
    txs = [
        {"amount": 12.5, "category": ["Food"], "merchant_name": "Cafe"},
        {"amount": -100.0, "category": ["Transfer"], "merchant_name": "Payroll"},
        {"amount": 40.0, "category": ["Food"], "merchant_name": "Diner"},
    ]
    summary = summarize_transactions(txs)
    assert summary["total_spend"] == 52.5, summary
    assert summary["total_income"] == 100.0, summary
    assert summary["leftover"] == 47.5, summary
    assert summary["by_category"]["Food"] == 52.5, summary
    assert summary["top_merchants"]["Diner"] == 40.0, summary
    kb = build_plaid_kb([{"account_id": "a1", "balance": 10}], txs)
    raw = serialize_kb(kb)
    parsed = json.loads(raw)
    assert parsed["summary"]["total_spend"] == 52.5
    assert "Advising is the job" in SYSTEM_PROMPT
    assert "Never mention Plaid" in SYSTEM_PROMPT
    assert "Good:" in SYSTEM_PROMPT and "Bad:" in SYSTEM_PROMPT
    cleaned = _strip_source_talk(
        "Based on your imported Plaid data, here's an analysis of your spending patterns: Food is $420."
    )
    assert "Plaid" not in cleaned
    assert cleaned.startswith("Food")
    user_msg = build_user_message("Help me save more money", raw)
    assert "PLAID_JSON" in user_msg and "Help me save more money" in user_msg
    contents = build_contents("Help me save more money", raw, [{"role": "user", "content": "hi"}])
    assert contents[-1]["role"] == "user"
    huge = [{"amount": 1, "category": ["A"], "transaction_id": str(i)} for i in range(5000)]
    assert len(serialize_kb(build_plaid_kb([], huge))) <= MAX_JSON_CHARS
    print("assistant_service self-check ok")


if __name__ == "__main__":
    _self_check()
