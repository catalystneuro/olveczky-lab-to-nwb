"""Convert one rat of one session of the Klibaite 2025 dataset to NWB.

A social session holds a pair of rats, and each rat becomes one NWB file; both files link the same videos. A lone
session holds one rat alone in the arena, and becomes one NWB file. See docs/data_organization.md for the folders.
"""

from pathlib import Path

from neuroconv.utils import dict_deep_update, load_dict_from_file

from olveczky_lab_to_nwb.klibaite_2025.nwbconverter import Klibaite2025NWBConverter
from olveczky_lab_to_nwb.klibaite_2025.utils.session_folders import (
    find_pose_file,
    get_fx_rat_order,
    parse_session_folder,
)
from olveczky_lab_to_nwb.klibaite_2025.utils.subject_metadata import get_subject_metadata

GENERAL_METADATA_PATH = Path(__file__).parent / "general_metadata.yaml"

# Metadata key of the pose in metadata["Pose"] (see general_metadata.yaml).
POSE_METADATA_KEY = "PoseEstimationSDANNCE"


def session_to_nwb(
    *,
    session_dir_path: str | Path,
    output_dir_path: str | Path,
    condition: str,
    cohort: str,
    rat_log_path: str | Path,
    rat_idx: int = 1,
    contacts_file_path: str | Path | None = None,
    stub_test: bool = False,
    overwrite: bool = False,
    verbose: bool = False,
) -> Path:
    """Convert one rat of one session to one NWB file.

    The file is written to <output_dir_path>/sub-<cohort>-<rat>/sub-<cohort>-<rat>_ses-<session_id>.nwb, or under
    <output_dir_path>/nwb_stub/ in stub mode. The session ID is ``social-<round>-<YYYYMMDD>[-<take>]-<rat a>-<rat b>``,
    the same for both rats of a social session, or ``lone-<YYYYMMDD>-<rat>`` (see parse_session_folder in
    utils/session_folders.py).

    Parameters
    ----------
    session_dir_path : str or Path
        The session folder, e.g. .../ARID1B/ARID1B_SOC1/2022_10_17_M1_M2 or .../FX/FXmale_wk1/2021_12_04_M1.
    output_dir_path : str or Path
        Folder of the NWB files.
    condition : {"social", "lone"}
        "social" for a pair of rats, "lone" for one rat alone in the arena.
    cohort : str
        Cohort folder name, a key of COHORTS in utils/subject_metadata.py.
    rat_log_path : str or Path
        Path to ugne_rat_log.xlsx.
    rat_idx : int, default: 1
        Social sessions: 1 for the blue rat, 2 for the red rat. The blue rat is the first rat of the folder name,
        except in FX, where it comes from the rat log (see get_fx_rat_order). Lone sessions: 1.
    contacts_file_path : str or Path, optional
        Path to the social session's skin_contacts_symmetric.h5. Without it the file has no skin contacts.
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
    session = parse_session_folder(session_dir_path, condition=condition)
    rat_ids = session["rat_ids"]
    if condition == "social" and cohort == "FX":
        rat_ids = get_fx_rat_order(session_dir_path=session_dir_path, rat_log_path=rat_log_path)
    rat_id = rat_ids[rat_idx - 1]
    subject_metadata = get_subject_metadata(rat_id=rat_id, cohort=cohort, rat_log_path=rat_log_path)

    subject_id = subject_metadata["subject_id"]
    output_dir_path = Path(output_dir_path) / "nwb_stub" if stub_test else Path(output_dir_path)
    nwbfile_path = output_dir_path / f"sub-{subject_id}" / f"sub-{subject_id}_ses-{session['session_id']}.nwb"
    if nwbfile_path.exists() and not overwrite:
        print(f"Skipping {nwbfile_path.name}: the file exists.")
        return nwbfile_path

    general_metadata = load_dict_from_file(GENERAL_METADATA_PATH)
    general_metadata = dict_deep_update(general_metadata, general_metadata.pop("Conditions")[condition])

    videos_folder_path = session_dir_path / "videos"
    camera1_frametimes_path = videos_folder_path / "Camera1" / "frametimes.npy"
    pose_file_path, animal_index = find_pose_file(session_dir_path, condition=condition, cohort=cohort, rat_idx=rat_idx)
    source_data = dict(
        DANNCE=dict(
            file_paths=pose_file_path,
            animal_index=animal_index,
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
    if condition == "social":
        rats = f"rats {rat_ids[0]} (rat1, blue) and {rat_ids[1]} (rat2, red). This file is {rat_id}."
    else:
        rats = f"rat {rat_id}."
    metadata["NWBFile"].update(
        session_id=session["session_id"],
        session_start_time=session["session_start_time"],
        session_description=(
            f"{metadata['NWBFile']['session_description'].strip()} Cohort: {cohort}, {session['encounter']}, {rats}"
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
    rat_log_path = data_dir_path / "ugne_rat_log.xlsx"

    # A social session: one file per rat (rat_idx 1 and 2), with the session's skin contacts.
    session_dir_path = data_dir_path / "ARID1B" / "ARID1B_SOC1" / "2022_10_17_M1_M2"
    session_to_nwb(
        session_dir_path=session_dir_path,
        output_dir_path=output_dir_path,
        condition="social",
        cohort="ARID1B",
        rat_log_path=rat_log_path,
        rat_idx=1,
        contacts_file_path=data_dir_path
        / "social_touch"
        / session_dir_path.parent.name
        / session_dir_path.name
        / "skin_contacts_symmetric.h5",
        stub_test=True,
        overwrite=True,
        verbose=True,
    )

    # A lone session: one rat alone in the arena.
    session_to_nwb(
        session_dir_path=data_dir_path / "FX" / "FXmale_wk1" / "2021_12_04_M1",
        output_dir_path=output_dir_path,
        condition="lone",
        cohort="FX",
        rat_log_path=rat_log_path,
        stub_test=True,
        overwrite=True,
        verbose=True,
    )
