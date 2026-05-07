import argparse
import os

from path_selection import PathSelectionError, choose_existing_directory, choose_output_directory, choose_save_file, fail_with_path_error


DEFAULT_INPUT_FOLDER = r"C:\Project\GeoOptimize\TecplotFile"
DEFAULT_MACRO_FILE = r"C:\Project\GeoOptimize\auto_generated_script.mcr"
DEFAULT_DAT_OUTPUT_FOLDER = r"C:\Project\GeoOptimize\FinalData"


def tecplot_path(path):
    """Return a Windows path escaped for Tecplot macro strings."""
    return str(path).replace("\\", "\\\\")


def parse_args():
    parser = argparse.ArgumentParser(description="Generate Tecplot macro commands for rectangular temperature exports.")
    parser.add_argument("--input-dir", "--plt-dir", dest="input_dir", help="Directory containing .plt files.")
    parser.add_argument("--macro-out", help="Output .mcr macro file.")
    parser.add_argument("--dat-output-dir", help="Directory referenced by the macro for exported .dat files.")
    parser.add_argument("--no-dialog", action="store_true", help="Disable GUI/text path prompts.")
    return parser.parse_args()


def main():
    args = parse_args()
    try:
        folder_path = choose_existing_directory(
            "Choose Tecplot .plt input directory",
            arg_value=args.input_dir,
            default=DEFAULT_INPUT_FOLDER,
            no_dialog=args.no_dialog,
        )
        macro_file_path = choose_save_file(
            "Choose Tecplot macro output file",
            arg_value=args.macro_out,
            default=DEFAULT_MACRO_FILE,
            no_dialog=args.no_dialog,
            filetypes=[("Tecplot macro", "*.mcr"), ("All files", "*.*")],
            defaultextension=".mcr",
        )
        dat_output_folder = choose_output_directory(
            "Choose Tecplot .dat export directory",
            arg_value=args.dat_output_dir,
            default=DEFAULT_DAT_OUTPUT_FOLDER,
            no_dialog=args.no_dialog,
        )
    except PathSelectionError as error:
        return fail_with_path_error(error)

    output_script = "#!MC 1410"

    for file_name in os.listdir(folder_path):
        if file_name.endswith(".plt"):
            base_name = os.path.splitext(file_name)[0]
            input_file_path = folder_path / file_name
            dat_file_path = dat_output_folder / f"{base_name}.dat"

            new_script = f"""
$!ReadDataSet  '{tecplot_path(input_file_path)}'
  ReadDataOption = New
  ResetStyle = Yes
  VarLoadMode = ByName
  AssignStrandIDs = Yes
  VarNameList = '"CoordinateX" "CoordinateY" "CoordinateZ" "Temperature"'
$!CreateRectangularZone
  IMax = 251
  JMax = 1001
  KMax = 1
  X1 = 0
  Y1 = 0
  Z1 = 0
  X2 = 0.0500000007451
  Y2 = 0.20000000298
  Z2 = 0
  XVar = 1
  YVar = 2
$!Pick SetMouseMode
  MouseMode = Select
$!LinearInterpolate
  SourceZones =  [1]
  DestinationZone = 2
  VarList =  [4]
  LinearInterPConst = 0
  LinearInterpMode = DontChange
$!WriteDataSet  '{tecplot_path(dat_file_path)}'
  IncludeText = No
  IncludeGeom = No
  IncludeCustomLabels = No
  IncludeDataShareLinkage = Yes
  ZoneList =  [2]
  VarList =  [1-2,4]
  Binary = No
  UsePointFormat = Yes
  Precision = 9
  TecplotVersionToWrite = TecplotCurrent
"""


            output_script += new_script


    with open(macro_file_path, "w") as file:
        file.write(output_script)

    print(f"Tecplot macro generated: {macro_file_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
