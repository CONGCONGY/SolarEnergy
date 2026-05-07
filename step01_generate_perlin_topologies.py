import argparse
import os
import numpy as np
from perlin_noise import PerlinNoise
from path_selection import PathSelectionError, choose_output_directory, fail_with_path_error


width_num = 10
height_num = 40
length_x = 50
length_y = 200
zoom_factor = 5


num_grids = 1000


DEFAULT_OUTPUT_FOLDER = r"C:\projectcode\topoOptimization\TopoPointData"


seeds = np.random.choice(range(1, 100000), size=num_grids, replace=False)


def generate_perlin_noise_grid(seed):
    """Generate one normalized Perlin height map for a topology seed."""
    noise = PerlinNoise(octaves=6, seed=seed)
    noise_grid = np.zeros((height_num + 1, width_num + 1))
    scale = 10.0
    for i in range(height_num + 1):
        for j in range(width_num + 1):
            noise_grid[i][j] = noise([i / scale, j / scale])


    min_val = np.min(noise_grid)
    max_val = np.max(noise_grid)
    noise_grid = (noise_grid - min_val) / (max_val - min_val) * zoom_factor

    return noise_grid


def generate_grid_with_perlin_noise(seed):
    """Return meshgrid coordinates and the generated height map."""
    noise_grid = generate_perlin_noise_grid(seed)


    x = np.linspace(0, length_x, width_num + 1)
    y = np.linspace(0, length_y, height_num + 1)
    x, y = np.meshgrid(x, y)


    z = noise_grid

    return x, y, z


def save_xyz_to_file(x, y, z, seed, folder_path):
    """Write flattened XYZ topology points for the SpaceClaim generator."""

    x_flat = x.flatten()
    y_flat = y.flatten()
    z_flat = z.flatten()


    xyz_data = list(zip(x_flat, y_flat, z_flat))


    xyz_data_sorted = sorted(xyz_data, key=lambda item: item[0])


    filename = f"GeomData{seed}.txt"
    file_path = os.path.join(folder_path, filename)


    with open(file_path, 'w') as f:
        for x_val, y_val, z_val in xyz_data_sorted:
            f.write(f"{x_val} {y_val} {z_val}\n")


def parse_args():
    parser = argparse.ArgumentParser(description="Generate Perlin topology TXT files.")
    parser.add_argument("--output-dir", help="Directory for generated GeomData*.txt files.")
    parser.add_argument("--no-dialog", action="store_true", help="Disable GUI/text path prompts.")
    return parser.parse_args()


def main():
    args = parse_args()
    try:
        output_dir = choose_output_directory(
            "Choose topology TXT output directory",
            arg_value=args.output_dir,
            default=DEFAULT_OUTPUT_FOLDER,
            no_dialog=args.no_dialog,
        )
    except PathSelectionError as error:
        return fail_with_path_error(error)

    for seed in seeds:
        x, y, z = generate_grid_with_perlin_noise(seed)
        save_xyz_to_file(x, y, z, seed, str(output_dir))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
