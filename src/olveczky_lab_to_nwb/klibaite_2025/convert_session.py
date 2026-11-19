"""Convert one rat of one session of the Klibaite 2025 dataset to NWB.

A session folder, <cohort>/<cohort>_SOC<N>/<YYYY_MM_DD>_M<a>_M<b>[_<suffix>]/, holds the recording of a pair
of rats; each rat becomes one NWB file, and both files link the same videos.
"""

import re
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from neuroconv.utils import dict_deep_update, load_dict_from_file

from olveczky_lab_to_nwb.klibaite_2025.nwbconverter import Klibaite2025NWBConverter
from olveczky_lab_to_nwb.klibaite_2025.utils.subject_metadata import get_subject_metadata

GENERAL_METADATA_PATH = Path(__file__).parent / "general_metadata.yaml"

# Metadata key of the pose in metadata["Pose"] (see general_metadata.yaml).
POSE_METADATA_KEY = "PoseEstimationSDANNCE"


def parse_session_folder(session_dir_path: str | Path) -> dict:
    """Read the date, rats and encounter of a session from its folder path.

    ``LONGEVANS/LONGEVANS_M_SOC7/2022_12_07_M2_M5_take2`` gives the rats ``("M2", "M5")``, encounter 7, suffix
    ``"take2"`` and session ID ``day-7-social-M2-M5-20221207-take2``. The session start time is the date at
    midnight in America/New_York: the time of day was not recorded.

    Raises
    ------
    ValueError
        If the folder is not a session folder of a social encounter.
    """
    session_dir_path = Path(session_dir_path)
    session_match = re.fullmatch(r"(\d{4})_(\d{2})_(\d{2})_(M\d+)_(M\d+)(?:_(\w+))?", session_dir_path.name)
    encounter_match = re.search(r"SOC(\d+)$", session_dir_path.parent.name)
    if session_match is None or encounter_match is None:
        raise ValueError(
            f"{session_dir_path} is not a session folder: expected <cohort>_SOC<N>/YYYY_MM_DD_M<a>_M<b>[_<suffix>]."
        )
    year, month, day, rat1_id, rat2_id, suffix = session_match.groups()
    encounter = int(encounter_match.group(1))
    session_id = f"day-{encounter}-social-{rat1_id}-{rat2_id}-{year}{month}{day}"
    if suffix:
        session_id += f"-{suffix.lower()}"
    return dict(
        session_id=session_id,
        session_start_time=datetime(int(year), int(month), int(day), tzinfo=ZoneInfo("America/New_York")),
        rat_ids=(rat1_id, rat2_id),
        encounter=encounter,
    )


def find_pose_file(session_dir_path: str | Path, rat_idx: int) -> Path:
    """Find the sDANNCE prediction file of a rat: SDANNCE*/bsl0.5_FM_rat<rat_idx>/save_data_AVG0.mat.

    Sessions keep it in SDANNCE/, SDANNCE_x2/ or SDANNCE_x3/; when several have it, the copies are the same and
    the first is used. Other prediction folders (test runs) and files (save_data_AVG.mat, which misses the last
    1000 frames) are not read.
    """
    pose_file_paths = sorted(Path(session_dir_path).glob(f"SDANNCE*/bsl0.5_FM_rat{rat_idx}/save_data_AVG0.mat"))
    if not pose_file_paths:
        raise FileNotFoundError(f"No SDANNCE*/bsl0.5_FM_rat{rat_idx}/save_data_AVG0.mat in {session_dir_path}.")
    return pose_file_paths[0]


def session_to_nwb(
    *,
    session_dir_path: str | Path,
    output_dir_path: str | Path,
    rat_idx: int,
    cohort: str,
    rat_log_path: str | Path,
    contacts_file_path: str | Path | None = None,
    stub_test: bool = False,
    overwrite: bool = False,
    verbose: bool = False,
) -> Path:
    """Convert one rat of one session to one NWB file.

    The file is written to <output_dir_path>/sub-<cohort>-<rat>/sub-<cohort>-<rat>_ses-<session_id>.nwb, or under
    <output_dir_path>/nwb_stub/ in stub mode.

    Parameters
    ----------
    session_dir_path : str or Path
        The session folder, e.g. .../ARID1B/ARID1B_SOC1/2022_10_17_M1_M2.
    output_dir_path : str or Path
        Folder of the NWB files.
    rat_idx : int
        1 for the first rat of the folder name (blue in the videos), 2 for the second (red).
    cohort : str
        Cohort folder name, a key of COHORTS in utils/subject_metadata.py.
    rat_log_path : str or Path
        Path to ugne_rat_log.xlsx.
    contacts_file_path : str or Path, optional
        Path to the session's skin_contacts_symmetric.h5. Without it the file has no skin contacts.
    stub_test : bool, default: False
        Write the first 100 pose samples and the first 1000 skin contacts only, to check the conversion quickly.
    overwrite : bool, default: False
        Replace an existing file. Otherwise an existing file is left as is and not converted again.
    verbose : bool, default: False

    Returns
    -------
    Path
        The NWB file.
    """
    session_dir_path = Path(session_dir_path)
    session = parse_session_folder(session_dir_path)
    rat_id = session["rat_ids"][rat_idx - 1]
    subject_metadata = get_subject_metadata(rat_id=rat_id, cohort=cohort, rat_log_path=rat_log_path)

    subject_id = subject_metadata["subject_id"]
    output_dir_path = Path(output_dir_path) / "nwb_stub" if stub_test else Path(output_dir_path)
    nwbfile_path = output_dir_path / f"sub-{subject_id}" / f"sub-{subject_id}_ses-{session['session_id']}.nwb"
    if nwbfile_path.exists() and not overwrite:
        print(f"Skipping {nwbfile_path.name}: the file exists.")
        return nwbfile_path

    general_metadata = load_dict_from_file(GENERAL_METADATA_PATH)
    videos_folder_path = session_dir_path / "videos"
    camera1_frametimes_path = videos_folder_path / "Camera1" / "frametimes.npy"
    source_data = dict(
        DANNCE=dict(
            file_paths=find_pose_file(session_dir_path, rat_idx),
            videos_folder_path=videos_folder_path,
            calibration_path=session_dir_path / "calibration",
            landmark_names=general_metadata["Pose"]["Skeletons"][POSE_METADATA_KEY]["nodes"],
            subject_name=subject_id,  # links the skeleton to the file's Subject
            metadata_key=POSE_METADATA_KEY,
        ),
        TaskEpoch=dict(
            frametimes_file_path=camera1_frametimes_path,
            camera_names=sorted(path.name for path in videos_folder_path.glob("Camera*")),
        ),
    )
    conversion_options = dict(DANNCE=dict(stub_test=stub_test))
    if contacts_file_path is not None:
        source_data["SkinContacts"] = dict(
            contacts_file_path=contacts_file_path, frametimes_file_path=camera1_frametimes_path
        )
        conversion_options["SkinContacts"] = dict(stub_test=stub_test)

    converter = Klibaite2025NWBConverter(source_data=source_data, verbose=verbose)

    metadata = dict_deep_update(converter.get_metadata(), general_metadata)
    metadata["Subject"].update(subject_metadata)
    metadata["Pose"]["Skeletons"][POSE_METADATA_KEY]["name"] = f"SkeletonPoseEstimationSDANNCE_Rat{rat_idx}"
    rat1_id, rat2_id = session["rat_ids"]
    metadata["NWBFile"].update(
        session_id=session["session_id"],
        session_start_time=session["session_start_time"],
        session_description=(
            f"{metadata['NWBFile']['session_description'].strip()} Cohort: {cohort}, encounter round "
            f"{session['encounter']}, rats {rat1_id} (rat1, blue) and {rat2_id} (rat2, red). This file is {rat_id}."
        ),
    )

    nwbfile_path.parent.mkdir(parents=True, exist_ok=True)
    converter.run_conversion(
        nwbfile_path=nwbfile_path, metadata=metadata, conversion_options=conversion_options, overwrite=True
    )
    if verbose:
        print(f"Wrote {nwbfile_path}")
    return nwbfile_path


if __name__ == "__main__":
    data_dir_path = Path("/path/to/ugne")  # the ugne/ folder of the data share
    output_dir_path = Path("/path/to/nwbfiles")
    session_dir_path = data_dir_path / "ARID1B" / "ARID1B_SOC1" / "2022_10_17_M1_M2"

    session_to_nwb(
        session_dir_path=session_dir_path,
        output_dir_path=output_dir_path,
        rat_idx=1,
        cohort="ARID1B",
        rat_log_path=data_dir_path / "ugne_rat_log.xlsx",
        contacts_file_path=data_dir_path
        / "social_touch"
        / session_dir_path.parent.name
        / session_dir_path.name
        / "skin_contacts_symmetric.h5",
        stub_test=True,
        overwrite=True,
        verbose=True,
    )
