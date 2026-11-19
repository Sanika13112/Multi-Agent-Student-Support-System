
"""
Kaggle Dataset Inspection

Purpose:
Inspect the CSV and Excel versions of the downloaded
Bitext dataset before selecting data for our project.
"""

import pandas as pd
from pathlib import Path

# Define the location of our downloaded Kaggle dataset.
DATA_FOLDER = Path(
    "data/archive (6)/Bitext_Sample_Customer_Service_Training_Dataset/Training"
)

# Define the CSV and Excel file paths.
CSV_PATH = DATA_FOLDER / "Bitext_Sample_Customer_Service_Training_Dataset.csv"
EXCEL_PATH = DATA_FOLDER / "Bitext_Sample_Customer_Service_Training_Dataset.xlsx"


def inspect_dataset(file_path):
    """Read and inspect a dataset file."""

    print("\n" + "=" * 60)
    print("FILE:", file_path.name)
    print("=" * 60)

    # Read the file according to its extension.
    if file_path.suffix == ".csv":
        df = pd.read_csv(file_path)
    else:
        df = pd.read_excel(file_path)

    # Display the dataset dimensions.
    print("\nDataset shape (rows, columns):")
    print(df.shape)

    # Display all column names.
    print("\nColumn names:")
    print(df.columns.tolist())

    # Display the first five records.
    print("\nFirst five records:")
    print(df.head().to_string(index=False))

    # Display missing values in each column.
    print("\nMissing values:")
    print(df.isnull().sum())

    # Display duplicate record count.
    print("\nDuplicate records:")
    print(df.duplicated().sum())

    # Display unique values in likely label columns.
    for column in ["intent", "category"]:
        if column in df.columns:
            print(f"\nUnique values in {column}:")
            print(df[column].nunique())

            print(f"\nExamples per {column}:")
            print(df[column].value_counts().to_string())

    return df


if __name__ == "__main__":

    # Check whether both files exist.
    if not CSV_PATH.exists():
        print("CSV file not found:", CSV_PATH)
    else:
        csv_data = inspect_dataset(CSV_PATH)

    if not EXCEL_PATH.exists():
        print("Excel file not found:", EXCEL_PATH)
    else:
        excel_data = inspect_dataset(EXCEL_PATH)

    # Compare both versions if they are available.
    if CSV_PATH.exists() and EXCEL_PATH.exists():
        print("\n" + "=" * 60)
        print("CSV AND EXCEL COMPARISON")
        print("=" * 60)

        print("Same shape:", csv_data.shape == excel_data.shape)
        print(
            "Same column names:",
            csv_data.columns.tolist() == excel_data.columns.tolist()
        )
