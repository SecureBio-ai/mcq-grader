import argparse
from datetime import datetime
import pandas as pd
from model_utils import *
from data_utils import *
from prompt_utils import format_prompt
from pathlib import Path
import os
import json
from tqdm import tqdm

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", help="Path to input samplesheet. See README for expected format.")
    return parser.parse_args()


def process_samplesheet(file_path):
    REQUIRED_COLUMNS = ['name', 'input', 'prompt', 'model', 'model-params']

    df = validate_input_csv(file_path, REQUIRED_COLUMNS)

    for index, row in df.iterrows():
        check_model_exists(row['model'])
        params_dict = parse_model_params(row['model-params'])

        # Update the DataFrame with the actual dictionary
        df.at[index, 'model-params'] = params_dict

        # Check if input file exists and is a .tsv file
        if not os.path.isfile(row['input']) or not row['input'].endswith('.tsv'):
            raise FileNotFoundError(f"Input file {row['input']} does not exist or is not a .tsv file")

        # Check if prompt file exists and is a .json file
        if not os.path.isfile(row['prompt']) or not row['prompt'].endswith('.json'):
            raise FileNotFoundError(f"Prompt file {row['prompt']} does not exist or is not a .json file")

        # Check that 'task_description' exists in the prompt file
        with open(row['prompt'], 'r') as file:
            prompt_data = json.load(file)
            if 'task_description' not in prompt_data:
                raise ValueError(f"task_description not found in {row['prompt']}")

    return df


def question_harness(exam_content, prompt_path, model, model_params):
    RED = '\033[91m'
    RESET = '\033[0m'

    with open(prompt_path, 'r') as file:
        data = json.load(file)
    task_description = data.get('task_description')

    api_key = load_api_link(model)

    successful_responses = []
    failed_responses = []
    # Loop through exam questions
    for index, line in tqdm(enumerate(exam_content.strip().split('\n'))):
        entry = json.loads(line)
        # entry['question_index'] = index

        question = entry.get('question')
        choices = entry.get('choices')

        # Get question-specific prompt
        try:
            prompt = format_prompt(task_description, question, choices)
            entry["prompt"] = prompt_path
        except Exception as e:
            entry["exception"] = e
            failed_responses.append(entry)
            print(f"An error occurred while preparing the prompt. Question {index}: {question} : \n{RED}{e}{RESET}\n Skipping...")
            continue

        # Get model reponse
        try:
            response = call_model(prompt, model, model_params, api_key)
        except Exception as e:
            entry["exception"] = e
            failed_responses.append(entry)
            print(f"An error occurred while calling the model. Question {index}: {question} : \n{RED}{e}{RESET}\n Skipping...")
            continue

        message = response.choices[0].message.content

        process_eleuther_style_output(message, entry, successful_responses, failed_responses)
        # process_openai_json_output(message, entry, successful_responses, failed_responses)

    return successful_responses, failed_responses


def score_exam(successful_responses, failed_responses):
    successful_q = len(successful_responses)
    failed_q = len(failed_responses)
    total_q = successful_q + failed_q

    correct = 0
    graded_questions = []
    for question in successful_responses:
        if question['answer'] == question['model_answer']:
            correct += 1
            question['correct'] = 1
            graded_questions.append(question)
        else:
            question['correct'] = 0
            graded_questions.append(question)

    print("\n--------Scoring statistics--------")
    print(f"Total questions = {total_q}")
    print(f"Valid responses recieved on {successful_q}/{total_q} ({round(successful_q/total_q, 2)}) questions. Among "
          f"the valid responses...")
    print(f"Accuracy = {correct}/{successful_q} ({round(correct/successful_q, 2)})")

    return graded_questions



def main():
    args = parse_args()

    samplesheet = process_samplesheet(args.input)

    if not os.path.exists('./results'):
        os.makedirs('./results')

    for index, run in samplesheet.iterrows():
        print(f"\nStarting run {run['name']}:")
        print(f"  Input File: {run['input']}")
        print(f"  Prompt File: {run['prompt']}")
        print(f"  Model: {run['model']}")
        print(f"  Model Params: {run['model-params']}\n")

        datestring = datetime.now().strftime("%Y-%m-%d_%H:%M:%S")
        results_path = f"{run['name']}_{datestring}"
        os.mkdir(f"./results/{results_path}")

        df, failed_checks = validate_exam(run['input'])
        if sum(len(indices) for indices in failed_checks.values()) != 0:
            with open(f"./results/{results_path}/exam-warnings.txt", 'w') as file:
                for check, items in failed_checks.items():
                    if items:
                        for index, question in items:
                            file.write(f"Warning for {check}: Row {index}, Question: {question}\n")

        df_preprocessed = preprocess_exam_df(df)

        # Convert df to mmlu-style jsonl file
        exam_jsonl = convert_df_to_mmlu_jsonl(df_preprocessed, run['name'])
        with open(Path(run['input']).with_suffix('.jsonl'), 'w') as file:
            file.write(exam_jsonl)
        print(f"JSONL version of the exam successfully saved in to {Path(run['input']).with_suffix('.jsonl')}")

        print("Getting model responses...")
        successful_responses, failed_responses = question_harness(exam_jsonl, run['prompt'], run['model'], run['model-params'])

        # Grade successful_responses
        graded_questions = score_exam(successful_responses, failed_responses)
        graded_questions_ordered = [order_dict_keys(question) for question in graded_questions]

        if failed_responses:
            failed_responses_ordered = [order_dict_keys(question) for question in failed_responses]
            print(f"WARNING: {len(failed_responses)} failed. Saving failed responses to results dir.\n")
            with open(f"./results/{results_path}/failed-{Path(run['input']).stem}.jsonl", 'w') as file:
                for obj in failed_responses_ordered:
                    file.write(json.dumps(obj) + '\n')

        graded_exam_path = f"./results/{results_path}/graded-{Path(run['input']).stem}.jsonl"
        with open(graded_exam_path, 'w') as file:
            for obj in graded_questions_ordered:
                file.write(json.dumps(obj) + '\n')

    df_graded_exam = pd.DataFrame(graded_questions_ordered).set_index('question_index')
    df_graded_exam.to_csv(f"./results/{results_path}/graded-{Path(run['input']).stem}-mmlu-format.csv")

    df_combined_exam = merge_exam_dataframes(df, df_graded_exam)
    df_combined_exam.to_csv(f"./results/{results_path}/graded-{Path(run['input']).stem}.csv")

if __name__ == "__main__":
    main()
