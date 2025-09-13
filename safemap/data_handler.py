import pandas as pd
import warnings

# Suppress warnings for cleaner output
warnings.filterwarnings('ignore')

def load_and_combine_data(file_path):
    """
    Loads data from multiple sheets of an Excel file and combines them.

    Args:
        file_path (str): The path to the Excel file.

    Returns:
        pandas.DataFrame: A single DataFrame with all city data combined,
                          or None if loading fails.
    """
    sheet_names_map = {
        'delhi_combined_data': 'Delhi',
        'mumbai_combined_data': 'Mumbai',
        'chennai_combined_data': 'Chennai',
        'bengaluru_combined_data': 'Bengaluru',
        'kochi_combined_data': 'Kochi'
    }

    all_dfs = []
    print(f"Attempting to load data from {file_path}...")

    try:
        xls = pd.read_excel(file_path, sheet_name=list(sheet_names_map.keys()))
        for sheet_name, city_name in sheet_names_map.items():
            if sheet_name in xls:
                df = xls[sheet_name]
                df['city'] = city_name
                all_dfs.append(df)

        if all_dfs:
            combined_df = pd.concat(all_dfs, ignore_index=True)
            print("All datasets combined successfully!")
            return combined_df
        else:
            print("\nNo data was loaded. Please check the Excel file and sheet names.")
            return None

    except FileNotFoundError:
        print(f"Error: File not found at '{file_path}'.")
        return None
    except Exception as e:
        print(f"An error occurred while reading the Excel file: {e}")
        return None