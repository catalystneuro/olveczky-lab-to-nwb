"""
Data inspection script for Olveczky Lab NWB conversion.

Usage:
    python inspect_data.py --session_dir H:/olveczky_inspect --data_root <path>

Or point it at a downloaded session folder with:
    python inspect_data.py --session_dir <path_to_session>

Requires: numpy, pandas, scipy, h5py
Install: pip install numpy pandas scipy h5py
"""

import argparse
import os
from pathlib import Path

import numpy as np
import pandas as pd


def inspect_frametimes(camera_dir: Path) -> None:
    ft_path = camera_dir / "frametimes.npy"
    if not ft_path.exists():
        print(f"  [MISSING] {ft_path}")
        return
    ft = np.load(ft_path)
    print(f"  shape: {ft.shape}, dtype: {ft.dtype}")
    print(f"  first 5: {ft[:5]}")
    print(f"  last  5: {ft[-5:]}")
    print(f"  min={ft.min():.6f}, max={ft.max():.6f}, range={ft.max()-ft.min():.4f}")
    diffs = np.diff(ft)
    print(
        f"  inter-frame: mean={diffs.mean():.6f}, std={diffs.std():.6f}, "
        f"min={diffs.min():.6f}, max={diffs.max():.6f}"
    )
    expected_fps = 1.0 / diffs.mean() if diffs.mean() > 0 else float("nan")
    print(f"  implied fps: {expected_fps:.2f}")


def inspect_metadata_csv(camera_dir: Path) -> None:
    p = camera_dir / "metadata.csv"
    if not p.exists():
        print(f"  [MISSING] {p}")
        return
    df = pd.read_csv(p)
    print(df.to_string())


def inspect_mat(path: Path, label: str = "") -> None:
    """Try scipy first (MATLAB <7.3), fall back to h5py (MATLAB 7.3 / HDF5)."""
    import scipy.io as sio
    import h5py

    print(f"\n{'=' * 60}")
    print(f"{label or path.name}")

    if not path.exists():
        print(f"  [MISSING] {path}")
        return

    try:
        mat = sio.loadmat(str(path))
        for k, v in mat.items():
            if k.startswith("_"):
                continue
            shape = getattr(v, "shape", "N/A")
            dtype = getattr(v, "dtype", "N/A")
            print(f"  {k}: shape={shape}, dtype={dtype}")
            if hasattr(v, "ndim") and v.ndim <= 2 and v.size > 0 and v.size <= 20:
                print(f"    values: {v}")
            elif hasattr(v, "ndim") and v.ndim >= 1 and v.size > 0:
                print(f"    first row/element: {v.flat[0] if v.ndim == 1 else v[0]}")
    except Exception as e:
        try:
            with h5py.File(str(path), "r") as f:
                def _show(name, obj):
                    if hasattr(obj, "shape"):
                        print(f"  {name}: shape={obj.shape}, dtype={obj.dtype}")
                        if obj.ndim <= 2 and obj.size > 0 and obj.size <= 20:
                            print(f"    values: {obj[()]}")
                        elif obj.ndim >= 1 and obj.size > 0:
                            arr = obj[()]
                            print(f"    first element: {arr.flat[0]}")
                f.visititems(_show)
        except Exception as e2:
            print(f"  [ERROR] scipy: {e} | h5py: {e2}")


def inspect_sdannce_mat(path: Path) -> None:
    """Inspect save_data_AVG.mat — large file, load and show all fields."""
    import scipy.io as sio
    import h5py

    print(f"\n{'=' * 60}")
    print(f"SDANNCE: {path.name}  ({path.stat().st_size / 1e6:.1f} MB)")
    if not path.exists():
        print(f"  [MISSING] {path}")
        return

    try:
        mat = sio.loadmat(str(path))
        keys = [k for k in mat.keys() if not k.startswith("_")]
        print(f"  Keys: {keys}")
        for k, v in mat.items():
            if k.startswith("_"):
                continue
            shape = getattr(v, "shape", "N/A")
            dtype = getattr(v, "dtype", "N/A")
            print(f"\n  '{k}': shape={shape}, dtype={dtype}")
            if hasattr(v, "ndim"):
                if v.ndim == 1 and v.size <= 50:
                    print(f"    values: {v}")
                elif v.dtype.kind in ("U", "S", "O"):
                    # string / object array — print all if small
                    flat = v.flatten()
                    preview = flat[:20]
                    print(f"    string values: {preview}")
                elif v.ndim >= 1 and v.size > 0:
                    print(f"    first row/slice: {v[0] if v.ndim >= 2 else v[:5]}")
    except Exception as e:
        # Try MATLAB 7.3 HDF5 format
        try:
            with h5py.File(str(path), "r") as f:
                print(f"  (HDF5/MATLAB-7.3 format; scipy error was: {e})")
                def _show(name, obj):
                    if isinstance(obj, h5py.Dataset):
                        print(f"  {name}: shape={obj.shape}, dtype={obj.dtype}")
                        if obj.size <= 50:
                            print(f"    values: {obj[()]}")
                        elif obj.size > 0:
                            print(f"    first row: {obj[0] if obj.ndim >= 1 else obj[()]}")
                    elif isinstance(obj, h5py.Group):
                        print(f"  [{name}/]  ({len(obj)} items)")
                f.visititems(_show)
        except Exception as e2:
            print(f"  [ERROR] scipy: {e} | h5py: {e2}")


def inspect_h5(path: Path, label: str = "", max_rows: int = 3) -> None:
    import h5py

    print(f"\n{'=' * 60}")
    print(f"{label or path.name}")
    if not path.exists():
        print(f"  [MISSING] {path}")
        return

    with h5py.File(str(path), "r") as f:
        def _show(name, obj):
            if isinstance(obj, h5py.Dataset):
                print(f"  {name}: shape={obj.shape}, dtype={obj.dtype}")
                if obj.ndim == 1 and obj.size <= 10:
                    print(f"    values: {obj[()]}")
                elif obj.ndim >= 1 and obj.size > 0:
                    slc = obj[:max_rows] if obj.shape[0] >= max_rows else obj[()]
                    print(f"    first {max_rows} rows: {slc}")
            elif isinstance(obj, h5py.Group):
                print(f"  [{name}/]  (group, {len(obj)} items)")
        f.visititems(_show)


def main():
    parser = argparse.ArgumentParser(description="Inspect Olveczky Lab data files")
    parser.add_argument(
        "--inspect_dir",
        type=Path,
        default=Path("H:/olveczky_inspect"),
        help="Directory containing downloaded inspection files",
    )
    parser.add_argument(
        "--session_dir",
        type=Path,
        default=None,
        help="Optional: path to a full session folder (overrides --inspect_dir for session-level files)",
    )
    args = parser.parse_args()

    inspect_dir = args.inspect_dir
    session_dir = args.session_dir

    # --- frametimes + metadata ---
    cam_dirs = []
    if session_dir and (session_dir / "videos").exists():
        cam_dirs = sorted((session_dir / "videos").iterdir())
    elif (inspect_dir / "SCN2A_cam1").exists():
        cam_dirs = [inspect_dir / "SCN2A_cam1"]

    for cam_dir in cam_dirs:
        if cam_dir.is_dir():
            print(f"\n{'=' * 60}")
            print(f"Camera: {cam_dir.name}")
            print("  frametimes.npy:")
            inspect_frametimes(cam_dir)
            print("  metadata.csv:")
            inspect_metadata_csv(cam_dir)

    # --- calibration ---
    cal_dir = (session_dir / "calibration") if session_dir else inspect_dir
    for cal_file in sorted(cal_dir.glob("*.mat")) if cal_dir.exists() else []:
        if "cam" in cal_file.name.lower() or "calib" in cal_file.name.lower():
            inspect_mat(cal_file, f"Calibration: {cal_file.name}")

    # --- SDANNCE COM ---
    com_path = inspect_dir / "com3d_used.mat"
    if com_path.exists():
        inspect_mat(com_path, "COM: com3d_used.mat")

    # --- SDANNCE keypoints (save_data_AVG.mat) ---
    sdannce_candidates = []
    if session_dir:
        for variant in ["SDANNCE", "SDANNCE_x2"]:
            sdannce_root = session_dir / variant
            if sdannce_root.exists():
                for rat_dir in sdannce_root.iterdir():
                    p = rat_dir / "save_data_AVG.mat"
                    if p.exists():
                        sdannce_candidates.append(p)
    for p in inspect_dir.rglob("save_data_AVG.mat"):
        sdannce_candidates.append(p)

    for p in sdannce_candidates[:2]:  # inspect at most 2 rats
        inspect_sdannce_mat(p)

    # --- skin contacts ---
    contacts_candidates = list(inspect_dir.rglob("skin_contacts_symmetric.h5"))
    if session_dir:
        contacts_candidates += list(session_dir.rglob("skin_contacts_symmetric.h5"))
    for p in contacts_candidates[:1]:
        inspect_h5(p, "Skin contacts: skin_contacts_symmetric.h5")

    print("\nInspection complete.")


if __name__ == "__main__":
    main()
