# retrieval_eval.py — computes rich retrieval metrics from retrieval_results.json
# Usage (from repo root or /evaluation):
#   python evaluation/retrieval_eval.py > evaluation/retrieval_scores.json

import json, math, sys, os
from collections import defaultdict

def load(path):
    with open(path, "r") as f:
        return json.load(f)

def mrr_at_k(preds, gold, k=10):
    for i, lab in enumerate(preds[:k], start=1):
        if lab in gold:
            return 1.0 / i
    return 0.0

def acc_at_k(preds, gold, k=1):
    return 1.0 if any(lab in gold for lab in preds[:k]) else 0.0

def precision_at_k(preds, gold, k=10):
    if k == 0: return 0.0
    hits = sum(1 for lab in preds[:k] if lab in gold)
    return hits / float(k)

def recall_at_k(preds, gold, k=10):
    if not gold: return 0.0
    hits = sum(1 for lab in preds[:k] if lab in gold)
    return hits / float(len(gold))

def ndcg_at_k(preds, gold, k=10):
    dcg = 0.0
    for i, lab in enumerate(preds[:k], start=1):
        rel = 1.0 if lab in gold else 0.0
        if rel:
            dcg += rel / math.log2(i + 1)
    # ideal DCG: all relevant up front (cap by k)
    G = min(len(gold), k)
    if G == 0: return 0.0
    idcg = sum(1.0 / math.log2(i + 1) for i in range(1, G + 1))
    return dcg / idcg if idcg > 0 else 0.0

def average_rank(preds, gold, k=10):
    ranks = []
    for lab in gold:
        if lab in preds[:k]:
            ranks.append(preds[:k].index(lab) + 1)
    return sum(ranks) / len(ranks) if ranks else None

def evaluate_retrieval(gold_path="evaluation/retrieval_data.json",
                       preds_path="evaluation/retrieval_results.json",
                       k_values=(1,3,5,10)):
    gold = load(gold_path)
    preds_all = load(preds_path)

    by_id = {q["id"]: q for q in gold["retrieval_queries"]}
    rows = []
    for qid, q in by_id.items():
        gold_labels = [c.get("clause_label","") for c in q["relevant_chunks"] if c.get("clause_label")]
        preds = preds_all.get(qid, {}).get("ranked_clause_labels", [])
        row = {
            "id": qid,
            "gold": gold_labels,
            "preds": preds,
            "mrr@10": mrr_at_k(preds, gold_labels, k=10),
        }
        for k in k_values:
            row[f"top{k}_acc"] = acc_at_k(preds, gold_labels, k)
            row[f"p@{k}"] = precision_at_k(preds, gold_labels, k)
            row[f"r@{k}"] = recall_at_k(preds, gold_labels, k)
            row[f"ndcg@{k}"] = ndcg_at_k(preds, gold_labels, k)
        row["avg_rank@10"] = average_rank(preds, gold_labels, k=10)
        row["coverage@10"] = 1.0 if row["avg_rank@10"] is not None else 0.0
        rows.append(row)

    # aggregate
    n = len(rows) or 1
    agg = {
        "n_queries": len(rows),
        "mrr@10": sum(r["mrr@10"] for r in rows) / n,
        "coverage@10": sum(r["coverage@10"] for r in rows) / n,
        "avg_rank@10": round(
            sum(r["avg_rank@10"] for r in rows if r["avg_rank@10"] is not None) /
            max(1, sum(1 for r in rows if r["avg_rank@10"] is not None)), 4
        ) if any(r["avg_rank@10"] is not None for r in rows) else None,
    }
    for k in k_values:
        for key in (f"top{k}_acc", f"p@{k}", f"r@{k}", f"ndcg@{k}"):
            agg[key] = sum(r[key] for r in rows) / n

    out = {"summary": agg, "per_query": rows}
    print(json.dumps(out, indent=2))

if __name__ == "__main__":
    # Allow running from repo root or evaluation/
    base = "evaluation" if os.path.exists("evaluation/retrieval_data.json") else "."
    evaluate_retrieval(
        gold_path=os.path.join(base, "retrieval_data.json"),
        preds_path=os.path.join(base, "retrieval_results.json"),
    )
