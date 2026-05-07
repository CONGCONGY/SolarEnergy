import argparse
import glob
import os
import re
from fluent_case_runner import fluentcompute
from path_selection import PathSelectionError, choose_existing_directory, choose_output_directory, fail_with_path_error


DEFAULT_PMDB_FOLDER = r'E:\topoOptimization\TopoFFGeom'
DEFAULT_CASE_OUTPUT_DIR = r'E:\topoOptimization\DataResult'


def parse_args():
    parser = argparse.ArgumentParser(description="Run Fluent for PMDB files in a directory.")
    parser.add_argument("--pmdb-dir", "--geometry-dir", dest="pmdb_dir", help="Directory containing .pmdb files.")
    parser.add_argument("--case-output-dir", help="Directory for Fluent .cas.h5 outputs.")
    parser.add_argument("--no-dialog", action="store_true", help="Disable GUI/text path prompts.")
    return parser.parse_args()


def main():
    args = parse_args()
    try:
        directory = choose_existing_directory(
            "Choose PMDB geometry input directory",
            arg_value=args.pmdb_dir,
            default=DEFAULT_PMDB_FOLDER,
            no_dialog=args.no_dialog,
        )
        case_output_dir = choose_output_directory(
            "Choose Fluent case-data output directory",
            arg_value=args.case_output_dir,
            default=DEFAULT_CASE_OUTPUT_DIR,
            no_dialog=args.no_dialog,
        )
    except PathSelectionError as error:
        return fail_with_path_error(error)

    pmdb_files = glob.glob(os.path.join(directory, '*.pmdb'))

    for pmdb_file in pmdb_files:

        print(pmdb_file)

        file_name = os.path.basename(pmdb_file)
        match = re.search(r'\d+', file_name)

        if match:
            pmdb_file_number = int(match.group())

            print(pmdb_file_number)

            fluentcompute(pmdb_file, pmdb_file_number, output_dir=str(case_output_dir))

            os.remove(pmdb_file)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
