# make_report.py — merges retrieval & generation scores into a clean Markdown report.
# Usage:
#   python evaluation/make_report.py \
#       --retrieval_scores evaluation/retrieval_scores.json \
#       --generation_scores evaluation/generation_scores.json

import json, argparse, datetime, os, textwrap

def md_tbl(rows, headers):
    # rows: list[list[str or number]]
    colw = [max(len(str(h)), *(len(str(r[i])) for r in rows)) for i, h in enumerate(headers)]
    def fmt(r): return "| " + " | ".join(str(r[i]).ljust(colw[i]) for i in range(len(headers))) + " |"
    sep = "| " + " | ".join("-"*w for w in colw) + " |"
    return "\n".join([fmt(headers), sep] + [fmt(r) for r in rows])

def load(path): 
    with open(path, "r") as f: 
        return json.load(f)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--retrieval_scores", required=True)
    ap.add_argument("--generation_scores", required=True)
    ap.add_argument("--out_md", default="evaluation/RAG_REPORT.md")
    args = ap.parse_args()

    R = load(args.retrieval_scores)["summary"]
    G = load(args.generation_scores)["summary"]
    Gdiff = load(args.generation_scores).get("by_difficulty", [])

    lines = []
    lines.append("# Casa Amigo — RAG Evaluation Report")
    lines.append(f"_Generated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}_\n")

    # Retrieval
    rows = [
      ["Queries",         R.get("n_queries")],
      ["MRR@10",          round(R.get("mrr@10",0), 4)],
      ["nDCG@10",         round(R.get("ndcg@10",0), 4) if "ndcg@10" in R else "—"],
      ["Precision@10",    round(R.get("p@10",0), 4)],
      ["Recall@10",       round(R.get("r@10",0), 4)],
      ["Coverage@10",     round(R.get("coverage@10",0), 4)],
      ["Top-1 Acc",       round(R.get("top1_acc",0), 4)],
      ["Top-3 Acc",       round(R.get("top3_acc",0), 4)],
      ["Top-5 Acc",       round(R.get("top5_acc",0), 4)],
      ["Top-10 Acc",      round(R.get("top10_acc",0), 4)],
      ["Avg Rank (hit)",  R.get("avg_rank@10") if R.get("avg_rank@10") is not None else "—"],
    ]
    lines.append("## Retrieval")
    lines.append(md_tbl(rows, ["Metric", "Value"]))
    lines.append("")

    # Generation
    rows = [
      ["Questions",          G.get("n_questions")],
      ["ROUGE-1 F",          round(G.get("rouge1_f",0), 4)],
      ["ROUGE-L F",          round(G.get("rougeL_f",0), 4)],
      ["BLEU-1",             round(G.get("bleu1",0), 4)],
      ["BERTScore F1",       round(G.get("bert_f1"), 4) if G.get("bert_f1") is not None else "n/a"],
      ["Exact Match %",      round(G.get("exact_match",0), 4)],
      ["Avg Answer Len (tok)", round(G.get("avg_answer_len_tokens",0), 2)],
      ["Len Ratio",          round(G.get("len_ratio",0), 4)],
    ]
    lines.append("## Generation")
    lines.append(md_tbl(rows, ["Metric", "Value"]))
    lines.append("")

    if Gdiff:
        rows = [[d["difficulty"], d["n"], round(d["rouge1_f"],4), round(d["rougeL_f"],4)] for d in Gdiff]
        lines.append("### Generation by Difficulty")
        lines.append(md_tbl(rows, ["Difficulty","N","ROUGE-1 F","ROUGE-L F"]))
        lines.append("")

    out = "\n".join(lines).strip() + "\n"
    os.makedirs(os.path.dirname(args.out_md), exist_ok=True)
    with open(args.out_md, "w") as f:
        f.write(out)
    print(f"Wrote {args.out_md}")

if __name__ == "__main__":
    main()
