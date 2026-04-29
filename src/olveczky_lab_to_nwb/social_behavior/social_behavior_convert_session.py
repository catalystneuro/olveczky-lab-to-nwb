"""
Convert one Olveczky Lab social behavior session to NWB.

Produces two NWB files per session — one per rat — both linking to the same
external video files.

Session directory naming convention:
    <data_root>/ugne/<genotype>/<genotype>_SOC<N>/<YYYY_MM_DD_M{rat1}_M{rat2}>/

Usage
-----
python social_behavior_convert_session.py \\
    --session_dir  /path/to/2022_09_22_M1_M2 \\
    --output_dir   /path/to/nwb_output \\
    --genotype     SCN2A \\
    --encounter    SOC1 \\
    [--contacts_file /path/to/social_touch/.../skin_contacts_symmetric.h5] \\
    [--stub_test]
"""

from __future__ import annotations

import argparse
import re
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import yaml
from neuroconv import ConverterPipe
from neuroconv.datainterfaces import SDANNCEInterface
from pynwb import NWBFile
from pynwb.file import Subject

from olveczky_lab_to_nwb.social_behavior.interfaces import (
    OlveczkyVideoInterface,
    SkinContactsInterface,
)

# Path to the static metadata YAML (same directory as this script).
_METADATA_YAML = Path(__file__).parent / "social_behavior_metadata.yaml"


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


def build_nwb_filename(subject_id: str, session_date_str: str, rat1_id: str, rat2_id: str) -> str:
    """Return DANDI-compliant NWB filename for one rat."""
    return f"sub-{subject_id}_ses-{session_date_str}-{rat1_id}-{rat2_id}.nwb"


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
    genotype: str,
    encounter: str,
    contacts_file: Path | None,
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
    interfaces.append(
        SDANNCEInterface(
            file_path=sdannce_mat,
            frametimes_file_path=frametimes_path,
            subject_name=f"rat{rat_idx}",
            animal_index=rat_idx,
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

    session_id = f"{session_date_str}-{genotype}-{encounter}-{rat1_id}-{rat2_id}"
    metadata["NWBFile"]["session_id"] = session_id
    metadata["NWBFile"]["session_start_time"] = session_date.isoformat()
    metadata["NWBFile"]["session_description"] = (
        f"{metadata['NWBFile']['session_description'].strip()} "
        f"Genotype group: {genotype}, encounter round: {encounter}, "
        f"session: {rat1_id} (rat1) vs {rat2_id} (rat2)."
    )

    metadata["Subject"]["subject_id"] = rat_id
    metadata["Subject"]["description"] = (
        f"Rat {rat_id}, genotype group {genotype}. "
        f"Paired with {rat2_id if rat_idx == 1 else rat1_id} in this session."
    )
    # TODO: fill in per-subject metadata once the lab provides the spreadsheet
    # (see metadata_request_email.md).  These fields are required by DANDI:
    #   metadata["Subject"]["sex"] = "M"  # "M", "F", or "U"
    #   metadata["Subject"]["date_of_birth"] = "2022-08-01T00:00:00+00:00"
    #   metadata["Subject"]["weight"] = "350 g"
    #   metadata["Subject"]["genotype"] = "SCN2A+/-"
    #   metadata["Subject"]["strain"] = "Long-Evans"
    # NWB Inspector CRITICAL: subject must have age or date_of_birth before DANDI upload.

    # --- Write NWB file ---
    output_dir.mkdir(parents=True, exist_ok=True)
    nwb_filename = build_nwb_filename(rat_id, session_date_str, rat1_id, rat2_id)
    nwbfile_path = output_dir / nwb_filename

    conversion_options = (
        {iface.__class__.__name__: {"stub_test": stub_test} for iface in interfaces} if stub_test else {}
    )

    converter.run_conversion(
        nwbfile_path=str(nwbfile_path),
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
    genotype: str,
    encounter: str,
    contacts_file: Path | None = None,
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
    genotype : str
        Genotype group label (e.g., ``"SCN2A"``, ``"ARID1B"``).
    encounter : str
        Encounter round label (e.g., ``"SOC1"``).
    contacts_file : Path, optional
        Path to ``skin_contacts_symmetric.h5``.  If None, the skin contacts
        interface is skipped.
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
    print(f"  Genotype: {genotype}, Encounter: {encounter}")
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
            genotype=genotype,
            encounter=encounter,
            contacts_file=contacts_file,
            stub_test=stub_test,
        )
        output_paths.append(path)

    return output_paths


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Convert one Olveczky Lab social behavior session to NWB.")
    parser.add_argument("--session_dir", type=Path, required=True, help="Path to session folder.")
    parser.add_argument("--output_dir", type=Path, required=True, help="Output directory for NWB files.")
    parser.add_argument("--genotype", type=str, required=True, help="Genotype group (e.g. SCN2A, ARID1B).")
    parser.add_argument("--encounter", type=str, required=True, help="Encounter round (e.g. SOC1, SOC2).")
    parser.add_argument("--contacts_file", type=Path, default=None, help="Path to skin_contacts_symmetric.h5.")
    parser.add_argument("--stub_test", action="store_true", help="Convert only first 100 frames for testing.")
    args = parser.parse_args()

    convert_session(
        session_dir=args.session_dir,
        output_dir=args.output_dir,
        genotype=args.genotype,
        encounter=args.encounter,
        contacts_file=args.contacts_file,
        stub_test=args.stub_test,
    )
