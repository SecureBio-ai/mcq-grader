import pandas as pd
import json
import re
import ast
import string


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
        'incorrect_column_order': [],
        'empty_A_or_B': [],
        'empty_question': [],
        'invalid_answer': []
    }

    choice_columns = [col for col in df.columns if col.isupper() and len(col) == 1]

    # Check 1: Column order
    # Check 1.1: Ensure 'question' is the first column
    if df.columns[0] != 'question':
        failed_checks['incorrect_column_order'].append("First column is not 'question'")

    # Check 1.2: Ensure 'answer' is after all choice columns
    answer_index = df.columns.get_loc('answer')
    for col in choice_columns:
        if df.columns.get_loc(col) > answer_index:
            failed_checks['incorrect_column_order'].append(f"Choice column {col} appears after 'answer'")

    # Check 1.3: Ensure there are no additional columns before 'answer'
    for col in df.columns[:answer_index]:
        if col not in choice_columns and col != 'question':
            failed_checks['incorrect_column_order'].append(
                f"Column {col} appears before 'answer'. Columns not among the required columns \
                ('question', choices ('A', 'B', etc.), and 'answer') should come after the 'answer' column.")

    for index, row in df.iterrows():
        # Check 2: Columns A and B should not be empty
        if pd.isna(row['A']) or pd.isna(row['B']):
            failed_checks['empty_A_or_B'].append((index, row['question']))

        # Check 3: 'question' rows should have text
        if pd.isna(row['question']) or row['question'].strip() == '':
            failed_checks['empty_question'].append((index, row['question']))

        # Check 4: 'answer' should match one of the answer column options
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

    jsonl_content = []
    for index, row in df.iterrows():
        answer_index = choice_columns.index(row['answer'])  # Convert answer to index

        # Collect choices that contain text and are present in the DataFrame
        choices = [row[col] for col in choice_columns if pd.notna(row[col]) and row[col] != '']

        json_object = {
            "question_index": index,
            "question": row['question'],
            "subject": subject,
            "choices": choices,
            "answer": answer_index
        }
        jsonl_content.append(json_object)

    return jsonl_content


def convert_mmlu_df_to_exam_df(df):

    return df

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
    ORDER = ['question_index', 'question', 'subject', 'choices', 'answer', 'model_answer', 'correct', 'model_response',
             'model', 'model_params', 'justification', 'prompt']

    return {key: entries[key] for key in ORDER if key in entries}


def merge_exam_dataframes(df_orig, df_exam, jsonl_mode):
    # Function to convert model_answer index to letter
    def index_to_letter(index):
        if 0 <= index < num_choices:
            return choice_cols[index]
        return None

    column_order = ['question']
    if jsonl_mode:
        num_choices = df_orig['choices'].apply(len).max()
        choice_cols = list(string.ascii_uppercase[:num_choices])

        choice_expansion = pd.DataFrame(df_orig['choices'].tolist(), columns=choice_cols, index=df_orig.index)
        df_orig = df_orig.join(choice_expansion)
        df_orig.drop(columns=['choices'], inplace=True)
        df_orig['answer'] = df_orig['answer'].apply(index_to_letter)
    else:
        choice_cols = [col for col in df_orig.columns if col.isupper() and len(col) == 1]
        num_choices = len(choice_cols)

    column_order.extend(choice_cols)
    column_order.extend(['answer', 'model_answer', 'correct', 'model_response', 'model', 'model_params', 'subject',
                         'justification', 'prompt'])

    # Append any additional columns from df_orig that are not in the specified column_order
    additional_columns = [col for col in df_orig.columns if col not in column_order]
    column_order.extend(additional_columns)

    combined_df = pd.merge(df_orig, df_exam, on='question_index', how='left', suffixes=('', '_drop'))
    combined_df.drop([col for col in combined_df if col.endswith('_drop')], axis=1, inplace=True)

    combined_df.drop('choices', axis=1, inplace=True)
    combined_df['model_answer'] = combined_df['model_answer'].apply(index_to_letter)
    combined_df = combined_df[column_order]
    return combined_df
