# Casa Amigo — RAG Evaluation Runner

This evaluation folder is meant to **generate predictions** with the retriever tool and then **score** them using the following metrics

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

## note
- all previous versions of evaluation_1, evaluation_2 etc reports are saved to track improvmeents