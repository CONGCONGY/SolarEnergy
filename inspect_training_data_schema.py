"""Inspect prepared DeepONet pickle data without modifying it.

Usage examples:
    python inspect_training_data_schema.py E:\\ZhaoYang\\Train\\final_files19327\\train
    python inspect_training_data_schema.py path\\to\\sample.pkl --max-files 1

The script is intentionally read-only and has no ANSYS, Fluent, SpaceClaim, or
Tecplot dependency.
"""

import argparse
import json
import pickle
from pathlib import Path
from typing import Any

from path_selection import PathSelectionError, choose_existing_directory, choose_existing_file, fail_with_path_error


TEMPERATURE_KEYS = {"temperature", "temp", "t"}
PRESSURE_KEYS = {"pressure", "p", "pressure_drop", "delta_p", "dp"}
COORDINATE_KEYS = {"x", "y", "z"}
BRANCH_KEYS = {"heights", "branch", "topology"}
TRUNK_KEYS = {"coordinates", "coordinate", "coords", "trunk", "xyz"}
TARGET_KEYS = {"targets", "target", "outputs", "output", "y"}
SCHEMA_LEGACY = "legacy-temperature-only"
SCHEMA_PAPER = "paper-temperature-pressure"
SCHEMA_AUTO = "auto"
SCHEMA_CHOICES = (SCHEMA_LEGACY, SCHEMA_PAPER, SCHEMA_AUTO)


def expected_schema(mode: str) -> dict[str, Any]:
    """Return the implementation schema expected by the training entrypoint."""
    common = {
        "pickle_top_level": "list/tuple of records, or dict with records/data/samples/items",
        "record_type": "dict",
        "branch_input_keys": ["heights", "branch", "topology"],
        "combined_trunk_keys": ["coordinates", "trunk", "coords", "xyz"],
        "combined_target_keys": ["targets", "outputs", "y"],
        "notes": [
            "No pressure labels are fabricated by the training code.",
            "Combined target vectors are treated as already model-ready.",
            "Separate temperature fields are converted from K to normalized Celsius using the legacy range.",
        ],
    }
    if mode == SCHEMA_LEGACY:
        return {
            "mode": SCHEMA_LEGACY,
            **common,
            "branch_input": "heights/branch/topology vector; branch input dimension is inferred, paper target is 251",
            "trunk_input": "2D coordinates, either coordinates/trunk[..., 2] or x and y fields",
            "target_output": "temperature only",
            "coordinate_dimension": 2,
            "output_dimension": 1,
            "required_fields": ["heights or branch/topology", "temperature or target vector", "x/y or coordinates/trunk"],
            "optional_fields": ["z", "pressure"],
        }
    if mode == SCHEMA_PAPER:
        return {
            "mode": SCHEMA_PAPER,
            **common,
            "branch_input": "heights/branch/topology vector; Supplementary Table S2 gives branch input dimension 251",
            "trunk_input": "3D coordinates, either coordinates/trunk[..., 3] or x, y, z fields",
            "target_output": "temperature and pressure",
            "coordinate_dimension": 3,
            "output_dimension": 2,
            "required_fields": [
                "heights or branch/topology",
                "3D coordinates or x/y/z",
                "temperature and pressure, or target/output vector length 2",
            ],
            "optional_fields": [],
        }
    return {
        "mode": SCHEMA_AUTO,
        "selection_rule": (
            "Use paper-temperature-pressure when pressure or a 2D target vector is present "
            "and trunk coordinates are 3D; otherwise fall back to legacy-temperature-only."
        ),
        "legacy_schema": expected_schema(SCHEMA_LEGACY),
        "paper_schema": expected_schema(SCHEMA_PAPER),
    }


def describe_value(value: Any) -> dict[str, Any]:
    """Return a compact schema description for one value."""
    info: dict[str, Any] = {"type": type(value).__name__}
    shape = getattr(value, "shape", None)
    dtype = getattr(value, "dtype", None)
    if shape is not None:
        info["shape"] = list(shape)
    elif isinstance(value, (list, tuple)):
        info["shape"] = [len(value)]
        if value:
            first = value[0]
            nested_shape = getattr(first, "shape", None)
            if nested_shape is not None:
                info["element_shape"] = list(nested_shape)
            elif isinstance(first, (list, tuple)):
                info["element_shape"] = [len(first)]
    if dtype is not None:
        info["dtype"] = str(dtype)
    if isinstance(value, (str, int, float, bool)) or value is None:
        info["sample"] = value
    return info


def find_pickle_files(path: Path, max_files: int) -> list[Path]:
    """Return pickle files from a file or directory path."""
    if path.is_file():
        return [path]
    if not path.exists():
        raise FileNotFoundError(f"Path does not exist: {path}")
    files = sorted(list(path.glob("*.pkl")) + list(path.glob("*.pickle")))
    return files[:max_files]


def load_pickle(path: Path) -> Any:
    """Read one pickle object without writing anything."""
    with path.open("rb") as handle:
        return pickle.load(handle)


def infer_records(obj: Any) -> tuple[Any, str]:
    """Infer the record collection consumed by the current training scripts."""
    if isinstance(obj, list):
        return obj, "top-level list"
    if isinstance(obj, tuple):
        return obj, "top-level tuple"
    if isinstance(obj, dict):
        for key in ("records", "data", "samples", "items"):
            if key in obj and isinstance(obj[key], (list, tuple)):
                return obj[key], f"dict['{key}']"
    return None, "not found"


def summarize_records(records: Any, max_records: int) -> dict[str, Any]:
    """Summarize record-level fields and current-model compatibility."""
    summary: dict[str, Any] = {
        "record_collection_type": type(records).__name__ if records is not None else None,
        "record_count": len(records) if hasattr(records, "__len__") else None,
        "sampled_records": [],
        "field_names_union": [],
        "temperature_exists": False,
        "pressure_exists": False,
        "target_vector_exists": False,
        "z_coordinate_exists": False,
        "x_coordinate_exists": False,
        "y_coordinate_exists": False,
        "heights_exists": False,
        "branch_input_exists": False,
        "trunk_input_exists": False,
        "coordinate_dimension": None,
        "heights_branch_input_length": None,
        "heights_matches_current_model": None,
        "heights_matches_appendix_branch_dim_251": None,
        "output_dimension": None,
        "output_schema": "unknown",
    }
    if records is None:
        return summary

    field_names: set[str] = set()
    for record in list(records)[:max_records]:
        if isinstance(record, dict):
            field_names.update(str(key) for key in record.keys())
            summary["sampled_records"].append({
                str(key): describe_value(value)
                for key, value in record.items()
            })
        else:
            summary["sampled_records"].append(describe_value(record))

    lower_names = {name.lower() for name in field_names}
    summary["field_names_union"] = sorted(field_names)
    summary["temperature_exists"] = bool(lower_names & TEMPERATURE_KEYS)
    summary["pressure_exists"] = bool(lower_names & PRESSURE_KEYS)
    summary["target_vector_exists"] = bool(lower_names & TARGET_KEYS)
    summary["x_coordinate_exists"] = "x" in lower_names
    summary["y_coordinate_exists"] = "y" in lower_names
    summary["z_coordinate_exists"] = "z" in lower_names
    summary["heights_exists"] = "heights" in lower_names
    summary["branch_input_exists"] = bool(lower_names & BRANCH_KEYS)
    summary["trunk_input_exists"] = bool(lower_names & TRUNK_KEYS)

    first_dict = next((record for record in records if isinstance(record, dict)), None)
    if first_dict is not None:
        key_map = {str(key).lower(): key for key in first_dict.keys()}
        heights_key = next((key_map[name] for name in BRANCH_KEYS if name in key_map), None)
        if heights_key is not None:
            heights = first_dict[heights_key]
            if hasattr(heights, "shape"):
                shape = list(heights.shape)
                summary["heights_branch_input_length"] = shape[-1] if shape else None
            elif isinstance(heights, (list, tuple)):
                summary["heights_branch_input_length"] = len(heights)
            summary["heights_matches_appendix_branch_dim_251"] = (
                summary["heights_branch_input_length"] == 251
            )
            summary["heights_matches_current_model"] = summary["heights_branch_input_length"] is not None

        trunk_key = next((key_map[name] for name in TRUNK_KEYS if name in key_map), None)
        if trunk_key is not None:
            trunk_value = first_dict[trunk_key]
            shape = getattr(trunk_value, "shape", None)
            if shape is not None and len(shape) > 0:
                summary["coordinate_dimension"] = int(shape[-1])
            elif isinstance(trunk_value, (list, tuple)):
                summary["coordinate_dimension"] = len(trunk_value)
        elif {"x", "y", "z"} <= set(key_map.keys()):
            summary["coordinate_dimension"] = 3
        elif {"x", "y"} <= set(key_map.keys()):
            summary["coordinate_dimension"] = 2

        target_key = next((key_map[name] for name in TARGET_KEYS if name in key_map), None)
        if target_key is not None:
            target_value = first_dict[target_key]
            shape = getattr(target_value, "shape", None)
            if shape is not None and len(shape) > 0:
                summary["output_dimension"] = int(shape[-1])
            elif isinstance(target_value, (list, tuple)):
                summary["output_dimension"] = len(target_value)

    if summary["temperature_exists"] and summary["pressure_exists"]:
        summary["output_schema"] = "temperature+pressure"
        summary["output_dimension"] = summary["output_dimension"] or 2
    elif summary["temperature_exists"]:
        summary["output_schema"] = "temperature-only"
        summary["output_dimension"] = summary["output_dimension"] or 1
    elif summary["pressure_exists"]:
        summary["output_schema"] = "pressure-only"

    return summary


def inspect_file(path: Path, max_records: int) -> dict[str, Any]:
    """Inspect one pickle file and return a JSON-serializable report."""
    obj = load_pickle(path)
    records, records_location = infer_records(obj)
    top_keys = sorted(str(key) for key in obj.keys()) if isinstance(obj, dict) else None
    return {
        "path": str(path),
        "top_level_type": type(obj).__name__,
        "top_level_keys": top_keys,
        "records_location": records_location,
        "top_level_summary": describe_value(obj),
        "record_summary": summarize_records(records, max_records),
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Read-only schema inspection for DeepONet training pickle files."
    )
    parser.add_argument("path", nargs="?", help="A .pkl/.pickle file or directory containing pickle files.")
    parser.add_argument("--input-file", help="A .pkl/.pickle file to inspect.")
    parser.add_argument("--input-dir", help="A directory containing .pkl/.pickle files to inspect.")
    parser.add_argument("--select-directory", action="store_true", help="Open a directory chooser when no path is provided.")
    parser.add_argument("--print-expected-schema", action="store_true", help="Print the expected training data schema and exit if no path is provided.")
    parser.add_argument("--mode", choices=SCHEMA_CHOICES, default=SCHEMA_AUTO, help="Expected schema mode to print or compare against.")
    parser.add_argument("--max-files", type=int, default=3, help="Maximum files to inspect from a directory.")
    parser.add_argument("--max-records", type=int, default=3, help="Maximum records to summarize per file.")
    parser.add_argument("--no-dialog", action="store_true", help="Disable GUI/text path prompts.")
    args = parser.parse_args()

    if args.print_expected_schema and not any([args.path, args.input_file, args.input_dir, args.select_directory]):
        print(json.dumps(expected_schema(args.mode), indent=2, ensure_ascii=False))
        return 0

    try:
        if args.path:
            input_path = Path(args.path)
        elif args.input_file:
            input_path = choose_existing_file(
                "Choose a DeepONet pickle file",
                arg_value=args.input_file,
                no_dialog=args.no_dialog,
                filetypes=[("Pickle files", "*.pkl *.pickle"), ("All files", "*.*")],
            )
        elif args.input_dir:
            input_path = choose_existing_directory(
                "Choose a DeepONet pickle directory",
                arg_value=args.input_dir,
                no_dialog=args.no_dialog,
            )
        elif args.select_directory:
            input_path = choose_existing_directory(
                "Choose a DeepONet pickle directory",
                no_dialog=args.no_dialog,
            )
        else:
            input_path = choose_existing_file(
                "Choose a DeepONet pickle file",
                no_dialog=args.no_dialog,
                filetypes=[("Pickle files", "*.pkl *.pickle"), ("All files", "*.*")],
            )
    except PathSelectionError as error:
        return fail_with_path_error(error)

    files = find_pickle_files(Path(input_path), args.max_files)
    report = {
        "input_path": str(input_path),
        "expected_schema": expected_schema(args.mode),
        "files_found": len(files),
        "files_inspected": [str(path) for path in files],
        "reports": [inspect_file(path, args.max_records) for path in files],
    }
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
