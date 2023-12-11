import argparse
from datetime import datetime
import os
import pandas as pd
from models import load_api_links, check_model_exists
from utils import validate_input_csv, convert_df_to_mmlu_jsonl
from pathlib import Path
import json

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", help="Path to input samplesheet. See README for expected format.")
    return parser.parse_args()


def process_samplesheet(file_path):
    REQUIRED_COLUMNS = ['name', 'input', 'prompt', 'model', 'model-params']

    def parse_model_params(row):
        params = row['model-params']
        if pd.isna(params) or params.strip() == '':
            return {}
        try:
            params_dict = eval(params)
            if not isinstance(params_dict, dict):
                raise ValueError("Model params should be a dictionary.")
            return params_dict
        except:
            raise ValueError("Error parsing model params. Ensure it's a valid dictionary.")

    df = validate_input_csv(file_path, REQUIRED_COLUMNS)

    for _, row in df.iterrows():
        check_model_exists(row.model)
        parse_model_params(row)

        # todo build checks to see if prompt file and input file exist
        # todo check that input file is .tsv and prompt file is .json

    return df


def check_exam(input):
    REQUIRED_COLUMNS = ['type', 'question']
    ALL_OPTIONS = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J']

    df = validate_input_csv(input, REQUIRED_COLUMNS, delimiter='\t')

    # Check whether all question types are supported
    with open('question-types.txt', 'r') as file:
        supported_q_types = {line.strip() for line in file}

    unsupported_types = df[~df['type'].isin(supported_q_types)]['type'].unique()
    if len(unsupported_types) > 0:
        print(f"WARNING: Unsupported question types found: {unsupported_types}")

    # Check for missing option columns
    max_mcq_option = max(int(q_type.split('-')[1]) for q_type in df['type'].unique() if 'MCQ' in q_type)
    expected_options = ALL_OPTIONS[:max_mcq_option]
    missing_columns = [opt for opt in expected_options if opt not in df.columns]
    if missing_columns:
        print(f"WARNING: Missing option columns {missing_columns} for the highest MCQ option MCQ-{max_mcq_option}")

    # todo check that TF questions use answer option A or B not TRUE or FALSE

    return df


def question_harness(exam):
    # For each question
    # 1) preprocess text and check question
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

        # Convert df to mmlu-style jsonl file
        exam_jsonl = convert_df_to_mmlu_jsonl(df, Path(run['input']).stem)
        with open(Path(run['input']).with_suffix('.jsonl'), 'w') as file:
            file.write(exam_jsonl)

        question_harness(exam_jsonl)


if __name__ == "__main__":
    main()
