import pandas as pd
import json
import re
import ast


def validate_input_csv(file_path, REQUIRED_COLUMNS, delimiter=None):
    try:
        df = pd.read_csv(file_path, delimiter=delimiter)
        df.index.name = 'question_index'
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


def validate_exam(input):
    REQUIRED_COLUMNS = ['question', 'A', 'B', 'answer']

    df = validate_input_csv(input, REQUIRED_COLUMNS, delimiter='\t')

    failed_checks = {
        'empty_A_or_B': [],
        'empty_question': [],
        'invalid_answer': []
    }

    choice_columns = [col for col in df.columns if col.isupper() and len(col) == 1]

    for index, row in df.iterrows():
        # Check 1: Columns A and B should not be empty
        if pd.isna(row['A']) or pd.isna(row['B']):
            failed_checks['empty_A_or_B'].append((index, row['question']))

        # Check 2: 'question' rows should have text
        if pd.isna(row['question']) or row['question'].strip() == '':
            failed_checks['empty_question'].append((index, row['question']))

        # Check 3: 'answer' should match one of the answer column options
        answer = row['answer']
        if answer not in choice_columns or pd.isna(row.get(answer, None)):
            failed_checks['invalid_answer'].append((index, row['question']))

        # Print summary of warnings
    total_warnings = sum(len(indices) for indices in failed_checks.values())
    print(f"Exam validation complete with {total_warnings} warnings")

    # Print just the indices for warnings
    for check, items in failed_checks.items():
        if items:
            indices = [index for index, _ in items]
            print(f"Warning for {check}: Row indices {indices} failed this check.")

    return df, failed_checks


def convert_df_to_mmlu_jsonl(df, subject):
    choice_columns = [col for col in df.columns if col.isupper() and len(col) == 1]

    jsonl_entries = []
    for index, row in df.iterrows():
        question = row['question']
        answer_index = choice_columns.index(row['answer'])  # Convert answer to index

        # Collect choices that contain text and are present in the DataFrame
        choices = [row[col] for col in choice_columns if pd.notna(row[col]) and row[col] != '']

        json_object = {
            "question_index": index,
            "question": question,
            "subject": subject,
            "choices": choices,
            "answer": answer_index
        }
        jsonl_entries.append(json.dumps(json_object))

    jsonl_content = "\n".join(jsonl_entries)
    return jsonl_content


def preprocess_exam_df(df):
    columns_to_preprocess = ['question'] + [col for col in df.columns if col.isupper() and len(col) == 1]

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


def order_dict_keys(entries):
    ORDER = ['question_index', 'question', 'subject', 'choices', 'answer', 'model_answer', 'correct',
                        'justification', 'prompt', 'model_response']

    return {key: entries[key] for key in ORDER if key in entries}


def merge_exam_dataframes(df_orig, df_exam):
    choice_columns = [col for col in df_orig.columns if col.isupper() and len(col) == 1]
    column_order = ['question']
    column_order.extend(choice_columns)
    column_order.extend(['answer', 'model_answer', 'correct', 'subject', 'justification', 'prompt', 'model_response'])

    combined_df = pd.merge(df_orig, df_exam, on='question_index', how='left', suffixes=('', '_drop'))
    combined_df.drop([col for col in combined_df if col.endswith('_drop')], axis=1, inplace=True)
    combined_df.drop('choices', axis=1, inplace=True)

    # Function to convert model_answer index to letter
    def index_to_letter(index):
        if 0 <= index < len(choice_columns):
            return choice_columns[index]
        return None

    combined_df['model_answer'] = combined_df['model_answer'].apply(index_to_letter)

    combined_df = combined_df[column_order]

    return combined_df
