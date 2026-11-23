"""Answer questions from the authenticated user's imported Plaid JSON."""
from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict, List, Optional

import httpx

from .plaid_service import PlaidService

logger = logging.getLogger(__name__)

LOOKBACK_DAYS = 90
MAX_TXNS = 300
MAX_JSON_CHARS = 80_000
DEFAULT_MODEL = "gemini-2.5-flash"

SYSTEM_PROMPT = """You are Wise Wallet's financial assistant.
Answer ONLY from the PLAID_JSON block. That JSON is this user's imported Plaid data.
Plaid amount sign: positive = money leaving the account (spend); negative = money in.
If the JSON does not contain the answer, say you don't have that in the imported data.
Do not invent transactions, balances, or merchants.
Not investment, tax, or legal advice.
Keep answers concise and specific to the numbers in the JSON."""


def summarize_transactions(transactions: List[Dict[str, Any]]) -> Dict[str, Any]:
    spend = 0.0
    income = 0.0
    by_category: Dict[str, float] = {}
    for tx in transactions:
        amt = float(tx.get("amount") or 0)
        cat = tx.get("category") or ["Other"]
        primary = cat[0] if isinstance(cat, list) and cat else str(cat or "Other")
        if amt > 0:
            spend += amt
            by_category[primary] = by_category.get(primary, 0.0) + amt
        elif amt < 0:
            income += abs(amt)
    return {
        "transaction_count": len(transactions),
        "total_spend": round(spend, 2),
        "total_income": round(income, 2),
        "by_category": {k: round(v, 2) for k, v in sorted(by_category.items(), key=lambda x: -x[1])},
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


def build_prompt(
    question: str,
    kb_json: str,
    previous_messages: Optional[List[Dict[str, Any]]] = None,
) -> str:
    history_lines = []
    for msg in (previous_messages or [])[-5:]:
        role = msg.get("role") or "user"
        content = (msg.get("content") or "").strip()
        if content:
            history_lines.append(f"{role}: {content}")
    history = "\n".join(history_lines) or "(none)"
    return (
        f"{SYSTEM_PROMPT}\n\n"
        f"PLAID_JSON:\n{kb_json}\n\n"
        f"RECENT_CHAT:\n{history}\n\n"
        f"QUESTION:\n{question}"
    )


def _gemini(prompt: str) -> str:
    key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not key:
        raise RuntimeError("GEMINI_API_KEY is not set")
    model = os.getenv("GEMINI_MODEL", DEFAULT_MODEL)
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    response = httpx.post(
        url,
        params={"key": key},
        json={"contents": [{"parts": [{"text": prompt}]}]},
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
    return text


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
        prompt = build_prompt(question, kb_json, previous_messages)
        answer = _gemini(prompt)
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
    assert summary["by_category"]["Food"] == 52.5, summary
    kb = build_plaid_kb([{"account_id": "a1", "balance": 10}], txs)
    raw = serialize_kb(kb)
    parsed = json.loads(raw)
    assert "positive" in parsed["amount_convention"].lower()
    assert parsed["summary"]["total_spend"] == 52.5
    prompt = build_prompt("How much on food?", raw, [{"role": "user", "content": "hi"}])
    assert "PLAID_JSON" in prompt and "How much on food?" in prompt
    huge = [{"amount": 1, "category": ["A"], "transaction_id": str(i)} for i in range(5000)]
    assert len(serialize_kb(build_plaid_kb([], huge))) <= MAX_JSON_CHARS
    print("assistant_service self-check ok")


if __name__ == "__main__":
    _self_check()
