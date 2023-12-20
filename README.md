# mcq-grader
Grade the performance of LLMs on multiple choice exams. Currently only OpenAI models are supported.

## Setup
1. To install dependencies run `pip install requirements.txt`. I'm running Python 3.9.18.  
2. Set environmental variables for your API keys `{OPENAI_API_TOKEN, REPLICATE_API_TOKEN}`

## Running mcq-grader
To grade exam/s run 
```
./run.py --input samplesheet.csv
``` 
The samplesheet is a csv file that specifies one or multiple "runs." Each run should have a unique name and can specify
different exams (as .tsv or .jsonl files), prompts, models, and model-params.  
  
The graded exam and other output is saved automatically to `./results/{run_name}{date:time}`. 

## Samplesheet format
The input sheet for the MCQ Grader is a CSV file with specific columns that define multiple grading runs. Each row in 
the input sheet represents a separate grading task. The required format for the input CSV is as follows:
* `name`: a unique identifier for the run.
* `input`: path to a .tsv or .jsonl input file containing the MCQs to be graded (see "Exam format").
* `prompt`: path to the JSON file containing the grading prompt (see "Prompts"). 
* `model`: identifier for the model to be used, e.g., 'gpt-4'. A full list of model names is in `model_utils.py` although some may not be supported yet.
* `model-params`: optional. A dictionary of model parameters to customize the grading behavior. Leave blank to use default settings.

An example input sheet

| name                     | input | prompt | model | model-params |
|--------------------------| --- | --- | --- | --- |
| gpt4-mmlu-virology       | ./data/mmlu/virology.tsv | ./grading-prompts/mmlu-gpt.json | gpt-4 | {temperature: 0.9} |
| llama2-70b-mmlu-virology | ./data/mmlu/virology.tsv | ./grading-prompts/mmlu-llama.json | llama2_70b | |

## Exam format
The exam can be a MMLU-style .jsonl file or a .tsv file.  
  
If using a .jsonl file the format should look like:
```angular2html
{"question":"How many human polyomaviruses are known at present?","subject":"virology","choices":["100","1","10","unknown"],"answer":0}
...
{"question":"Globally, the most deaths are caused by:","subject":"virology","choices":["Respiratory infections","Diarrheal diseases","Malaria","Tuberculosis"],"answer":1}
```

If using a .tsv file, it should have at least four columns: `{question, A, B, answer}`, although the exam can have A-Z 
option columns. If your exam has different kinds of multiple-choice questions (e.g., True/False, a question with six options) 
simply leave the option columns you don't need blank.    

You may include other columns (with different names) after the question, choices, and answer columns – these 
will be ignored by mcq-grader.

Mcq-grader will parse the your .tsv file to check for logical inconsistencies like "Correct answer given as C but only options A 
and B have text in them." This parsing is not yet implemented for .jsonl files.

An example exam

| question                                                                                 | A                   | B            | C                            | D                                                          | E             | answer | optional columns... |
|------------------------------------------------------------------------------------------|---------------------|--------------|------------------------------|------------------------------------------------------------|---------------|--------|---------------------|
| Which of the following is the most special characteristic of the adaptive immune system? | Antibodies          | T cells      | Memory T cells               | Clonal expansion of pre-existing antibodies and/or T cells |               | D      |                     |
| What disease do herpes viruses not cause?                                                | Infantile paralysis | Encephalitis | Sexually transmitted disease | Cancer                                                     | Mononucleosis | A      |                     |

