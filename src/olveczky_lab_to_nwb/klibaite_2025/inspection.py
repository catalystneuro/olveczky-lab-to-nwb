"""Inspect converted NWB files with NWB Inspector and validate their HED annotations.

convert_all_sessions.py writes the NWB files to <output folder>/sub-<subject>/. For each of them,
inspect_output_folder saves an NWB Inspector report, inspector_reports/<file stem>.txt in the output folder, and
writes inspection_summary.csv to the output folder, with one row per NWB file: its subject and session, the number
of inspector messages per importance level, the number of HERD references (the ontology terms stated under
ExternalResources in general_metadata.yaml) and the number of HED validation errors.

The DANDI configuration of NWB Inspector is used, the same checks dandi upload runs. A file with CRITICAL messages
cannot be uploaded.
"""

from pathlib import Path

import pandas as pd

INSPECTOR_REPORT_FOLDER_NAME = "inspector_reports"
INSPECTION_SUMMARY_FILE_NAME = "inspection_summary.csv"
IMPORTANCE_LEVELS = ["ERROR", "PYNWB_VALIDATION", "CRITICAL", "BEST_PRACTICE_VIOLATION", "BEST_PRACTICE_SUGGESTION"]


def inspect_nwbfile_and_save_report(nwbfile_path: str | Path, report_folder_path: str | Path) -> dict[str, int]:
    """Run NWB Inspector with the DANDI configuration on one NWB file and save its report.

    Parameters
    ----------
    nwbfile_path : str or Path
        Path to the NWB file.
    report_folder_path : str or Path
        Folder of the report, <file stem>.txt. An earlier report of the same file is replaced.

    Returns
    -------
    dict[str, int]
        The number of inspector messages per importance level of IMPORTANCE_LEVELS.
    """
    from nwbinspector import format_messages, inspect_nwbfile, load_config, save_report

    nwbfile_path = Path(nwbfile_path)
    report_folder_path = Path(report_folder_path)
    messages = list(inspect_nwbfile(nwbfile_path=nwbfile_path, config=load_config("dandi")))
    report_folder_path.mkdir(parents=True, exist_ok=True)
    save_report(
        report_file_path=report_folder_path / f"{nwbfile_path.stem}.txt",
        formatted_messages=format_messages(messages, levels=["importance", "check_function_name"]),
        overwrite=True,
    )
    return {level: sum(message.importance.name == level for message in messages) for level in IMPORTANCE_LEVELS}


def read_and_validate_nwbfile(nwbfile_path: str | Path) -> dict:
    """Read the subject, session and number of HERD references of an NWB file, and validate its HED.

    The HED of the task (the HED column of the task table) and of the skin contact types (the meanings table of
    the SkinContacts table) is validated with ndx-hed's HedNWBValidator against the file's HED schema and
    definitions. The task table is not validated as a whole: the validator does not read its camera_id cell,
    which holds several values. The skin contacts are validated by distinct contact type (assemble=False), which
    does not read the millions of rows.

    Returns
    -------
    dict
        "subject_id", "session_id", "herd_references" and "hed_errors" (the HED validation errors, warnings
        such as the tag extensions of general_metadata.yaml are not counted).
    """
    from ndx_hed.utils.hed_nwb_validator import HedNWBValidator
    from pynwb import NWBHDF5IO

    with NWBHDF5IO(nwbfile_path, "r") as io:
        nwbfile = io.read()
        validator = HedNWBValidator(nwbfile.lab_meta_data["hed_schema"])
        hed_issues = validator.validate_vector(nwbfile.processing["tasks"]["task_table"]["HED"])
        if nwbfile.events is not None and "SkinContacts" in nwbfile.events:
            hed_issues += validator.validate_table(nwbfile.events["SkinContacts"], assemble=False)
        external_resources = nwbfile.external_resources
        return dict(
            subject_id=nwbfile.subject.subject_id,
            session_id=nwbfile.session_id,
            herd_references=0 if external_resources is None else len(external_resources.to_dataframe()),
            hed_errors=len(hed_issues),
        )


def inspect_output_folder(output_dir_path: str | Path) -> pd.DataFrame:
    """Inspect every NWB file of a conversion output folder and write the inspection summary.

    The NWB files are those in the subject folders, <output folder>/sub-*/*.nwb; stub files (in nwb_stub/) are
    left out. The reports go to <output folder>/inspector_reports/ and the summary to
    <output folder>/inspection_summary.csv, both replacing earlier ones.

    Parameters
    ----------
    output_dir_path : str or Path
        The output folder of convert_all_sessions.dataset_to_nwb.

    Returns
    -------
    pd.DataFrame
        The summary, one row per NWB file.
    """
    output_dir_path = Path(output_dir_path)
    nwbfile_paths = sorted(output_dir_path.glob("sub-*/*.nwb"))
    if not nwbfile_paths:
        raise FileNotFoundError(f"No NWB files found in {output_dir_path}/sub-*/.")

    report_folder_path = output_dir_path / INSPECTOR_REPORT_FOLDER_NAME
    rows = []
    for nwbfile_path in nwbfile_paths:
        print(f"Inspecting {nwbfile_path.name}")
        rows.append(
            dict(
                nwbfile_name=nwbfile_path.name,
                **read_and_validate_nwbfile(nwbfile_path),
                **inspect_nwbfile_and_save_report(nwbfile_path, report_folder_path),
            )
        )
    summary = pd.DataFrame(rows)
    summary.to_csv(output_dir_path / INSPECTION_SUMMARY_FILE_NAME, index=False)
    return summary


if __name__ == "__main__":
    output_dir_path = Path("/path/to/nwbfiles")  # output folder of convert_all_sessions.py

    summary = inspect_output_folder(output_dir_path)
    print(summary.to_string(index=False))
    print(f"Reports in {output_dir_path / INSPECTOR_REPORT_FOLDER_NAME}")
