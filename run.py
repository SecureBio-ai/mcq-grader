import argparse
from datetime import datetime
import os
import pandas as pd
from models import load_api_links, check_model_exists
from data_utils import *
from prompt_utils import format_prompt
from pathlib import Path
import string
import json

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", help="Path to input samplesheet. See README for expected format.")
    return parser.parse_args()


def process_samplesheet(file_path):
    REQUIRED_COLUMNS = ['name', 'input', 'prompt', 'model', 'model-params']

    df = validate_input_csv(file_path, REQUIRED_COLUMNS)

    for _, row in df.iterrows():
        check_model_exists(row.model)
        parse_model_params(row)

        # todo build checks to see if prompt file and input file exist
        # todo check that input file is .tsv and prompt file is .json
        # todo check that 'task_description' exists in the prompt file

    return df


def question_harness(exam_content, prompt_path):


    with open(prompt_path, 'r') as file:
        data = json.load(file)
    task_description = data.get('task_description')

    for index, line in enumerate(exam_content.strip().split('\n')):
        entry = json.loads(line)

        try:
            question = entry.get('question')
            choices = entry.get('choices')
            prompt = format_prompt(task_description, choices)
            pass
            # response = call_model()
        except Exception as e:
            print(f"An error occurred with question {index}: {question} : \n{e}\n Skipping...")
            continue


    # 2) assemble prompt
    # 3) call model
    # 4) save answer
    pass


def main():
    args = parse_args()

    samplesheet = process_samplesheet(args.input)

    if not os.path.exists('./results'):
        os.makedirs('./results')

    for _, run in samplesheet.iterrows():
        datestring = datetime.now().strftime("%Y-%m-%d_%H:%M:%S")
        results_path = f"{run['name']}_{datestring}"
        os.mkdir(f"./results/{results_path}")

        df = check_exam(run['input'])
        df_preprocessed = preprocess_exam_df(df)

        # Convert df to mmlu-style jsonl file
        exam_jsonl = convert_df_to_mmlu_jsonl(df_preprocessed, Path(run['input']).stem)
        with open(Path(run['input']).with_suffix('.jsonl'), 'w') as file:
            file.write(exam_jsonl)

        question_harness(exam_jsonl, run['prompt'])

        # todo save all original model response to output dir


if __name__ == "__main__":
    main()
