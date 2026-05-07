import argparse
import os
from path_selection import PathSelectionError, choose_existing_directory, choose_existing_file, choose_output_directory, fail_with_path_error


DEFAULT_BATCH_FOLDER = r'E:\topoOptimization\TopoGeneBatch'
DEFAULT_SCRIPT_FOLDER = r'E:\topoOptimization\TopoPointPyFiles'
DEFAULT_SPACECLAIM_PATH = r'C:\Program Files\ANSYS Inc\v241\scdm\SpaceClaim.exe'


def parse_args():
    parser = argparse.ArgumentParser(description="Generate SpaceClaim batch files for generated scripts.")
    parser.add_argument("--script-dir", help="Directory containing generated SpaceClaim Python scripts.")
    parser.add_argument("--batch-output-dir", help="Directory for generated .bat files.")
    parser.add_argument("--spaceclaim-exe", help="Path to SpaceClaim.exe.")
    parser.add_argument("--no-dialog", action="store_true", help="Disable GUI/text path prompts.")
    return parser.parse_args()


def main():
    args = parse_args()
    try:
        geocomputegenerate_folder = choose_existing_directory(
            "Choose generated SpaceClaim script directory",
            arg_value=args.script_dir,
            default=DEFAULT_SCRIPT_FOLDER,
            no_dialog=args.no_dialog,
        )
        geocomputebatch_folder = choose_output_directory(
            "Choose geometry batch output directory",
            arg_value=args.batch_output_dir,
            default=DEFAULT_BATCH_FOLDER,
            no_dialog=args.no_dialog,
        )
        spaceclaim_path = choose_existing_file(
            "Choose SpaceClaim.exe",
            arg_value=args.spaceclaim_exe,
            default=DEFAULT_SPACECLAIM_PATH,
            no_dialog=args.no_dialog,
            filetypes=[("Executable", "*.exe"), ("All files", "*.*")],
        )
    except PathSelectionError as error:
        return fail_with_path_error(error)

    for filename in os.listdir(geocomputegenerate_folder):
        if filename.endswith('.py'):
            script_path = os.path.join(geocomputegenerate_folder, filename)

            bat_file_path = os.path.join(geocomputebatch_folder, filename.replace(".py", ".bat"))

            bat_file_content = f'"{spaceclaim_path}" /Headless=True /Splash=False /RunScript="{script_path}" /ExitAfterScript=True'

            with open(bat_file_path, 'w') as bat_file:
                bat_file.write(bat_file_content)

    print("Batch files created successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
