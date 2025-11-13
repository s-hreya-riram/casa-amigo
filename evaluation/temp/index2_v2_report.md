# Casa Amigo — RAG Evaluation Report
_Generated: 2025-11-13 18:26_

## Retrieval
| Metric         | Value  |
| -------------- | ------ |
| Queries        | 30     |
| MRR@10         | 0.6667 |
| nDCG@10        | 0.6034 |
| Precision@10   | 0.1033 |
| Recall@10      | 0.7111 |
| Coverage@10    | 0.9    |
| Top-1 Acc      | 0.4333 |
| Top-3 Acc      | 0.9    |
| Top-5 Acc      | 0.9    |
| Top-10 Acc     | 0.9    |
| Avg Rank (hit) | 1.6296 |

## Generation
| Metric               | Value  |
| -------------------- | ------ |
| Questions            | 20     |
| ROUGE-1 F            | 0.3432 |
| ROUGE-L F            | 0.2847 |
| BLEU-1               | 0.2796 |
| BERTScore F1         | 0.879  |
| Exact Match %        | 0.0    |
| Avg Answer Len (tok) | 28.15  |
| Len Ratio            | 0.6365 |

### Generation by Difficulty
| Difficulty | N | ROUGE-1 F | ROUGE-L F |
| ---------- | - | --------- | --------- |
| easy       | 7 | 0.4067    | 0.3504    |
| medium     | 9 | 0.3015    | 0.2425    |
| hard       | 4 | 0.3257    | 0.2645    |
