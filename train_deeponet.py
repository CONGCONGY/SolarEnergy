"""Paper-target DeepONet training entry with legacy schema compatibility.

The paper target schema uses 3D trunk coordinates and two supervised outputs:
temperature and pressure. The legacy schema remains supported for existing
2D-coordinate, temperature-only pickle files. This script never fabricates
pressure labels; paper mode fails clearly if pressure or 3D coordinates are
missing.
"""

import argparse
import os
import pickle
import sys
import time

if __name__ == "__main__" and any(arg in ("-h", "--help") for arg in sys.argv[1:]):
    help_parser = argparse.ArgumentParser(description="Train the canonical DeepONet model with paper-target schema support.")
    help_parser.add_argument("--train-dir", help="Directory containing training pickle files.")
    help_parser.add_argument("--test-dir", "--val-dir", dest="test_dir", help="Directory containing validation pickle files.")
    help_parser.add_argument("--model-dir", help="Directory for per-epoch model checkpoints.")
    help_parser.add_argument("--log-dir", help="TensorBoard log output directory.")
    help_parser.add_argument(
        "--schema-mode",
        choices=("auto", "legacy-temperature-only", "paper-temperature-pressure"),
        default="auto",
        help="Training data schema mode. Auto uses paper-temperature-pressure only when pressure and 3D coordinates are present.",
    )
    help_parser.add_argument("--no-dialog", action="store_true", help="Disable GUI/text path prompts.")
    help_parser.parse_args()
    raise SystemExit(0)

import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
from torch.utils.tensorboard import SummaryWriter

from path_selection import PathSelectionError, choose_existing_directory, choose_output_directory, fail_with_path_error


SCHEMA_LEGACY = "legacy-temperature-only"
SCHEMA_PAPER = "paper-temperature-pressure"
SCHEMA_AUTO = "auto"
SCHEMA_CHOICES = (SCHEMA_AUTO, SCHEMA_LEGACY, SCHEMA_PAPER)

BRANCH_KEYS = ("heights", "branch", "topology")
COORDINATE_KEYS = ("coordinates", "coordinate", "coords", "trunk", "xyz")
TARGET_KEYS = ("targets", "target", "outputs", "output", "y")
TEMPERATURE_KEYS = ("temperature", "temp", "t")
PRESSURE_KEYS = ("pressure", "p", "pressure_drop", "delta_p", "dp")

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print(f"Current device: {device}")


min_y, max_y = 15.0, 45.0
DEFAULT_TRAIN_DIR = r'E:\ZhaoYang\Train\final_files19327\train'
DEFAULT_TEST_DIR = r'E:\ZhaoYang\Train\final_files19327\test'
DEFAULT_MODEL_DIR = r'E:\ZhaoYang\Train\model'
DEFAULT_LOG_DIR = r'runs\deep_onet_experiment'


def _key_map(record):
    return {str(key).lower(): key for key in record.keys()}


def _get_value(record, names, required=True):
    keys = _key_map(record)
    for name in names:
        key = keys.get(name)
        if key is not None:
            return record[key]
    if required:
        raise KeyError(f"Missing required field. Expected one of: {', '.join(names)}")
    return None


def _as_1d_tensor(value):
    return torch.as_tensor(value, dtype=torch.float32).flatten()


def _temperature_to_model_value(value):
    return (float(value) - 273.15 - min_y) / (max_y - min_y)


def infer_records(data):
    """Return the record list from a pickle object."""
    if isinstance(data, (list, tuple)):
        return data
    if isinstance(data, dict):
        for key in ("records", "data", "samples", "items"):
            value = data.get(key)
            if isinstance(value, (list, tuple)):
                return value
    raise ValueError("Pickle data must be a record list/tuple or a dict containing records/data/samples/items.")


def infer_schema_mode(records):
    """Infer schema mode from the first dictionary record."""
    first = next((record for record in records if isinstance(record, dict)), None)
    if first is None:
        raise ValueError("Cannot infer schema mode because no dictionary record was found.")

    keys = set(_key_map(first).keys())
    has_pressure = bool(keys & set(PRESSURE_KEYS))
    has_target_vector = any(name in keys for name in TARGET_KEYS)
    coordinate_dim = read_coordinates(first, SCHEMA_AUTO).numel()

    if (has_pressure or has_target_vector) and coordinate_dim >= 3:
        return SCHEMA_PAPER

    print(
        "Warning: auto schema detection did not find both pressure targets and 3D coordinates; "
        "falling back to legacy-temperature-only mode."
    )
    return SCHEMA_LEGACY


def read_branch(record):
    """Read topology/height branch input from a supported field name."""
    return _as_1d_tensor(_get_value(record, BRANCH_KEYS))


def read_coordinates(record, schema_mode):
    """Read trunk coordinates for legacy 2D or paper-target 3D mode."""
    coordinate_value = _get_value(record, COORDINATE_KEYS, required=False)
    if coordinate_value is not None:
        coordinates = _as_1d_tensor(coordinate_value)
    else:
        keys = _key_map(record)
        if "x" not in keys or "y" not in keys:
            raise KeyError("Missing coordinate fields. Expected coordinates/trunk or x/y fields.")
        values = [record[keys["x"]], record[keys["y"]]]
        if "z" in keys:
            values.append(record[keys["z"]])
        coordinates = _as_1d_tensor(values)

    if schema_mode == SCHEMA_AUTO:
        return coordinates

    if schema_mode == SCHEMA_PAPER:
        if coordinates.numel() < 3:
            raise ValueError("paper-temperature-pressure mode requires 3D coordinates.")
        return coordinates[:3]

    if coordinates.numel() < 2:
        raise ValueError("legacy-temperature-only mode requires at least 2D coordinates.")

    if coordinate_value is None:
        return torch.tensor([
            float(coordinates[0]) / 5.000000075E-02,
            float(coordinates[1]) / 2.000000030E-01,
        ], dtype=torch.float32)
    return coordinates[:2]


def read_targets(record, schema_mode):
    """Read supervised targets without inventing pressure labels."""
    target_value = _get_value(record, TARGET_KEYS, required=False)
    if target_value is not None:
        targets = _as_1d_tensor(target_value)
        required_dim = 2 if schema_mode == SCHEMA_PAPER else 1
        if targets.numel() < required_dim:
            raise ValueError(f"{schema_mode} requires target dimension {required_dim}.")
        return targets[:required_dim]

    temperature = _get_value(record, TEMPERATURE_KEYS)
    if schema_mode == SCHEMA_PAPER:
        pressure = _get_value(record, PRESSURE_KEYS)
        return torch.tensor([
            _temperature_to_model_value(temperature),
            float(pressure),
        ], dtype=torch.float32)

    return torch.tensor([_temperature_to_model_value(temperature)], dtype=torch.float32)


class LargeDataset(Dataset):
    """Load prepared per-topology records for legacy or paper-target schemas."""

    def __init__(self, data_dir, schema_mode=SCHEMA_AUTO):
        self.data_files = [
            os.path.join(data_dir, file)
            for file in os.listdir(data_dir)
            if file.endswith(('.pkl', '.pickle'))
        ]
        self.requested_schema_mode = schema_mode
        self.schema_mode = self._resolve_schema_mode(schema_mode)
        self.trunk_input_dim = 3 if self.schema_mode == SCHEMA_PAPER else 2
        self.output_dim = 2 if self.schema_mode == SCHEMA_PAPER else 1
        print(f"Using schema mode: {self.schema_mode}")

    def _load_records(self, file_path):
        with open(file_path, 'rb') as handle:
            return infer_records(pickle.load(handle))

    def _resolve_schema_mode(self, schema_mode):
        if schema_mode != SCHEMA_AUTO:
            return schema_mode
        if not self.data_files:
            raise FileNotFoundError("No .pkl or .pickle files found for schema auto-detection.")
        return infer_schema_mode(self._load_records(self.data_files[0]))

    def __len__(self):
        return len(self.data_files)

    def __getitem__(self, idx):
        records = self._load_records(self.data_files[idx])

        heights = torch.stack([read_branch(record) for record in records], dim=0) / 5
        trunk_inputs = torch.stack([read_coordinates(record, self.schema_mode) for record in records], dim=0)
        targets = torch.stack([read_targets(record, self.schema_mode) for record in records], dim=0)

        return heights, trunk_inputs, targets


class BranchNet(nn.Module):
    def __init__(self, input_dim):
        super(BranchNet, self).__init__()
        self.fc1 = nn.Linear(input_dim, 1024)
        self.bn1 = nn.BatchNorm1d(1024)
        self.dropout1 = nn.Dropout(0.5)
        self.fc2 = nn.Linear(1024, 512)
        self.bn2 = nn.BatchNorm1d(512)
        self.dropout2 = nn.Dropout(0.5)
        self.fc3 = nn.Linear(512, 256)
        self.bn3 = nn.BatchNorm1d(256)
        self.dropout3 = nn.Dropout(0.4)
        self.fc4 = nn.Linear(256, 128)
        self.bn4 = nn.BatchNorm1d(128)
        self.dropout4 = nn.Dropout(0.4)
        self.fc5 = nn.Linear(128, 64)

    def forward(self, x):
        x = torch.relu(self.bn1(self.fc1(x)))
        x = self.dropout1(x)
        x = torch.relu(self.bn2(self.fc2(x)))
        x = self.dropout2(x)
        x = torch.relu(self.bn3(self.fc3(x)))
        x = self.dropout3(x)
        x = torch.relu(self.bn4(self.fc4(x)))
        x = self.dropout4(x)
        return self.fc5(x)


class TrunkNet(nn.Module):
    """Trunk network for 2D legacy or 3D paper-target coordinates."""

    def __init__(self, input_dim, output_dim):
        super(TrunkNet, self).__init__()
        self.fc1 = nn.Linear(input_dim, 128)
        self.bn1 = nn.BatchNorm1d(128)
        self.dropout1 = nn.Dropout(0.6)
        self.fc2 = nn.Linear(128, 256)
        self.bn2 = nn.BatchNorm1d(256)
        self.dropout2 = nn.Dropout(0.5)
        self.fc3 = nn.Linear(256, 128)
        self.bn3 = nn.BatchNorm1d(128)
        self.dropout3 = nn.Dropout(0.5)
        self.fc4 = nn.Linear(128, 64)
        self.bn4 = nn.BatchNorm1d(64)
        self.dropout4 = nn.Dropout(0.4)
        self.fc5 = nn.Linear(64, output_dim)

    def forward(self, x):
        x = torch.relu(self.bn1(self.fc1(x)))
        x = self.dropout1(x)
        x = torch.relu(self.bn2(self.fc2(x)))
        x = self.dropout2(x)
        x = torch.relu(self.bn3(self.fc3(x)))
        x = self.dropout3(x)
        x = torch.relu(self.bn4(self.fc4(x)))
        x = self.dropout4(x)
        return self.fc5(x)


class DeepONet(nn.Module):
    def __init__(self, branch_input_dim, trunk_input_dim, trunk_output_dim, output_dim):
        super(DeepONet, self).__init__()
        self.output_dim = output_dim
        self.branch_net = BranchNet(branch_input_dim)
        self.trunk_net = TrunkNet(trunk_input_dim, trunk_output_dim)
        self.output_projection = None
        if output_dim > 1:
            self.output_projection = nn.Linear(trunk_output_dim, output_dim, bias=False)

    def forward(self, branch_input, trunk_input):
        branch_output = self.branch_net(branch_input.view(branch_input.size(0), -1))
        trunk_output = self.trunk_net(trunk_input)
        combined_features = branch_output * trunk_output
        if self.output_projection is None:
            return torch.sum(combined_features, dim=1, keepdim=True)
        return self.output_projection(combined_features)


def parse_args():
    parser = argparse.ArgumentParser(description="Train the canonical DeepONet model with paper-target schema support.")
    parser.add_argument("--train-dir", help="Directory containing training pickle files.")
    parser.add_argument("--test-dir", "--val-dir", dest="test_dir", help="Directory containing validation pickle files.")
    parser.add_argument("--model-dir", help="Directory for per-epoch model checkpoints.")
    parser.add_argument("--log-dir", help="TensorBoard log output directory.")
    parser.add_argument(
        "--schema-mode",
        choices=SCHEMA_CHOICES,
        default=SCHEMA_AUTO,
        help="Training data schema mode. Auto uses paper-temperature-pressure only when pressure and 3D coordinates are present.",
    )
    parser.add_argument("--no-dialog", action="store_true", help="Disable GUI/text path prompts.")
    return parser.parse_args()


def initialize_weights(m):
    if isinstance(m, nn.Linear):
        nn.init.xavier_normal_(m.weight)
        if m.bias is not None:
            nn.init.zeros_(m.bias)


if __name__ == '__main__':
    args = parse_args()
    try:
        train_dir = choose_existing_directory(
            "Choose DeepONet training data directory",
            arg_value=args.train_dir,
            default=DEFAULT_TRAIN_DIR,
            no_dialog=args.no_dialog,
        )
        test_dir = choose_existing_directory(
            "Choose DeepONet validation data directory",
            arg_value=args.test_dir,
            default=DEFAULT_TEST_DIR,
            no_dialog=args.no_dialog,
        )
        model_dir = choose_output_directory(
            "Choose DeepONet model checkpoint directory",
            arg_value=args.model_dir,
            default=DEFAULT_MODEL_DIR,
            no_dialog=args.no_dialog,
        )
        log_dir = choose_output_directory(
            "Choose TensorBoard log directory",
            arg_value=args.log_dir,
            default=DEFAULT_LOG_DIR,
            no_dialog=args.no_dialog,
        )
    except PathSelectionError as error:
        raise SystemExit(fail_with_path_error(error))

    train_dataset = LargeDataset(train_dir, schema_mode=args.schema_mode)
    test_dataset = LargeDataset(test_dir, schema_mode=train_dataset.schema_mode)

    train_loader = DataLoader(train_dataset, batch_size=2, shuffle=True, num_workers=10, pin_memory=True)
    val_loader = DataLoader(test_dataset, batch_size=4, shuffle=False, num_workers=12, pin_memory=True)

    sample_heights, _, _ = train_dataset[0]
    model = DeepONet(
        branch_input_dim=sample_heights.shape[1],
        trunk_input_dim=train_dataset.trunk_input_dim,
        trunk_output_dim=64,
        output_dim=train_dataset.output_dim,
    ).to(device)
    model.apply(initialize_weights)

    criterion = nn.SmoothL1Loss()
    optimizer = optim.Adam(model.parameters(), lr=1e-5, weight_decay=1e-4)

    step_size_up = len(train_loader) // 2
    scheduler = optim.lr_scheduler.CyclicLR(
        optimizer,
        base_lr=1e-5,
        max_lr=5e-4,
        step_size_up=step_size_up,
        mode='triangular'
    )

    writer = SummaryWriter(str(log_dir))

    num_epochs = 200
    for epoch in range(num_epochs):
        epoch_start_time = time.time()

        model.train()
        for i, (heights, X_batch, y_batch) in enumerate(train_loader):
            heights = heights.view(-1, heights.size(-1)).to(device)
            X_batch = X_batch.view(-1, X_batch.size(-1)).to(device)
            y_batch = y_batch.view(-1, y_batch.size(-1)).to(device)

            outputs = model(heights, X_batch)
            loss = criterion(outputs, y_batch)

            optimizer.zero_grad()
            loss.backward()
            optimizer.step()

            scheduler.step()

            torch.cuda.empty_cache()

            print(f'Epoch {epoch + 1}, Batch {i + 1}/{len(train_loader)}: Loss: {loss.item():.4f}')
            writer.add_scalar('Loss/train', loss.item(), epoch * len(train_loader) + i)

        model.eval()
        val_loss = 0.0
        with torch.no_grad():
            for heights, X_batch, y_batch in val_loader:
                heights = heights.view(-1, heights.size(-1)).to(device)
                X_batch = X_batch.view(-1, X_batch.size(-1)).to(device)
                y_batch = y_batch.view(-1, y_batch.size(-1)).to(device)

                outputs = model(heights, X_batch)

                if train_dataset.output_dim == 1:
                    outputs_actual = outputs * (max_y - min_y) + min_y
                    y_batch_actual = y_batch * (max_y - min_y) + min_y
                    loss = criterion(outputs_actual, y_batch_actual)
                else:
                    loss = criterion(outputs, y_batch)
                val_loss += loss.item()

        average_val_loss = val_loss / len(val_loader)
        average_val_rmse = torch.sqrt(torch.tensor(average_val_loss)).item()
        writer.add_scalar('Loss/val_rmse', average_val_rmse, epoch)
        print(f'Epoch [{epoch + 1}/{num_epochs}], Validation RMSE: {average_val_rmse:.4f}')

        model_save_path = os.path.join(model_dir, f"deep_onet_model_epoch_{epoch + 1}.pth")
        torch.save(model.state_dict(), model_save_path)
        print(f"Model saved to: {model_save_path}")

        epoch_end_time = time.time()
        epoch_duration = epoch_end_time - epoch_start_time
        print(f'Epoch [{epoch + 1}/{num_epochs}] Cost Time: {epoch_duration:.2f} seconds')

    writer.close()
    print("Training completed.")
