from typing import Dict, List

def compute_simple_targets(income: float, fixed: float, variable: float, top_cats: List[Dict]) -> Dict:
    desired_savings = max(0.10 * income, 100.0)
    current_savings = max(income - (fixed + variable), 0.0)
    gap = max(desired_savings - current_savings, 0.0)

    cuts = []
    remaining = gap
    for cat in top_cats[:3]:
        cut = round(0.15 * float(cat["spend"]), 2)
        cuts.append({"cat": cat["cat"], "reduce_by": cut})
        remaining = max(0.0, remaining - cut)
        if remaining <= 0:
            break

    return {"desired_savings": desired_savings, "cuts": cuts, "gap_after": remaining}
