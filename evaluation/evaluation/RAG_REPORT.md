# Casa Amigo — RAG Evaluation Report
_Generated: 2025-11-12 23:25_

## Retrieval
| Metric         | Value  |
| -------------- | ------ |
| Queries        | 30     |
| MRR@10         | 0.2253 |
| nDCG@10        | 0.2067 |
| Precision@10   | 0.0433 |
| Recall@10      | 0.2833 |
| Coverage@10    | 0.4333 |
| Top-1 Acc      | 0.1667 |
| Top-3 Acc      | 0.2333 |
| Top-5 Acc      | 0.3    |
| Top-10 Acc     | 0.4333 |
| Avg Rank (hit) | 3.4615 |

## Generation
| Metric               | Value  |
| -------------------- | ------ |
| Questions            | 20     |
| ROUGE-1 F            | 0.4702 |
| ROUGE-L F            | 0.398  |
| BLEU-1               | 0.4067 |
| BERTScore F1         | 0.9016 |
| Exact Match %        | 0.0    |
| Avg Answer Len (tok) | 30.85  |
| Len Ratio            | 0.7592 |

### Generation by Difficulty
| Difficulty | N | ROUGE-1 F | ROUGE-L F |
| ---------- | - | --------- | --------- |
| easy       | 7 | 0.5955    | 0.5284    |
| medium     | 9 | 0.4112    | 0.3449    |
| hard       | 4 | 0.3836    | 0.2897    |
