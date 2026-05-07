import argparse
import os
from path_selection import PathSelectionError, choose_existing_directory, choose_output_directory, fail_with_path_error


def convert_txt_to_py_with_groups(txt_file_path, py_folder, geom_folder, fluentgeom_folder, height_num):

    with open(txt_file_path, 'r') as txt_file:
        lines = txt_file.readlines()


    txt_filename = os.path.basename(txt_file_path)
    py_filename = txt_filename.replace(".txt", ".py")
    py_file_path = os.path.join(py_folder, py_filename)


    with open(py_file_path, 'w') as py_file:


        py_file.write("# Set Plane\n")
        py_file.write("sectionPlane = Plane.PlaneXY\n")
        py_file.write("result = ViewHelper.SetSketchPlane(sectionPlane, None)\n")
        py_file.write("# EndBlock\n\n")

        py_file.write("# Sktech Rec\n")
        py_file.write("point1 = Point2D.Create(MM(0),MM(0))\n")
        py_file.write("point2 = Point2D.Create(MM(50),MM(0))\n")
        py_file.write("point3 = Point2D.Create(MM(50),MM(200))\n")
        py_file.write("result = SketchRectangle.Create(point1, point2, point3)\n")
        py_file.write("# EndBlock\n\n")

        py_file.write("# Entity\n")
        py_file.write("mode = InteractionMode.Solid\n")
        py_file.write("result = ViewHelper.SetViewMode(mode, None)\n")
        py_file.write("# EndBlock\n\n")


        py_file.write("# move Z direction\n")
        py_file.write("selection = BodySelection.Create(GetRootPart().Bodies[0])\n")
        py_file.write("direction = Direction.DirZ\n")
        py_file.write("options = MoveOptions()\n")
        py_file.write("options.CreatePatterns = False\n")
        py_file.write("options.DetachFirst = False\n")
        py_file.write("options.MaintainOrientation = False\n")
        py_file.write("options.MaintainMirrorRelationships = True\n")
        py_file.write("options.MaintainConnectivity = True\n")
        py_file.write("options.MaintainOffsetRelationships = True\n")
        py_file.write("options.Copy = False\n")
        py_file.write("options.SnapAssociatedVertices = True\n")
        py_file.write("options.SubDProportionalRadius = MM(0)\n")
        py_file.write("result = Move.Translate(selection, direction, MM(10.0), options)\n")
        py_file.write("# EndBlock\n\n")

        py_file.write("# Python Script for Sketch Points\n\n")


        for group_start in range(0, len(lines), height_num + 1):
            group = lines[group_start:group_start + height_num + 1]


            for line in group:
                x, y, z = line.split()
                py_file.write("# Sketch Point\n")
                py_file.write(f"point = Point.Create(MM({x}), MM({y}), MM({z}))\n")
                py_file.write("result = SketchPoint.Create(point)\n")
                py_file.write("# EndBlock\n\n")


        total_curves = len(lines)
        for curve_start in range(0, total_curves, height_num + 1):
            curve_end = min(curve_start + height_num, total_curves - 1)


            py_file.write("# Curve\n")
            py_file.write("points = Selection.Create([\n")
            for curve_index in range(curve_start, curve_end + 1):
                if curve_index == curve_end:
                    py_file.write(f"\tGetRootPart().Curves[{curve_index}]\n")
                else:
                    py_file.write(f"\tGetRootPart().Curves[{curve_index}],\n")
            py_file.write("])\n")
            py_file.write("result = SketchNurbs.Create(points)\n")
            py_file.write("# EndBlock\n\n")


        py_file.write("# Melt1\n")
        py_file.write("selection = Selection.Create([\n")
        py_file.write("\tGetRootPart().Curves[451],\n")
        py_file.write("\tGetRootPart().Curves[452],\n")
        py_file.write("\tGetRootPart().Curves[453],\n")
        py_file.write("\tGetRootPart().Curves[454],\n")
        py_file.write("\tGetRootPart().Curves[455],\n")
        py_file.write("\tGetRootPart().Curves[456],\n")
        py_file.write("\tGetRootPart().Curves[457],\n")
        py_file.write("\tGetRootPart().Curves[458],\n")
        py_file.write("\tGetRootPart().Curves[459],\n")
        py_file.write("\tGetRootPart().Curves[460],\n")
        py_file.write("\tGetRootPart().Curves[461]\n")
        py_file.write("])\n")
        py_file.write("options = LoftOptions()\n")
        py_file.write("options.GeometryCommandOptions = GeometryCommandOptions()\n")
        py_file.write("options.GeometryCommandOptions.KeepMirror = True\n")
        py_file.write("options.GeometryCommandOptions.KeepLayoutSurfaces = True\n")
        py_file.write("options.GeometryCommandOptions.KeepCompositeFaceRelationships = True\n")
        py_file.write("options.GeometryCommandOptions.Select = True\n")
        py_file.write("options.PeriodicBlend = False\n")
        py_file.write("options.RotationalBlend = False\n")
        py_file.write("options.SheetMetalBlend = False\n")
        py_file.write("options.ClockIt = False\n")
        py_file.write("options.IsRuled = False\n")
        py_file.write("options.IsLocalGuide = False\n")
        py_file.write("options.IsMinimalTopology = False\n")
        py_file.write("options.ExtrudeType = ExtrudeType.Add\n")
        py_file.write("result = Loft.Create(selection, None, options)\n")
        py_file.write("# EndBlock\n\n")


        py_file.write("# Melt2\n")
        py_file.write("selection = FaceSelection.Create([\n")
        py_file.write("\tGetRootPart().Bodies[0].Faces[0],\n")
        py_file.write("\tGetRootPart().Bodies[1].Faces[0]\n")
        py_file.write("])\n")
        py_file.write("options = LoftOptions()\n")
        py_file.write("options.GeometryCommandOptions = GeometryCommandOptions()\n")
        py_file.write("options.GeometryCommandOptions.KeepMirror = True\n")
        py_file.write("options.GeometryCommandOptions.KeepLayoutSurfaces = True\n")
        py_file.write("options.GeometryCommandOptions.KeepCompositeFaceRelationships = True\n")
        py_file.write("options.GeometryCommandOptions.Select = True\n")
        py_file.write("options.PeriodicBlend = False\n")
        py_file.write("options.RotationalBlend = False\n")
        py_file.write("options.SheetMetalBlend = False\n")
        py_file.write("options.ClockIt = False\n")
        py_file.write("options.IsRuled = False\n")
        py_file.write("options.IsLocalGuide = False\n")
        py_file.write("options.IsMinimalTopology = False\n")
        py_file.write("options.ExtrudeType = ExtrudeType.Add\n")
        py_file.write("result = Loft.Create(selection, None, options)\n")
        py_file.write("# EndBlock\n\n")


        py_file.write("# Entity\n")
        py_file.write("mode = InteractionMode.Solid\n")
        py_file.write("result = ViewHelper.SetViewMode(mode, None)\n")
        py_file.write("# EndBlock\n\n")


        py_file.write("# Create Named Selection Group\n")
        py_file.write("primarySelection = FaceSelection.Create(GetRootPart().Bodies[0].Faces[3])\n")
        py_file.write("secondarySelection = Selection.Empty()\n")
        py_file.write('result = NamedSelection.Create(primarySelection, secondarySelection, "Group1")\n')
        py_file.write("# EndBlock\n\n")

        py_file.write("# Rename Named Selection\n")
        py_file.write('result = NamedSelection.Rename("Group1", "inlet")\n')
        py_file.write("# EndBlock\n\n")

        py_file.write("# Create Named Selection Group\n")
        py_file.write("primarySelection = FaceSelection.Create(GetRootPart().Bodies[0].Faces[0])\n")
        py_file.write("secondarySelection = Selection.Empty()\n")
        py_file.write('result = NamedSelection.Create(primarySelection, secondarySelection, "Group1")\n')
        py_file.write("# EndBlock\n\n")

        py_file.write("# Rename Named Selection\n")
        py_file.write('result = NamedSelection.Rename("Group1", "re")\n')
        py_file.write("# EndBlock\n\n")

        py_file.write("# Create Named Selection Group\n")
        py_file.write("primarySelection = FaceSelection.Create(GetRootPart().Bodies[0].Faces[5])\n")
        py_file.write("secondarySelection = Selection.Empty()\n")
        py_file.write('result = NamedSelection.Create(primarySelection, secondarySelection, "Group1")\n')
        py_file.write("# EndBlock\n\n")

        py_file.write("# Rename Named Selection\n")
        py_file.write('result = NamedSelection.Rename("Group1", "outlet")\n')
        py_file.write("# EndBlock\n\n")

        py_file.write("# Create Named Selection Group\n")
        py_file.write("primarySelection = FaceSelection.Create(GetRootPart().Bodies[0].Faces[2])\n")
        py_file.write("secondarySelection = Selection.Empty()\n")
        py_file.write('result = NamedSelection.Create(primarySelection, secondarySelection, "Group1")\n')
        py_file.write("# EndBlock\n\n")

        py_file.write("# Rename Named Selection\n")
        py_file.write('result = NamedSelection.Rename("Group1", "symmetry")\n')
        py_file.write("# EndBlock\n\n")


        py_file.write("# Delete\n")
        py_file.write("selection = Selection.Create([\n")
        for i in range(462):
            if i == 461:
                py_file.write(f"\tGetRootPart().Curves[{i}]\n")
            else:
                py_file.write(f"\tGetRootPart().Curves[{i}],\n")
        py_file.write("])\n")
        py_file.write("result = Delete.Execute(selection)\n")
        py_file.write("# EndBlock\n\n")


        scdoc_file_path = os.path.join(geom_folder, txt_filename.replace(".txt", ".scdoc"))
        py_file.write("# Save File\n")
        py_file.write("options = ExportOptions.Create()\n")
        py_file.write(f'DocumentSave.Execute(r"{scdoc_file_path}", options)\n')
        py_file.write("# EndBlock\n\n")


        pmdb_file_path = os.path.join(fluentgeom_folder, txt_filename.replace(".txt", ".pmdb"))
        py_file.write("# Save File\n")
        py_file.write(f'Workbench.Fluent.ExportPMDB(r"{pmdb_file_path}")\n')
        py_file.write("# EndBlock\n\n")

    print(f"Generated: {py_file_path}")


def process_all_txt_files_in_folder(txt_folder, py_folder, geom_folder, fluentgeom_folder, height_num):

    for txt_filename in os.listdir(txt_folder):
        if txt_filename.endswith(".txt"):

            txt_file_path = os.path.join(txt_folder, txt_filename)

            convert_txt_to_py_with_groups(txt_file_path, py_folder, geom_folder, fluentgeom_folder, height_num)


DEFAULT_TXT_FOLDER = r"E:\topoOptimization\TopoPointData"
DEFAULT_PY_FOLDER = r"E:\topoOptimization\TopoPointPyFiles"
DEFAULT_GEOM_FOLDER = r"E:\topoOptimization\TopoFGeom"
DEFAULT_FLUENT_GEOM_FOLDER = r"E:\topoOptimization\TopoFFGeom"


def parse_args():
    parser = argparse.ArgumentParser(description="Generate SpaceClaim scripts from topology TXT files.")
    parser.add_argument("--input-dir", help="Directory containing topology TXT files.")
    parser.add_argument("--script-output-dir", help="Directory for generated SpaceClaim Python scripts.")
    parser.add_argument("--geometry-output-dir", help="Directory used by generated scripts for .scdoc files.")
    parser.add_argument("--pmdb-output-dir", help="Directory used by generated scripts for Fluent .pmdb files.")
    parser.add_argument("--no-dialog", action="store_true", help="Disable GUI/text path prompts.")
    return parser.parse_args()


height_num = 40


def main():
    args = parse_args()
    try:
        txt_folder = choose_existing_directory(
            "Choose topology TXT input directory",
            arg_value=args.input_dir,
            default=DEFAULT_TXT_FOLDER,
            no_dialog=args.no_dialog,
        )
        py_folder = choose_output_directory(
            "Choose generated SpaceClaim script output directory",
            arg_value=args.script_output_dir,
            default=DEFAULT_PY_FOLDER,
            no_dialog=args.no_dialog,
        )
        geom_folder = choose_output_directory(
            "Choose generated SCDOC output directory",
            arg_value=args.geometry_output_dir,
            default=DEFAULT_GEOM_FOLDER,
            no_dialog=args.no_dialog,
        )
        fluentgeom_folder = choose_output_directory(
            "Choose generated PMDB output directory",
            arg_value=args.pmdb_output_dir,
            default=DEFAULT_FLUENT_GEOM_FOLDER,
            no_dialog=args.no_dialog,
        )
    except PathSelectionError as error:
        return fail_with_path_error(error)

    process_all_txt_files_in_folder(
        str(txt_folder),
        str(py_folder),
        str(geom_folder),
        str(fluentgeom_folder),
        height_num,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
