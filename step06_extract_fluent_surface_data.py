"""Export solved Fluent surface data for the current temperature-only dataset.

The paper describes temperature and pressure supervision, but the current
downstream pickle schema and training scripts expose only temperature labels.
Pressure export is therefore not added here until the Fluent field name,
surface convention, and dataset schema are confirmed.
"""

import argparse
import os
import ansys.fluent.core as pyfluent
from path_selection import PathSelectionError, choose_existing_directory, choose_output_directory, fail_with_path_error


DEFAULT_CASE_FOLDER = "E:\\topoOptimization\\DataResult"
DEFAULT_EXPORT_FOLDER = "E:\\topoOptimization\\TecplotFile"


def parse_args():
    parser = argparse.ArgumentParser(description="Export Fluent case-data surface temperature to Tecplot files.")
    parser.add_argument("--case-dir", help="Directory containing .cas.h5 files.")
    parser.add_argument("--export-dir", help="Directory for exported Tecplot files.")
    parser.add_argument("--no-dialog", action="store_true", help="Disable GUI/text path prompts.")
    return parser.parse_args()


def main():
    args = parse_args()
    try:
        folder_path = choose_existing_directory(
            "Choose Fluent .cas.h5 input directory",
            arg_value=args.case_dir,
            default=DEFAULT_CASE_FOLDER,
            no_dialog=args.no_dialog,
        )
        export_folder = choose_output_directory(
            "Choose Tecplot export output directory",
            arg_value=args.export_dir,
            default=DEFAULT_EXPORT_FOLDER,
            no_dialog=args.no_dialog,
        )
    except PathSelectionError as error:
        return fail_with_path_error(error)

    cas_files = [f for f in os.listdir(folder_path) if f.endswith('.cas.h5')]

    for cas_file in cas_files:

        file_path = os.path.join(folder_path, cas_file)


        solver = pyfluent.launch_fluent(precision="double", processor_count=32, ui_mode="gui", mode="solver")


        solver.file.read_case_data(file_name=file_path)


        export_file_name = os.path.join(export_folder, cas_file.replace('.cas.h5', ''))


        solver.file.export.tecplot(file_name=export_file_name, surfaces=["re"], cell_func_domain_export=["temperature"])


        solver.exit()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
