"""Write per-file maximum and average temperature statistics.

This remains a temperature-only post-processing step. Pressure-drop metrics
should be added only after the pressure export and label schema are confirmed.
"""

import argparse
import os
import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed

from path_selection import PathSelectionError, choose_existing_directory, choose_save_file, fail_with_path_error


DEFAULT_INPUT_FOLDER = r'C:\Project\GeoOptimize\FinalData'
DEFAULT_OUTPUT_FILE = r'C:\Project\GeoOptimize\temperature_stats.txt'
directory_path = DEFAULT_INPUT_FOLDER

file_temperature_stats = {}
processed_files_count = 0


def process_file(filename):
    global processed_files_count
    file_path = os.path.join(directory_path, filename)
    try:
        data = pd.read_csv(file_path, sep='\s+', header=10, names=['X', 'Y', 'Temperature'])

        max_temperature = data['Temperature'].max()
        average_temperature = data['Temperature'].mean()

        processed_files_count += 1

        return filename, max_temperature, average_temperature
    except Exception as e:
        print(f"Error processing file {filename}: {e}")
        return filename, None, None


def parse_args():
    parser = argparse.ArgumentParser(description="Write maximum and average temperature statistics from .dat files.")
    parser.add_argument("--input-dir", help="Directory containing Tecplot-exported .dat files.")
    parser.add_argument("--output-file", help="Text file for temperature statistics.")
    parser.add_argument("--no-dialog", action="store_true", help="Disable GUI/text path prompts.")
    return parser.parse_args()


def main():
    global directory_path, file_temperature_stats, processed_files_count
    args = parse_args()
    try:
        directory_path = str(choose_existing_directory(
            "Choose temperature .dat input directory",
            arg_value=args.input_dir,
            default=DEFAULT_INPUT_FOLDER,
            no_dialog=args.no_dialog,
        ))
        output_file_path = choose_save_file(
            "Choose temperature statistics output file",
            arg_value=args.output_file,
            default=DEFAULT_OUTPUT_FILE,
            no_dialog=args.no_dialog,
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
            defaultextension=".txt",
        )
    except PathSelectionError as error:
        return fail_with_path_error(error)

    file_temperature_stats = {}
    processed_files_count = 0

    dat_files = [f for f in os.listdir(directory_path) if f.endswith('.dat')]

    with ThreadPoolExecutor() as executor:
        futures = {executor.submit(process_file, filename): filename for filename in dat_files}

        for future in as_completed(futures):
            filename, max_temperature, average_temperature = future.result()
            if max_temperature is not None and average_temperature is not None:
                file_temperature_stats[filename] = {
                    'Max Temperature': max_temperature,
                    'Average Temperature': average_temperature,
                }
                print(f"Processed file: {filename} | Processed file count: {processed_files_count}")

    if file_temperature_stats:
        with open(output_file_path, 'w') as f:
            f.write("File\tMax Temperature (K)\tAverage Temperature (K)\n")
            for file, stats in file_temperature_stats.items():
                f.write(f"{file}\t{stats['Max Temperature']:.2f}\t{stats['Average Temperature']:.2f}\n")
            print(f"Results saved to {output_file_path}")
    else:
        print("No valid temperature data found.")

    print(f"Total processed files: {processed_files_count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
