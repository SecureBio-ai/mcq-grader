import argparse
from datetime import datetime
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

        # Check if input file exists and is a .tsv or .jsonl file
        if not os.path.isfile(row['input']) or (
                not row['input'].endswith('.tsv') and not row['input'].endswith('.jsonl')):
            raise FileNotFoundError(f"Input file {row['input']} does not exist or is not a .tsv or .jsonl file")

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
    for index, entry in tqdm(enumerate(exam_content)):
        entry['model'] = model
        entry['model_params'] = model_params

        # Get question-specific prompt
        try:
            prompt = format_prompt(task_description, entry['question'], entry['choices'])
            entry["prompt"] = prompt_path  # saving prompt path instead of prompt text to data footprint
        except Exception as e:
            entry["exception"] = e
            failed_responses.append(entry)
            print(
                f"An error occurred while preparing the prompt. Question {index}: {entry['question']} : \n{RED}{e}{RESET}\n Skipping...")
            continue

        # Get model reponse
        try:
            response = call_model(prompt, model, model_params, api_key)
        except Exception as e:
            entry["exception"] = e
            failed_responses.append(entry)
            print(
                f"An error occurred while calling the model. Question {index}: {entry['question']} : \n{RED}{e}{RESET}\n Skipping...")
            continue

        message = response.choices[0].message.content

        process_eleuther_style_output(message, entry, successful_responses, failed_responses)
        # process_openai_json_output(message, entry, successful_responses, failed_responses)

    return successful_responses, failed_responses


def score_exam(successful_responses, failed_responses, report_path):
    successful_q = len(successful_responses)
    failed_q = len(failed_responses)
    total_q = successful_q + failed_q

    correct = 0
    graded_questions = []
    report_content = []

    for question in successful_responses:
        if question['answer'] == question['model_answer']:
            correct += 1
            question['correct'] = 1
            graded_questions.append(question)
        else:
            question['correct'] = 0
            graded_questions.append(question)

    report_content.append("--------Scoring statistics--------\n")
    report_content.append(f"Total questions = {total_q}\n")
    report_content.append(
        f"Valid responses received on {successful_q}/{total_q} ({round(successful_q / total_q, 2)}) questions. Among the valid responses...\n")
    report_content.append(f"Accuracy = {correct}/{successful_q} ({round(correct / successful_q, 2)})\n")

    report_text = "".join(report_content)
    print(report_text)

    with open(report_path, 'w') as file:
        file.write(report_text)

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
        results_path = f"./results/{run['name']}_{datestring}"
        os.mkdir(results_path)

        if run['input'].endswith('.jsonl'):
            # todo check mmlu virology format
            jsonl_mode = True
            exam_jsonl = []
            with open(run['input'], 'r') as file:
                for index, line in enumerate(file):
                    entry = json.loads(line)
                    entry['question_index'] = index
                    exam_jsonl.append(entry)
            df = pd.DataFrame(exam_jsonl).set_index('question_index')

            # todo implement checks and text preprocessing
        else:
            jsonl_mode = False

            # Load tsv file to dataframe and validate exam format
            df, failed_checks = validate_exam(run['input'])
            if sum(len(indices) for indices in failed_checks.values()) != 0:
                with open(f"{results_path}/exam-warnings.txt", 'w') as file:
                    for check, items in failed_checks.items():
                        if items:
                            for index, question in items:
                                file.write(f"Warning for {check}: Row {index}, Question: {question}\n")

            # Preprocess exam text
            df_preprocessed = preprocess_exam_df(df)

            # Convert exam df to mmlu-style jsonl file
            exam_jsonl = convert_df_to_mmlu_jsonl(df_preprocessed, run['name'])
            exam_jsonl_path = os.path.join(results_path, Path(run['input']).stem + '.jsonl')
            with open(exam_jsonl_path, 'w') as file:
                for obj in exam_jsonl:
                    file.write(json.dumps(obj) + '\n')
            print(f"JSONL version of the exam successfully saved in to {exam_jsonl_path}")

        print("Getting model responses...")
        successful_responses, failed_responses = question_harness(exam_jsonl, run['prompt'], run['model'],
                                                                  run['model-params'])

        # Grade successful_responses
        report_path = f"{results_path}/score-report-{Path(run['input']).stem}.txt"
        graded_questions = score_exam(successful_responses, failed_responses, report_path)
        graded_questions_ordered = [order_dict_keys(question) for question in graded_questions]

        if failed_responses:
            failed_responses_ordered = [order_dict_keys(question) for question in failed_responses]
            print(f"WARNING: {len(failed_responses)} failed. Saving failed responses to results dir.\n")
            with open(f"{results_path}/failed-{Path(run['input']).stem}.jsonl", 'w') as file:
                for obj in failed_responses_ordered:
                    file.write(json.dumps(obj))
                    file.write('\n')

        graded_exam_path = f"{results_path}/graded-{Path(run['input']).stem}.jsonl"
        with open(graded_exam_path, 'w') as file:
            for obj in graded_questions_ordered:
                file.write(json.dumps(obj) + '\n')

        df_graded_exam = pd.DataFrame(graded_questions_ordered).set_index('question_index')

        df_combined_exam = merge_exam_dataframes(df, df_graded_exam, jsonl_mode)
        df_combined_exam.to_csv(f"{results_path}/graded-{Path(run['input']).stem}.csv")


if __name__ == "__main__":
    main()
