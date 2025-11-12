# generation_eval.py — computes ROUGE-1/ROUGE-L, BLEU-1, BERTScore (if available), EM, lengths.
# Usage:
#   python evaluation/generation_eval.py > evaluation/generation_scores.json

import json, os, re
from collections import defaultdict, Counter
from typing import List, Tuple
import torch

import transformers, logging
transformers.logging.set_verbosity_error()
logging.getLogger("transformers.modeling_utils").setLevel(logging.ERROR)


# --- tiny tokenizer (no external downloads)
def tok(s: str) -> List[str]:
    s = re.sub(r"<[^>]+>", " ", s)
    s = re.sub(r"[^\w\s]+", " ", s, flags=re.UNICODE)
    return [t for t in s.lower().split() if t]

def rouge_1_f(ref: List[str], hyp: List[str]) -> float:
    ref_ct = Counter(ref); hyp_ct = Counter(hyp)
    overlap = sum((ref_ct & hyp_ct).values())
    p = overlap / max(1, sum(hyp_ct.values()))
    r = overlap / max(1, sum(ref_ct.values()))
    return 0.0 if (p+r)==0 else 2*p*r/(p+r)

def lcs(a: List[str], b: List[str]) -> int:
    # classic DP
    dp = [[0]*(len(b)+1) for _ in range(len(a)+1)]
    for i in range(1,len(a)+1):
        for j in range(1,len(b)+1):
            dp[i][j] = dp[i-1][j-1]+1 if a[i-1]==b[j-1] else max(dp[i-1][j], dp[i][j-1])
    return dp[-1][-1]

def rouge_l_f(ref: List[str], hyp: List[str]) -> float:
    L = lcs(ref, hyp)
    p = L / max(1, len(hyp))
    r = L / max(1, len(ref))
    return 0.0 if (p+r)==0 else 2*p*r/(p+r)

def bleu1(ref: List[str], hyp: List[str]) -> float:
    ref_ct = Counter(ref); hyp_ct = Counter(hyp)
    overlap = sum(min(hyp_ct[w], ref_ct[w]) for w in hyp_ct)
    p = overlap / max(1, sum(hyp_ct.values()))
    bp = 1.0 if len(hyp) > len(ref) else (0.0 if len(hyp)==0 else (len(hyp)/max(1,len(ref))))
    return p * bp  # simple BLEU-1 with brevity penalty

def try_bertscore(cands: List[str], refs: List[str]) -> float:
    try:
        from bert_score import score as bert_score
        P, R, F1 = bert_score(cands, refs, lang="en", verbose=False)
        return float(F1.mean())
    except Exception:
        return None

def evaluate(gold_path="evaluation/rouge_data.json", preds_path="evaluation/gen_outputs.json"):
    gold = json.load(open(gold_path))
    preds = json.load(open(preds_path))

    by_id = {q["id"]: q for q in gold["qna_pairs"]}
    rows = []
    refs_all, hyps_all = [], []

    diffs = defaultdict(list)

    for qid, q in by_id.items():
        ref = q["reference_answer"].strip()
        hyp = preds.get(qid, {}).get("answer", "").strip()
        ref_t, hyp_t = tok(ref), tok(hyp)

        r1 = rouge_1_f(ref_t, hyp_t)
        rl = rouge_l_f(ref_t, hyp_t)
        bl = bleu1(ref_t, hyp_t)
        em = 1.0 if hyp.strip().lower() == ref.strip().lower() else 0.0
        row = {
            "id": qid,
            "category": q.get("category"),
            "difficulty": q.get("difficulty"),
            "rouge1_f": r1, "rougeL_f": rl,
            "bleu1": bl, "exact_match": em,
            "len_ref": len(ref_t), "len_hyp": len(hyp_t),
            "answer": hyp
        }
        rows.append(row)
        refs_all.append(ref); hyps_all.append(hyp)
        diffs[q.get("difficulty","unknown")].append(row)

    # aggregates
    n = len(rows) or 1
    avg_len_ratio = sum(r["len_hyp"]/max(1,r["len_ref"]) for r in rows)/n
    agg = {
        "n_questions": len(rows),
        "rouge1_f": sum(r["rouge1_f"] for r in rows)/n,
        "rougeL_f": sum(r["rougeL_f"] for r in rows)/n,
        "bleu1": sum(r["bleu1"] for r in rows)/n,
        "bert_f1": try_bertscore(hyps_all, refs_all),  # may be None if package missing
        "exact_match": sum(r["exact_match"] for r in rows)/n,
        "avg_answer_len_tokens": sum(r["len_hyp"] for r in rows)/n,
        "len_ratio": avg_len_ratio,
    }

    # difficulty breakdown (ROUGE only to keep table tidy)
    by_diff = []
    for d, items in diffs.items():
        m = len(items) or 1
        by_diff.append({
            "difficulty": d,
            "n": len(items),
            "rouge1_f": sum(x["rouge1_f"] for x in items)/m,
            "rougeL_f": sum(x["rougeL_f"] for x in items)/m,
        })

    out = {"summary": agg, "by_difficulty": by_diff, "per_question": rows}
    print(json.dumps(out, indent=2))

if __name__ == "__main__":
    base = "evaluation" if os.path.exists("evaluation/rouge_data.json") else "."
    evaluate(
        gold_path=os.path.join(base, "rouge_data.json"),
        preds_path=os.path.join(base, "gen_outputs.json"),
    )
