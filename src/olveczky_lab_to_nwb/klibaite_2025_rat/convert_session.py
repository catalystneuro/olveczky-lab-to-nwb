"""
Convert one Klibaite 2025 - Rat social behavior session to NWB.

Produces two NWB files per session — one per rat — both linking to the same
external video files.

Session directory naming convention:
    <data_root>/ugne/<cohort>/<cohort>_SOC<N>/<YYYY_MM_DD_M{rat1}_M{rat2}>/

Usage
-----
python convert_session.py \\
    --session_dir  /path/to/2022_09_22_M1_M2 \\
    --output_dir   /path/to/nwb_output \\
    --cohort     SCN2A \\
    --encounter    SOC1 \\
    --rat_log_path /path/to/ugne_rat_log.xlsx \\
    [--contacts_file /path/to/social_touch/.../skin_contacts_symmetric.h5] \\
    [--stub_test]
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path

import yaml
from neuroconv import ConverterPipe
from neuroconv.datainterfaces import DANNCEInterface

from olveczky_lab_to_nwb.klibaite_2025_rat.utils.constants import SDANNCE_LANDMARK_NAMES, SDANNCE_SKELETON_EDGES
from olveczky_lab_to_nwb.klibaite_2025_rat.interfaces import (
    OlveczkyVideoInterface,
    SkinContactsInterface,
)
from olveczky_lab_to_nwb.klibaite_2025_rat.utils.subject_metadata import get_subject_metadata

# Path to the static metadata YAML (same directory as this script).
_METADATA_YAML = Path(__file__).parent / "general_metadata.yaml"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def parse_session_folder_name(folder_name: str) -> dict:
    """
    Parse a session folder name into its components.

    Expected format: ``YYYY_MM_DD_M{rat1_id}_M{rat2_id}``
    e.g. ``2022_09_22_M1_M2`` → date 2022-09-22, rat1_id "M1", rat2_id "M2"
    """
    pattern = r"^(\d{4})_(\d{2})_(\d{2})_(M\w+)_(M\w+)$"
    m = re.match(pattern, folder_name)
    if not m:
        raise ValueError(
            f"Session folder '{folder_name}' does not match expected pattern " "YYYY_MM_DD_M<rat1>_M<rat2>."
        )
    year, month, day, rat1_id, rat2_id = m.groups()
    session_date = datetime(int(year), int(month), int(day), tzinfo=timezone.utc)
    return {
        "session_date": session_date,
        "rat1_id": rat1_id,
        "rat2_id": rat2_id,
        "session_date_str": f"{year}{month}{day}",
    }


def find_sdannce_mat(session_dir: Path, rat: str) -> Path:
    """
    Find ``save_data_AVG.mat`` for a given rat.

    Handles both SDANNCE folder naming variants:
    - SCN2A: ``SDANNCE/bsl0.5_FM_rat{N}/``
    - ARID1B: ``SDANNCE_x2/bsl0.5_FM_rat{N}/``
    """
    for sdannce_root_name in ["SDANNCE", "SDANNCE_x2"]:
        sdannce_root = session_dir / sdannce_root_name
        if not sdannce_root.exists():
            continue
        for rat_dir in sorted(sdannce_root.iterdir()):
            if rat_dir.is_dir() and rat.lower() in rat_dir.name.lower():
                mat_file = rat_dir / "save_data_AVG.mat"
                if mat_file.exists():
                    return mat_file
    raise FileNotFoundError(
        f"Could not find save_data_AVG.mat for '{rat}' in {session_dir}. "
        "Searched SDANNCE/ and SDANNCE_x2/ subdirectories."
    )


# ---------------------------------------------------------------------------
# Per-rat conversion
# ---------------------------------------------------------------------------


def convert_one_rat(
    session_dir: Path,
    output_dir: Path,
    rat_idx: int,
    rat_id: str,
    rat1_id: str,
    rat2_id: str,
    session_date: datetime,
    session_date_str: str,
    cohort: str,
    encounter: str,
    contacts_file: Path | None,
    rat_log_path: Path | None,
    stub_test: bool,
) -> Path:
    """
    Build and run the ConverterPipe for one rat, writing one NWB file.

    Returns
    -------
    Path
        Path to the written NWB file.
    """
    frametimes_path = session_dir / "videos" / "Camera1" / "frametimes.npy"

    # --- Assemble interfaces ---
    interfaces: list = []

    sdannce_mat = find_sdannce_mat(session_dir, f"rat{rat_idx}")
    pose_key = f"PoseEstimationSDANNCERat{rat_idx}"
    interfaces.append(
        DANNCEInterface(
            file_path=sdannce_mat,
            frametimes_file_path=frametimes_path,
            landmark_names=SDANNCE_LANDMARK_NAMES,
            subject_name=f"rat{rat_idx}",
            pose_estimation_metadata_key=pose_key,
        )
    )

    interfaces.append(OlveczkyVideoInterface(session_videos_dir=session_dir / "videos"))

    if contacts_file is not None and contacts_file.exists():
        interfaces.append(
            SkinContactsInterface(
                contacts_file_path=contacts_file,
                frametimes_file_path=frametimes_path,
            )
        )
    elif contacts_file is not None:
        print(f"  [WARNING] Contacts file not found, skipping: {contacts_file}")

    converter = ConverterPipe(data_interfaces=interfaces)

    # --- Load static metadata and override session-specific fields ---
    with open(_METADATA_YAML) as f:
        metadata = yaml.safe_load(f)

    # --- Subject metadata ---
    subject_id = f"{cohort}-{rat_id}"
    if rat_log_path is not None:
        try:
            subj = get_subject_metadata(rat_id, cohort, rat_log_path)
            metadata["Subject"].update(subj)
        except (KeyError, Exception) as exc:
            print(f"  [WARNING] Could not load subject metadata for {rat_id}: {exc}")
            metadata["Subject"]["subject_id"] = subject_id
            metadata["Subject"]["description"] = (
                f"Rat {rat_id}, cohort group {cohort}. "
                f"Paired with {rat2_id if rat_idx == 1 else rat1_id} in this session."
            )
    else:
        metadata["Subject"]["subject_id"] = subject_id
        metadata["Subject"]["description"] = (
            f"Rat {rat_id}, cohort group {cohort}. "
            f"Paired with {rat2_id if rat_idx == 1 else rat1_id} in this session."
        )

    # --- Session metadata ---

    session_id = f"{session_date_str}-{cohort}-{encounter}-{rat1_id}-{rat2_id}"
    metadata["NWBFile"]["session_id"] = session_id
    metadata["NWBFile"]["session_start_time"] = session_date.isoformat()
    metadata["NWBFile"]["session_description"] = (
        f"{metadata['NWBFile']['session_description'].strip()} "
        f"Cohort group: {cohort}, encounter round: {encounter}, "
        f"session: {rat1_id} (rat1) vs {rat2_id} (rat2)."
    )

    # --- Inject skeleton edges and sDANNCE labels into PoseEstimation metadata ---
    # Must include all schema-required fields (name, nodes) so validate_metadata passes.
    # add_to_nwbfile deep-merges this with get_metadata(); edges replaces the empty default.
    skeleton_key = f"Skeleton{pose_key}_{f'rat{rat_idx}'.capitalize()}"
    metadata.setdefault("PoseEstimation", {}).setdefault("Skeletons", {})[skeleton_key] = {
        "name": skeleton_key,
        "nodes": SDANNCE_LANDMARK_NAMES,
        "edges": SDANNCE_SKELETON_EDGES,
    }
    metadata["PoseEstimation"].setdefault("PoseEstimationContainers", {})[pose_key] = {
        "name": pose_key,
        "source_software": "sDANNCE",
        "scorer": "sDANNCE",
        "description": "3D keypoint coordinates estimated using sDANNCE (social DANNCE).",
    }

    # --- Write NWB file ---
    output_dir.mkdir(parents=True, exist_ok=True)
    nwb_filename = f"sub-{subject_id}_ses-{session_id}.nwb"
    nwbfile_path = output_dir / nwb_filename

    conversion_options = (
        {iface.__class__.__name__: {"stub_test": stub_test} for iface in interfaces} if stub_test else {}
    )

    converter.run_conversion(
        nwbfile_path=nwbfile_path,
        metadata=metadata,
        conversion_options=conversion_options,
        overwrite=True,
    )

    print(f"  Written: {nwbfile_path}")
    return nwbfile_path


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def convert_session(
    session_dir: Path,
    output_dir: Path,
    cohort: str,
    encounter: str,
    contacts_file: Path | None = None,
    rat_log_path: Path | None = None,
    stub_test: bool = False,
) -> list[Path]:
    """
    Convert one session to two NWB files (one per rat).

    Parameters
    ----------
    session_dir : Path
        Path to the session folder (e.g., ``2022_09_22_M1_M2/``).
    output_dir : Path
        Directory where NWB files will be written.
    cohort : str
        Cohort group label (e.g., ``"SCN2A"``, ``"ARID1B"``).
    encounter : str
        Encounter round label (e.g., ``"SOC1"``).
    contacts_file : Path, optional
        Path to ``skin_contacts_symmetric.h5``.  If None, the skin contacts
        interface is skipped.
    rat_log_path : Path, optional
        Path to ``ugne_rat_log.xlsx`` for per-rat DOB lookup.
    stub_test : bool
        If True, convert only the first 100 frames for quick testing.

    Returns
    -------
    list[Path]
        Paths to the two written NWB files.
    """
    session_dir = Path(session_dir)
    output_dir = Path(output_dir)

    parsed = parse_session_folder_name(session_dir.name)
    session_date = parsed["session_date"]
    session_date_str = parsed["session_date_str"]
    rat1_id = parsed["rat1_id"]
    rat2_id = parsed["rat2_id"]

    print(f"Converting session: {session_dir.name}")
    print(f"  Cohort: {cohort}, Encounter: {encounter}")
    print(f"  Rats: {rat1_id} (rat1), {rat2_id} (rat2)")
    print(f"  Stub test: {stub_test}")

    output_paths = []
    for rat_idx, rat_id in [(1, rat1_id), (2, rat2_id)]:
        print(f"\n  --- Converting {rat_id} (rat{rat_idx}) ---")
        path = convert_one_rat(
            session_dir=session_dir,
            output_dir=output_dir,
            rat_idx=rat_idx,
            rat_id=rat_id,
            rat1_id=rat1_id,
            rat2_id=rat2_id,
            session_date=session_date,
            session_date_str=session_date_str,
            cohort=cohort,
            encounter=encounter,
            contacts_file=contacts_file,
            rat_log_path=rat_log_path,
            stub_test=stub_test,
        )
        output_paths.append(path)

    return output_paths


if __name__ == "__main__":
    # import argparse
    # parser = argparse.ArgumentParser(description="Convert one Olveczky Lab social behavior session to NWB.")
    # parser.add_argument("--session_dir", type=Path, required=True, help="Path to session folder.")
    # parser.add_argument("--output_dir", type=Path, required=True, help="Output directory for NWB files.")
    # parser.add_argument("--cohort", type=str, required=True, help="Cohort group (e.g. SCN2A, ARID1B).")
    # parser.add_argument("--encounter", type=str, required=True, help="Encounter round (e.g. SOC1, SOC2).")
    # parser.add_argument("--contacts_file", type=Path, default=None, help="Path to skin_contacts_symmetric.h5.")
    # parser.add_argument("--rat_log_path", type=Path, default=None, help="Path to ugne_rat_log.xlsx.")
    # parser.add_argument("--stub_test", action="store_true", help="Convert only first 100 frames for testing.")
    # args = parser.parse_args()
    # session_dir = args.session_dir
    # output_dir = args.output_dir
    # cohort = args.cohort
    # encounter = args.encounter
    # contacts_file = args.contacts_file
    # rat_log_path = args.rat_log_path
    # stub_test = args.stub_test

    data_dir = Path("H:/Olveczky-CN-data-share/ugne")
    output_dir = Path("H:/olveczky-nwbfiles")
    cohort = "ARID1B"
    encounter = "SOC1"
    session = "2022_10_17_M1_M2"
    session_dir = data_dir / cohort / f"{cohort}_{encounter}" / session
    contacts_file = data_dir / "social_touch" / f"{cohort}_{encounter}" / session / "skin_contacts_symmetric.hdf5"
    rat_log_path = data_dir / "ugne_rat_log.xlsx"
    stub_test = True

    convert_session(
        session_dir=session_dir,
        output_dir=output_dir,
        cohort=cohort,
        encounter=encounter,
        contacts_file=contacts_file,
        rat_log_path=rat_log_path,
        stub_test=stub_test,
    )
