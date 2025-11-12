# Casa Amigo — RAG Evaluation Report
_Generated: 2025-11-12 22:50_

## Retrieval
| Metric         | Value  |
| -------------- | ------ |
| Queries        | 30     |
| MRR@10         | 0.2206 |
| nDCG@10        | 0.1999 |
| Precision@10   | 0.04   |
| Recall@10      | 0.2667 |
| Coverage@10    | 0.4    |
| Top-1 Acc      | 0.1667 |
| Top-3 Acc      | 0.2333 |
| Top-5 Acc      | 0.3    |
| Top-10 Acc     | 0.4    |
| Avg Rank (hit) | 3.1667 |

## Generation
| Metric               | Value  |
| -------------------- | ------ |
| Questions            | 20     |
| ROUGE-1 F            | 0.4843 |
| ROUGE-L F            | 0.4186 |
| BLEU-1               | 0.4208 |
| BERTScore F1         | 0.9031 |
| Exact Match %        | 0.0    |
| Avg Answer Len (tok) | 32.1   |
| Len Ratio            | 0.7818 |

### Generation by Difficulty
| Difficulty | N | ROUGE-1 F | ROUGE-L F |
| ---------- | - | --------- | --------- |
| easy       | 7 | 0.6262    | 0.5838    |
| medium     | 9 | 0.4183    | 0.3444    |
| hard       | 4 | 0.3847    | 0.2963    |
