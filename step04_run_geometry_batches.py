import argparse
import os
import subprocess
import concurrent.futures
from path_selection import PathSelectionError, choose_existing_directory, fail_with_path_error


DEFAULT_BATCH_FOLDER = r"E:\topoOptimization\TopoGeneBatch"

def execute_bat_file(filepath):
    print(f"Executing {filepath}")
    subprocess.run([filepath], shell=True)

def parse_args():
    parser = argparse.ArgumentParser(description="Run generated SpaceClaim geometry batch files.")
    parser.add_argument("--batch-dir", help="Directory containing generated .bat files.")
    parser.add_argument("--max-workers", type=int, default=20, help="Parallel worker count.")
    parser.add_argument("--no-dialog", action="store_true", help="Disable GUI/text path prompts.")
    return parser.parse_args()


def main():
    args = parse_args()
    try:
        directory = choose_existing_directory(
            "Choose geometry batch directory",
            arg_value=args.batch_dir,
            default=DEFAULT_BATCH_FOLDER,
            no_dialog=args.no_dialog,
        )
    except PathSelectionError as error:
        return fail_with_path_error(error)

    with concurrent.futures.ProcessPoolExecutor(max_workers=args.max_workers) as executor:

        futures = []
        for filename in os.listdir(directory):

            if filename.endswith(".bat"):

                filepath = os.path.join(directory, filename)

                futures.append(executor.submit(execute_bat_file, filepath))


        concurrent.futures.wait(futures)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
