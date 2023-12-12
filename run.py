import argparse
from datetime import datetime
from model_utils import *
from data_utils import *
from prompt_utils import format_prompt
from pathlib import Path
import os
import json
from json.decoder import JSONDecodeError
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

    all_responses = []
    failed_responses = []
    # Loop through exam questions
    for index, line in tqdm(enumerate(exam_content.strip().split('\n'))):
        entry = json.loads(line)
        entry['question_index'] = index

        question = entry.get('question')
        choices = entry.get('choices')

        # Get question-specific prompt
        try:
            prompt = format_prompt(task_description, question, choices)
            entry["prompt"] = prompt
        except Exception as e:
            entry["exception"] = e
            failed_responses.append(json.dumps(entry))
            print(f"An error occurred while preparing the prompt. Question {index}: {question} : \n{RED}{e}{RESET}\n Skipping...")
            continue

        # Get model reponse
        try:
            response = call_model(prompt, model, model_params, api_key)
        except Exception as e:
            entry["exception"] = e
            failed_responses.append(json.dumps(entry))
            print(f"An error occurred while calling the model. Question {index}: {question} : \n{RED}{e}{RESET}\n Skipping...")
            continue

        response_content = response.choices[0].message.content

        # Try treating model output as JSON to separate entries like 'model_answer' and 'justification'.
        # Otherwise, save the entire response to the JSON object
        try:
            json_response_content = json.loads(response_content)
        except JSONDecodeError:
            response_key = "model_response"
            json_response_content = {response_key: response_content}
            print(f"Response content could not be parsed in JSON format. Saving all content to single JSON entry...")

        # append model response to entry JSON
        entry.update(json_response_content)
        print(json.dumps(entry))
        all_responses.append(json.dumps(entry))

    return all_responses, failed_responses


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
        exam_jsonl = convert_df_to_mmlu_jsonl(df_preprocessed, Path(run['input']).stem)
        with open(Path(run['input']).with_suffix('.jsonl'), 'w') as file:
            file.write(exam_jsonl)
        print(f"JSONL version of the exam successfully saved in to {Path(run['input']).with_suffix('.jsonl')}")

        print("Getting model responses...")
        responses, failed_responses = question_harness(exam_jsonl, run['prompt'], run['model'], run['model-params'])

        if failed_responses:
            print(f"WARNING: {len(failed_responses)} failed.\n")
            with open(f"./results/{results_path}/failed-{Path(run['input']).stem}.jsonl", 'w') as file:
                for obj in failed_responses:
                    file.write(obj + '\n')

        with open(f"./results/{results_path}/graded-{Path(run['input']).stem}.jsonl", 'w') as file:
            for obj in responses:
                file.write(obj + '\n')

        # todo get summary stats
        # todo save model answers to input tsv


if __name__ == "__main__":
    main()
