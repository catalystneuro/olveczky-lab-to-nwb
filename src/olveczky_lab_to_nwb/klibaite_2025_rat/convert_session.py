"""Convert one rat's data from a Klibaite 2025 - Rat social behavior session to NWB.

Each session folder holds data for a pair of rats; this script converts one of
them (selected via ``rat_idx``) to one NWB file, linking to the shared external
video files.

Session directory naming convention:
    <data_root>/ugne/<cohort>/<cohort>_SOC<N>/<YYYY_MM_DD_M{rat1}_M{rat2}>/
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Union

import yaml
from neuroconv.utils import dict_deep_update

from olveczky_lab_to_nwb.klibaite_2025_rat.nwbconverter import Klibaite2025NWBConverter
from olveczky_lab_to_nwb.klibaite_2025_rat.utils.constants import SDANNCE_LANDMARK_NAMES, SDANNCE_SKELETON_EDGES

_GENERAL_METADATA_YAML = Path(__file__).parent / "general_metadata.yaml"


def parse_session_folder_name(folder_name: str) -> dict:
    """Parse a session folder name into its components.

    Expected format: ``YYYY_MM_DD_M{rat1_id}_M{rat2_id}``
    e.g. ``2022_09_22_M1_M2`` -> date 2022-09-22, rat1_id "M1", rat2_id "M2"
    """
    pattern = r"^(\d{4})_(\d{2})_(\d{2})_(M\w+)_(M\w+)$"
    m = re.match(pattern, folder_name)
    if not m:
        raise ValueError(
            f"Session folder '{folder_name}' does not match expected pattern " "YYYY_MM_DD_M<rat1>_M<rat2>."
        )
    year, month, day, rat1_id, rat2_id = m.groups()
    return {
        "session_date": datetime(int(year), int(month), int(day), tzinfo=timezone.utc),
        "session_date_str": f"{year}{month}{day}",
        "rat1_id": rat1_id,
        "rat2_id": rat2_id,
    }


def _encounter_to_label(encounter: str) -> str:
    """Convert an encounter round code to a session_id label.

    e.g. ``"SOC1"`` -> ``"day-1-social"``, ``"SOC12"`` -> ``"day-12-social"``.
    """
    m = re.match(r"^SOC(\d+)$", encounter)
    if not m:
        raise ValueError(f"Encounter '{encounter}' does not match expected pattern 'SOC<N>'.")
    return f"day-{m.group(1)}-social"


def find_sdannce_mat(session_dir_path: Path, rat: str) -> Path:
    """Find ``save_data_AVG.mat`` for a given rat.

    Handles both SDANNCE folder naming variants:
    - SCN2A: ``SDANNCE/bsl0.5_FM_rat{N}/``
    - ARID1B: ``SDANNCE_x2/bsl0.5_FM_rat{N}/``
    """
    for sdannce_root_name in ["SDANNCE", "SDANNCE_x2"]:
        sdannce_root = session_dir_path / sdannce_root_name
        if not sdannce_root.exists():
            continue
        for rat_dir in sorted(sdannce_root.iterdir()):
            if rat_dir.is_dir() and rat.lower() in rat_dir.name.lower():
                mat_file = rat_dir / "save_data_AVG.mat"
                if mat_file.exists():
                    return mat_file
    raise FileNotFoundError(
        f"Could not find save_data_AVG.mat for '{rat}' in {session_dir_path}. "
        "Searched SDANNCE/ and SDANNCE_x2/ subdirectories."
    )


def session_to_nwb(
    session_dir_path: Union[str, Path],
    output_dir_path: Union[str, Path],
    rat_idx: int,
    cohort: str,
    encounter: str,
    subject_metadata: dict | None = None,
    contacts_file_path: Union[str, Path, None] = None,
    stub_test: bool = False,
    overwrite: bool = True,
    verbose: bool = False,
) -> Path:
    """Convert one rat from one session directory to one NWB file.

    Parameters
    ----------
    session_dir_path : str or Path
        Path to the session folder (e.g. ``2022_09_22_M1_M2/``), shared by both rats.
    output_dir_path : str or Path
        Directory where the NWB file will be written.
    rat_idx : int
        Which rat in the pair to convert: 1 or 2.
    cohort : str
        Cohort group label (e.g. ``"SCN2A"``, ``"ARID1B"``).
    encounter : str
        Encounter round label (e.g. ``"SOC1"``).
    subject_metadata : dict, optional
        Per-rat NWB Subject fields (sex, date_of_birth, strain, genotype, etc.).
        When not provided, a minimal subject_id/description is generated instead.
    contacts_file_path : str or Path, optional
        Path to ``skin_contacts_symmetric.h5``. If None or missing, the skin
        contacts interface is skipped.
    stub_test : bool
        If True, convert only the first 100 frames for quick testing.
    overwrite : bool
        If True, overwrite an existing NWB file at the output path.
    verbose : bool
        Pass-through to converter interfaces.

    Returns
    -------
    Path
        Path to the written NWB file.
    """
    session_dir_path = Path(session_dir_path)
    output_dir_path = Path(output_dir_path)
    if stub_test:
        output_dir_path = output_dir_path / "nwb_stub"

    parsed = parse_session_folder_name(session_dir_path.name)
    session_date = parsed["session_date"]
    session_date_str = parsed["session_date_str"]
    rat1_id, rat2_id = parsed["rat1_id"], parsed["rat2_id"]
    rat_id, paired_rat_id = (rat1_id, rat2_id) if rat_idx == 1 else (rat2_id, rat1_id)

    subject_id = f"{cohort}-{rat_id}"
    encounter_label = _encounter_to_label(encounter)
    session_id = f"{encounter_label}-{rat1_id}-{rat2_id}-{session_date_str}"

    output_dir_path = output_dir_path / f"sub-{subject_id}"
    output_dir_path.mkdir(parents=True, exist_ok=True)

    nwbfile_path = output_dir_path / f"sub-{subject_id}_ses-{session_id}.nwb"

    sdannce_mat = find_sdannce_mat(session_dir_path, f"rat{rat_idx}")
    pose_key = "PoseEstimationSDANNCE"

    # ── Build source_data ────────────────────────────────────────────────────
    source_data: dict = {}
    conversion_options: dict = {}

    source_data["DANNCE"] = dict(
        file_path=str(sdannce_mat),
        videos_folder_path=session_dir_path / "videos",
        landmark_names=SDANNCE_LANDMARK_NAMES,
        subject_name=f"rat{rat_idx}",
        metadata_key=pose_key,
    )
    calibration_path = session_dir_path / "calibration"
    if calibration_path.is_dir():
        source_data["DANNCE"]["calibration_path"] = str(calibration_path)
    else:
        print(f"  [WARNING] Calibration directory not found, skipping camera calibration: {calibration_path}")
    conversion_options["DANNCE"] = dict(stub_test=stub_test)

    if contacts_file_path is not None:
        contacts_file_path = Path(contacts_file_path)
        if contacts_file_path.exists():
            source_data["SkinContacts"] = dict(
                contacts_file_path=str(contacts_file_path),
                frametimes_file_path=str(session_dir_path / "videos" / "Camera1" / "frametimes.npy"),
            )
            conversion_options["SkinContacts"] = dict(stub_test=stub_test)
        else:
            print(f"  [WARNING] Contacts file not found, skipping: {contacts_file_path}")

    # ── Instantiate converter ────────────────────────────────────────────────
    converter = Klibaite2025NWBConverter(source_data=source_data, verbose=verbose)

    # ── Build metadata (layered) ─────────────────────────────────────────────
    # Start from the converter's auto-generated metadata (required so schema sections
    # contributed by each interface, e.g. video ExternalVideos/Devices, are present), then
    # layer the static YAML and session-specific fields on top.
    metadata = converter.get_metadata()
    with open(_GENERAL_METADATA_YAML) as f:
        metadata = dict_deep_update(metadata, yaml.safe_load(f))

    if subject_metadata:
        metadata["Subject"] = dict_deep_update(metadata["Subject"], subject_metadata)
    else:
        metadata["Subject"]["subject_id"] = subject_id
        metadata["Subject"][
            "description"
        ] = f"Rat {rat_id}, cohort group {cohort}. Paired with {paired_rat_id} in this session."

    metadata["NWBFile"]["session_id"] = session_id
    metadata["NWBFile"]["session_start_time"] = session_date.isoformat()
    metadata["NWBFile"]["session_description"] = (
        f"{metadata['NWBFile']['session_description'].strip()} "
        f"Cohort group: {cohort}, encounter round: {encounter}, "
        f"session: {rat1_id} (rat1) vs {rat2_id} (rat2)."
    )

    # Inject skeleton edges and sDANNCE labels into Behavior/Pose metadata. Must include all
    # schema-required fields (name, nodes) so validate_metadata passes; add_to_nwbfile deep-merges
    # this with get_metadata() via DeepDict.deep_update (a key-for-key merge, not name-based), and
    # DANNCEInterface looks up the skeleton via PoseEstimations[pose_key]["skeleton_metadata_key"]
    # (which defaults to pose_key) -- so the override below MUST be keyed by pose_key itself (not
    # the Skeleton's descriptive "name" field) for edges to actually replace the empty default.
    skeleton_key = f"Skeleton{pose_key}_{f'rat{rat_idx}'.capitalize()}"
    behavior_pose = metadata.setdefault("Behavior", {}).setdefault("Pose", {})
    behavior_pose.setdefault("Skeletons", {})[pose_key] = {
        "name": skeleton_key,
        "nodes": SDANNCE_LANDMARK_NAMES,
        "edges": SDANNCE_SKELETON_EDGES,
    }
    behavior_pose.setdefault("PoseEstimations", {})[pose_key] = {
        "name": pose_key,
        "source_software": "sDANNCE",
        "scorer": "sDANNCE",
        "description": "3D keypoint coordinates estimated using sDANNCE (social DANNCE).",
    }

    # ── Run conversion ───────────────────────────────────────────────────────
    converter.run_conversion(
        nwbfile_path=nwbfile_path,
        metadata=metadata,
        conversion_options=conversion_options,
        overwrite=overwrite,
    )
    if verbose:
        print(f"Wrote {nwbfile_path}")

    return nwbfile_path


if __name__ == "__main__":
    from olveczky_lab_to_nwb.klibaite_2025_rat.utils.subject_metadata import get_subject_metadata

    data_dir = Path("H:/Olveczky-CN-data-share/ugne")
    output_dir = Path("H:/olveczky-nwbfiles")
    cohort = "ARID1B"
    encounter = "SOC1"
    session = "2022_10_17_M1_M2"
    session_dir = data_dir / cohort / f"{cohort}_{encounter}" / session
    contacts_file = data_dir / "social_touch" / f"{cohort}_{encounter}" / session / "skin_contacts_symmetric.h5"
    rat_log_path = data_dir / "ugne_rat_log.xlsx"

    subject_metadata = get_subject_metadata(rat_id="M1", cohort=cohort, rat_log_path=rat_log_path)

    session_to_nwb(
        session_dir_path=session_dir,
        output_dir_path=output_dir,
        rat_idx=1,
        cohort=cohort,
        encounter=encounter,
        subject_metadata=subject_metadata,
        contacts_file_path=contacts_file,
        stub_test=True,
        verbose=True,
    )
