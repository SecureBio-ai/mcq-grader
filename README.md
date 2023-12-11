`# mcq-grader
Evaluating LLMs on multiple-choice questions

## Input Sheet Format for MCQ Grader
The input sheet for the MCQ Grader is a CSV file with specific columns that define multiple grading runs. Each row in 
the input sheet represents a separate grading task. The required format for the input CSV is as follows:
* `name`: a unique identifier for the run.
* `input`: path to the input file containing the MCQs to be graded.
* `prompt`: path to the JSON file containing the grading prompts.
* `model`: identifier for the model to be used, e.g., 'gpt-4'.
* `model-params`: optional. A dictionary of model parameters to customize the grading behavior. Leave blank to use default settings.

An example input sheet

| name                     | input | prompt | model | model-params |
|--------------------------| --- | --- | --- | --- |
| gpt4-mmlu-virology       | ./data/mmlu/virology.tsv | ./grading-prompts/mmlu-gpt.json | gpt-4 | {temperature: 0.9} |
| llama2-70b-mmlu-virology | ./data/mmlu/virology.tsv | ./grading-prompts/mmlu-llama.json | llama2_70b | |