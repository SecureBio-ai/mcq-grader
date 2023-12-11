import pandas as pd
import json

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