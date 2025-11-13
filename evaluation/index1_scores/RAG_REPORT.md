# Casa Amigo — RAG Evaluation Report
_Generated: 2025-11-13 17:52_

## Retrieval
| Metric         | Value  |
| -------------- | ------ |
| Queries        | 30     |
| MRR@10         | 0.3667 |
| nDCG@10        | 0.2818 |
| Precision@10   | 0.04   |
| Recall@10      | 0.2667 |
| Coverage@10    | 0.4    |
| Top-1 Acc      | 0.3333 |
| Top-3 Acc      | 0.4    |
| Top-5 Acc      | 0.4    |
| Top-10 Acc     | 0.4    |
| Avg Rank (hit) | 1.1667 |

## Generation
| Metric               | Value  |
| -------------------- | ------ |
| Questions            | 20     |
| ROUGE-1 F            | 0.4806 |
| ROUGE-L F            | 0.4089 |
| BLEU-1               | 0.4122 |
| BERTScore F1         | 0.902  |
| Exact Match %        | 0.0    |
| Avg Answer Len (tok) | 31.0   |
| Len Ratio            | 0.7676 |

### Generation by Difficulty
| Difficulty | N | ROUGE-1 F | ROUGE-L F |
| ---------- | - | --------- | --------- |
| easy       | 7 | 0.6431    | 0.5776    |
| medium     | 9 | 0.3971    | 0.3258    |
| hard       | 4 | 0.3839    | 0.3005    |
