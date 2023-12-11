import argparse
from datetime import datetime
import os
import pandas as pd

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", help="Path to input samplesheet. See README for expected format.")
    return parser.parse_args()


def process_input_sheet(file_path):
    REQUIRED_COLUMNS = ['name', 'input', 'prompt', 'model', 'model-params']

    def validate_input_csv(file_path):
        try:
            df = pd.read_csv(file_path)
        except FileNotFoundError:
            raise FileNotFoundError(f"The file {file_path} does not exist.")
        except pd.errors.EmptyDataError:
            raise ValueError(f"The file {file_path} is empty.")

        missing_columns = [col for col in REQUIRED_COLUMNS if col not in df.columns]
        if missing_columns:
            raise ValueError(f"Missing required columns: {', '.join(missing_columns)}")
        return df

    def check_model(row):
        pass
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

    df = validate_input_csv(file_path)

    for _, row in df.iterrows():
        check_model(row)
        parse_model_params(row)

    # Checks not yet implemented
    return df

def main():
    args = parse_args()

    df = process_input_sheet(args.input)

    for index, run in df.iterrows():
        datestring = datetime.now().strftime("%Y-%m-%d_%H:%M:%S")
        results_path = f"{run.name}_{datestring}"
        os.mkdir(f"./results/{results_path}")

        # ...
