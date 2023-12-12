import pandas as pd
import json
import re
import ast


def validate_input_csv(file_path, REQUIRED_COLUMNS, delimiter=None):
    try:
        df = pd.read_csv(file_path, delimiter=delimiter)
    except FileNotFoundError:
        raise FileNotFoundError(f"The file {file_path} does not exist.")
    except pd.errors.EmptyDataError:
        raise ValueError(f"The file {file_path} is empty.")

    missing_columns = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    if missing_columns:
        raise ValueError(f"Missing required columns: {', '.join(missing_columns)}")
    return df


def parse_model_params(params):
    if pd.isna(params) or params.strip() == '':
        return {}
    try:
        params_dict = ast.literal_eval(params)
        if not isinstance(params_dict, dict):
            raise ValueError("Model params should be a dictionary.")
        return params_dict
    except:
        raise ValueError("Error parsing model params. Ensure it's a valid dictionary.")


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
    # todo check for blank questions and answers
    # todo check that answer exists among possible options

    return df


def convert_df_to_mmlu_jsonl(df, subject):
    choice_columns = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J']

    jsonl_entries = []
    for index, row in df.iterrows():
        question = row['question']
        answer_index = choice_columns.index(row['answer'])  # Convert answer to index

        # Collect choices that contain text and are present in the DataFrame
        choices = [row[col] for col in choice_columns if col in df.columns and pd.notna(row[col]) and row[col] != '']

        json_object = {
            "question": question,
            "subject": subject,
            "choices": choices,
            "answer": answer_index
        }
        jsonl_entries.append(json.dumps(json_object))

    jsonl_content = "\n".join(jsonl_entries)
    return jsonl_content


def preprocess_exam_df(df):
    columns_to_preprocess = ['question', 'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J']

    # Regular expression to match trailing whitespaces after a period
    trailing_whitespace_regex = re.compile(r'\.\s{2,}')

    # Function to replace curly quotes, excessive trailing whitespaces, and standardize True/False
    def preprocess_text(text):
        if pd.notna(text):
            text = text.replace('‘', "'").replace('’', "'").replace('“', '"').replace('”', '"')
            text = trailing_whitespace_regex.sub('. ', text)

            if text.lower() == 'true':
                text = 'True'
            elif text.lower() == 'false':
                text = 'False'

            text = text.strip()
        return text

    for col in columns_to_preprocess:
        if col in df.columns:
            df[col] = df[col].apply(preprocess_text)

    return df
