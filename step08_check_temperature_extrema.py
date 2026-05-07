import argparse
import os
import pandas as pd

from path_selection import PathSelectionError, choose_existing_directory, fail_with_path_error


DEFAULT_INPUT_FOLDER = r'C:\Project\GeoOptimize\FinalData'


def parse_args():
    parser = argparse.ArgumentParser(description="Report maximum temperatures from Tecplot-exported .dat files.")
    parser.add_argument("--input-dir", help="Directory containing Tecplot-exported .dat files.")
    parser.add_argument("--no-dialog", action="store_true", help="Disable GUI/text path prompts.")
    return parser.parse_args()


def main():
    args = parse_args()
    try:
        directory_path = choose_existing_directory(
            "Choose temperature .dat input directory",
            arg_value=args.input_dir,
            default=DEFAULT_INPUT_FOLDER,
            no_dialog=args.no_dialog,
        )
    except PathSelectionError as error:
        return fail_with_path_error(error)

    max_temperatures = []
    processed_files_count = 0

    for filename in os.listdir(directory_path):
        if filename.endswith('.dat'):
            file_path = os.path.join(directory_path, filename)
            try:
                data = pd.read_csv(file_path, sep='\s+', header=9, names=['X', 'Y', 'Temperature'])

                max_temperature = data['Temperature'].max()
                max_temperatures.append(max_temperature)
                processed_files_count += 1

                print(f"Processed file: {filename} | Processed file count: {processed_files_count}")
            except Exception as e:
                print(f"Error processing file {filename}: {e}")

    max_of_max_temperatures = max(max_temperatures) if max_temperatures else None

    if max_of_max_temperatures is not None:
        print(f"Maximum value among per-file maximum temperatures: {max_of_max_temperatures:.2f} K")
    else:
        print("No valid temperature data found.")

    print(f"Total processed files: {processed_files_count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
