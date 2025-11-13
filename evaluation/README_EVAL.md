# Casa Amigo — RAG Evaluation - Contents

This evaluation folder is used to generate the retrieval & generation metrics of Casa Amigo's RAG tool.  
Below you can find
1. baseline VS final version of Retrieval Metrics
2. baseline VS final version of Generation Metrics
3. What changes we made to baseline to get the final version of our RAG system
4. How to run the evaluation files if you would like to reproduce the scores for latest version of RAG system



## 1. Retrieval Metrics

| Metric                  | Baseline Value  |  Final Value After Enhancements |
| ----------------------- | --------------- | ------------------------------- |
| Queries                 | 30              | 30                              |
| MRR@10                  | 0.3667          | 0.6667                          |
| nDCG@10                 | 0.2818          | 0.6034                          |
| Precision@10            | 0.04            | 0.1033                          |
| Recall@10               | 0.2667          | 0.7111                          |
| Coverage@10             | 0.4             | 0.9                             |
| Top-1 Acc               | 0.3333          | 0.4333                          |
| Top-3 Acc               | 0.4             | 0.9                             |
| Top-5 Acc               | 0.4             | 0.9                             |
| Top-10 Acc              | 0.4             | 0.9                             |
| Avg Rank (hit)          | 1.1667          | 1.6296

## 2. Generation Metrics

| Metric               | Baseline Value  | Final Value After Enhancements |
| -------------------- | --------------- | ------------------------------ |
| Questions            | 20              | 20                             |
| ROUGE-1 F            | 0.4806          | 0.3616                         |
| ROUGE-L F            | 0.4089          | 0.2914                         |
| BLEU-1               | 0.4122          | 0.2896                         |
| BERTScore F1         | 0.902           | 0.8812                         |
| Avg Answer Len (tok) | 31.0            | 26.7                           |
| Len Ratio            | 0.7676          | 0.6176                         |


# What changes did we make to obtain final version from baseline RAG?
- Baseline RAG system had:
    - Default llamaindex chunking (~800 tokens per chunk)
    - Default ranking after retrieval (cosine similarity of embeddings)
    - Created index with this embedding model: `text-embedding-3-small`
- Final RAG system has:
    - Clause aware chunking (chunks are clause aware i.e each clause as a seperate node with each label/title as metadata)
    - Reranking after retrieval using sentence-transformers, specifically `mixedbread-ai/mxbai-rerank-large-v1` performed better than `cross-encoder/ms-marco-MiniLM-L-12-v2` and `cross-encoder/ms-marco-MiniLM-L-6-v2`
    - Adding reranking depth parameter of 15 (this number chosen after comparing 10,15,20,25)
    - Created index with larger embedding model: `text-embedding-3-large`

# HOW TO RUN:

## step 1: Generate the RAG output

generate the 'retriever' results and the LLM 'generated answers'

`python run_predictions.py --persist_dir ../pdf_index --top_k 10 \1--retrieval_gold retrieval_data.json  --rouge_gold rouge_data.json \  --retrieval_out retrieval_results.json \ --gen_out gen_outputs.json` `

## step 2: - Cross check it against gold standard
`python retrieval_eval.py > retrieval_scores.json`  
`python generation_eval.py > generation_scores.json`

## step 3: Generate report with scores
`python make_report.py --retrieval_scores retrieval_scores.json --generation_scores generation_scores.json`

## View final report 
now you can open the latest report at evaluation/RAG_REPORT.md

# Understanding the evaluation codebase:

### GOLD STANDARD DATA, aka test-set
- **retrieval_data.json**: to test the retriever
- **rouge_data.json**: to test the LLM generated answers

### files to generate our latest output
- **run_predictions.py**: runs the retriever & LLM and stores the respective 'clauses' and 'answers' to gen_outputs.jsonn
- **gen_outputs.json**: ^ stores results from above python script

## files to evaluate & score
- **retrieval_eval.py**: evaluates the 'retrieved clauses' in gen_outputs.py against the gold standard 'retrieval_data.json'
- '**retrieval_scores.json'** ^ stores scores from above python file
- **generation_eval.py**: evaluates the 'generated answers' in gen_outputs.py against the gold standard 'rouge_data.json'
- **'generation_scores.json'** ^ stores the scores from above python file

## create a final report
- **make_report.py**:** uses the retrieval and generation scores above and condenses it to 1 clear file
- **evalatuion/RAG_REPORT.md**: is the final report


