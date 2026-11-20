"""Upload the converted NWB files to the draft of dandiset 000637 on the EMBER archive.

The dataset is behavioral only, so it goes to EMBER (https://dandi.emberarchive.org), which runs the DANDI archive
software: the DANDI client organizes, validates and uploads the files, with EMBER as its instance.

Uploading takes two steps, so that the organized files can be checked before anything is sent:

1. organize_nwbfiles copies the NWB files into a local dandiset folder, named and placed as DANDI expects
   (sub-<subject>/sub-<subject>_ses-<session>_image.nwb, with the 6 linked videos of each file in a folder of the
   same name). The NWB files in the conversion output folder are not changed. The two files of a session (one per
   rat) link the same videos, so each gets its own copy of them; DANDI stores identical files once.
2. upload_organized_files validates the organized files and the dandiset metadata, and uploads the folder to the
   draft of the dandiset if they are valid.

Before uploading, report_draft_assets lists the draft assets that the upload replaces, those it leaves next to a
new file of the same session (superseded) and those it does not touch (not reconverted).

Every function takes the instance: "ember-dandi" for the EMBER archive, "ember-dandi-sandbox" for its sandbox. EMBER
needs an API key, from the account page of that instance, to read a draft and to upload: in the EMBER_DANDI_API_KEY
environment variable for the archive, EMBER_DANDI_SANDBOX_API_KEY for the sandbox.
"""

import re
from pathlib import Path

import pandas as pd

DANDI_INSTANCES = ("ember-dandi", "ember-dandi-sandbox")


def check_dandi_instance(dandi_instance: str) -> None:
    """Raise if dandi_instance is not one of DANDI_INSTANCES."""
    if dandi_instance not in DANDI_INSTANCES:
        raise ValueError(f"Unknown DANDI instance {dandi_instance!r}; use one of {DANDI_INSTANCES}.")


def organize_nwbfiles(
    *,
    nwb_folder_path: str | Path,
    dandiset_folder_path: str | Path,
    dandiset_id: str,
    dandi_instance: str,
) -> Path:
    """Copy the NWB files of a folder into a local dandiset folder, organized as DANDI expects.

    The dandiset metadata (dandiset.yaml, no assets) of the draft is downloaded to
    dandiset_folder_path / dandiset_id, then dandi organize copies the NWB files there. The external video files
    are copied next to the NWB files that link them, and the links are updated. File names always have the session
    (sub-<subject>_ses-<session>), also for a subject with one file in the folder.

    Parameters
    ----------
    nwb_folder_path : str | Path
        Folder of the NWB files to upload, e.g. the output folder of convert_all_sessions.dataset_to_nwb. It is
        searched recursively and not changed. Stub files (nwb_stub/) must not be in it.
    dandiset_folder_path : str | Path
        Folder in which the dandiset folder is created.
    dandiset_id : str
        The dandiset, e.g. "000637".
    dandi_instance : str
        "ember-dandi" or "ember-dandi-sandbox".

    Returns
    -------
    Path
        The dandiset folder, dandiset_folder_path / dandiset_id.

    Raises
    ------
    FileExistsError
        If the dandiset folder already holds NWB files, from an earlier organize. Remove it first.
    """
    from dandi.consts import known_instances
    from dandi.download import download
    from dandi.organize import CopyMode, FileOperationMode, organize

    check_dandi_instance(dandi_instance)
    if any(Path(nwb_folder_path).rglob("nwb_stub")):
        raise ValueError(f"{nwb_folder_path} holds stub files (nwb_stub/). Organize the full files only.")
    dandiset_folder_path = Path(dandiset_folder_path)
    dandiset_path = dandiset_folder_path / dandiset_id
    if any(dandiset_path.rglob("*.nwb")):
        raise FileExistsError(f"{dandiset_path} already holds organized NWB files. Remove it before organizing again.")
    dandiset_folder_path.mkdir(parents=True, exist_ok=True)
    dandiset_url = f"{known_instances[dandi_instance].gui}/dandiset/{dandiset_id}/draft"
    download(urls=dandiset_url, output_dir=str(dandiset_folder_path), get_metadata=True, get_assets=False)
    if not (dandiset_path / "dandiset.yaml").exists():
        raise FileNotFoundError(f"Downloading the metadata of {dandiset_url} did not create {dandiset_path}.")
    organize(
        paths=[str(nwb_folder_path)],
        dandiset_path=str(dandiset_path),
        update_external_file_paths=True,
        files_mode=FileOperationMode.COPY,
        media_files_mode=CopyMode.COPY,
        required_fields=["session_id"],  # dandi organize leaves out the session of a subject's only file otherwise
    )
    return dandiset_path


def validate_organized_files(dandiset_path: str | Path) -> list[str]:
    """Validate the files of an organized dandiset folder and its dandiset metadata, as dandi upload does.

    The NWB files are checked against the NWB schema and the DANDI requirements (including the critical NWB
    Inspector checks), and dandiset.yaml against the DANDI metadata schema of the installed dandi client.

    Parameters
    ----------
    dandiset_path : str | Path
        The dandiset folder from organize_nwbfiles.

    Returns
    -------
    list[str]
        One line per validation error, "<file>: <message>"; empty if every file is valid.
    """
    from dandi.files import DandisetMetadataFile, find_dandi_files
    from dandi.validate import Severity
    from dandischema.models import get_schema_version

    errors = []
    for dandi_file in find_dandi_files(dandiset_path, dandiset_path=dandiset_path, include_metadata=True):
        # The draft's dandiset.yaml can state an older schema version, which dandi refuses to validate. NWB files
        # keep the default, as in dandi upload: with a schema version, dandi skips their NWB Inspector checks.
        schema_version = get_schema_version() if isinstance(dandi_file, DandisetMetadataFile) else None
        for result in dandi_file.get_validation_errors(schema_version=schema_version):
            if result.severity is not None and result.severity.value >= Severity.ERROR.value:
                errors.append(f"{dandi_file.filepath}: {result.message}")
    return errors


def get_draft_asset_paths(*, dandiset_id: str, dandi_instance: str) -> list[str]:
    """List the paths of the assets of the draft of a dandiset."""
    from dandi.dandiapi import DandiAPIClient

    check_dandi_instance(dandi_instance)
    with DandiAPIClient.for_dandi_instance(dandi_instance, authenticate=True) as client:
        return [asset.path for asset in client.get_dandiset(dandiset_id, "draft").get_assets()]


def get_subject_and_session(asset_path: str) -> tuple[str, str]:
    """Get the subject and session of an asset path, in lower case.

    For example "sub-SCN2A-M1/sub-SCN2A-M1_ses-social-1-20220922-M1-M2_image.nwb" and the external video
    "sub-SCN2A-M1/sub-SCN2A-M1_ses-social-1-20220922-M1-M2_image/<uuid>_external_file_0.mp4" both give
    ("scn2a-m1", "social-1-20220922-m1-m2").
    """
    subject = asset_path.split("/")[0].removeprefix("sub-")
    match = re.search(r"_ses-([^_/.]+)", asset_path)
    return subject.lower(), match.group(1).lower() if match else ""


def report_draft_assets(*, dandiset_path: str | Path, dandiset_id: str, dandi_instance: str) -> pd.DataFrame:
    """Compare an organized dandiset folder with the draft, before uploading it.

    Nothing is removed from the draft. Each draft asset gets a status:

    - "replaced": the organized folder has a file at the same path, which the upload replaces.
    - "superseded": the organized folder has a file of the same subject and session (compared in lower case) at
      another path. The upload adds the new file and the asset stays on the draft next to it until it is removed.
    - "not reconverted": the organized folder has no file of its subject and session.

    Each organized file that is not on the draft gets the status "new".

    Parameters
    ----------
    dandiset_path : str | Path
        The dandiset folder from organize_nwbfiles.
    dandiset_id : str
        The dandiset, e.g. "000637".
    dandi_instance : str
        "ember-dandi" or "ember-dandi-sandbox".

    Returns
    -------
    pd.DataFrame
        One row per asset, with columns "path", "status" and "replaced_by" (the organized NWB files of the same
        subject and session, for superseded assets).
    """
    dandiset_path = Path(dandiset_path)
    local_paths = sorted(
        file_path.relative_to(dandiset_path).as_posix()
        for file_path in dandiset_path.rglob("*")
        if file_path.is_file() and file_path.name != "dandiset.yaml"
    )
    subject_and_session_to_local_nwbfile_paths = dict()
    for local_path in local_paths:
        if local_path.endswith(".nwb"):
            subject_and_session_to_local_nwbfile_paths.setdefault(get_subject_and_session(local_path), []).append(
                local_path
            )
    draft_paths = get_draft_asset_paths(dandiset_id=dandiset_id, dandi_instance=dandi_instance)
    rows = []
    for draft_path in sorted(draft_paths):
        replaced_by = subject_and_session_to_local_nwbfile_paths.get(get_subject_and_session(draft_path), [])
        if draft_path in local_paths:
            rows.append(dict(path=draft_path, status="replaced", replaced_by=""))
        elif replaced_by:
            rows.append(dict(path=draft_path, status="superseded", replaced_by="; ".join(replaced_by)))
        else:
            rows.append(dict(path=draft_path, status="not reconverted", replaced_by=""))
    rows += [
        dict(path=local_path, status="new", replaced_by="")
        for local_path in sorted(set(local_paths) - set(draft_paths))
    ]
    return pd.DataFrame(rows, columns=["path", "status", "replaced_by"])


def upload_organized_files(*, dandiset_path: str | Path, dandi_instance: str) -> None:
    """Validate an organized dandiset folder and upload it to the draft of its dandiset.

    Nothing is uploaded if a file or the dandiset metadata is invalid (validate_organized_files).

    Parameters
    ----------
    dandiset_path : str | Path
        The dandiset folder from organize_nwbfiles.
    dandi_instance : str
        "ember-dandi" or "ember-dandi-sandbox", as for organize_nwbfiles.

    Raises
    ------
    ValueError
        If validation finds errors; the message lists them.
    """
    from dandi.upload import upload

    check_dandi_instance(dandi_instance)
    errors = validate_organized_files(dandiset_path)
    if errors:
        raise ValueError(f"{len(errors)} validation errors in {dandiset_path}, nothing uploaded:\n" + "\n".join(errors))
    upload(paths=[str(dandiset_path)], dandi_instance=dandi_instance)


if __name__ == "__main__":
    nwb_folder_path = Path("/path/to/nwbfiles")  # output folder of convert_all_sessions.py
    dandiset_folder_path = Path("/path/to/dandiset")  # the organized copy is written here
    dandiset_id = "000637"
    dandi_instance = "ember-dandi"  # "ember-dandi" for the EMBER archive, "ember-dandi-sandbox" for its sandbox
    # Set to True after checking the organized folder and the draft asset report printed below.
    upload = False

    dandiset_path = dandiset_folder_path / dandiset_id
    if not any(dandiset_path.rglob("*.nwb")):
        organize_nwbfiles(
            nwb_folder_path=nwb_folder_path,
            dandiset_folder_path=dandiset_folder_path,
            dandiset_id=dandiset_id,
            dandi_instance=dandi_instance,
        )
    report = report_draft_assets(dandiset_path=dandiset_path, dandiset_id=dandiset_id, dandi_instance=dandi_instance)
    print(report.to_string(index=False))

    if upload:
        upload_organized_files(dandiset_path=dandiset_path, dandi_instance=dandi_instance)
