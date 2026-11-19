# Converting sessions

Each rat of a session becomes one NWB file, `sub-<cohort>-<rat>/sub-<cohort>-<rat>_ses-<session_id>.nwb`, so a
session gives two files that link the same videos. Sessions are converted with the scripts of the package (see the
[README](../../../../README.md#installation) to install it). Run them from the conda environment of the package:

```bash
conda activate olveczky-lab-to-nwb-env
```

Each script has an `if __name__ == "__main__":` block at the bottom with placeholder paths: the `ugne/` folder of the
data share (see [Data organization](data_organization.md)) and an output folder for the NWB files and reports. Edit
them, then run the file.

Keep the output folder on the same drive as the data share. The NWB files link the videos by a path relative to the
file, which is not possible across drives.

## 1. Convert one session as a stub

In `convert_session.py`, set `data_dir_path`, `output_dir_path` and the session, keep `stub_test=True`, and run:

```bash
python src/olveczky_lab_to_nwb/klibaite_2025/convert_session.py
```

A stub file holds the first 100 pose samples and the first 1000 skin contacts, and is written to
`<output folder>/nwb_stub/`. The videos are linked in full. It is a quick way to check the metadata after a change.

## 2. Convert all sessions

In `convert_all_sessions.py`, set `data_dir_path` and `output_dir_path`, and run:

```bash
python src/olveczky_lab_to_nwb/klibaite_2025/convert_all_sessions.py
```

This converts both rats of every session folder of the cohorts in `COHORTS` (`utils/subject_metadata.py`); pass
`cohorts=["SCN2A"]` to `dataset_to_nwb` to convert some cohorts only. With `overwrite=False` (the default in the
script), rat-sessions whose NWB file exists are skipped, which converts only new sessions after recordings are added
to the share; set `overwrite=True` to convert everything again, for example after changing the metadata.

`max_workers` sets how many rat-sessions are converted in parallel. Time, memory and file size grow with the number
of skin contacts of the session. Measured on the data share (a mounted network drive):

| Session | Contacts file | Time | Peak memory | NWB file |
| --- | --- | --- | --- | --- |
| `ARID1B_SOC2/2022_10_25_M5_M12` | 0.39 GB (16 million contacts) | 11 min | 5 GB | 0.9 GB |
| `NRXN1_SOC2/2022_12_07_M4_M8`, the largest | 1.45 GB | 32 min | 18 GB | 3.3 GB |

Half of the contacts files are under 0.29 GB, and the largest are in NRXN1. On a machine with 32 GB, use
`max_workers=2` (the script's setting), and `max_workers=1` for NRXN1.

A rat-session that fails does not stop the others: its arguments and traceback are written to
`<output folder>/exceptions/ERROR_<encounter folder>_<session folder>_rat<1 or 2>.txt`, and removed when the
rat-session converts on a later run. The sessions that fail on the current data share, and why, are listed in
[Excluded sessions](excluded_sessions.md).

## 3. Inspect

In `inspection.py`, set `output_dir_path`, and run:

```bash
python src/olveczky_lab_to_nwb/klibaite_2025/inspection.py
```

This runs NWB Inspector with the DANDI configuration on every `<output folder>/sub-*/*.nwb` file (stubs are left
out), validates the HED annotations, and writes:

- `inspector_reports/<file name>.txt`: the report of each file.
- `inspection_summary.csv`: one row per file, with its subject and session, `herd_references` (the number of
  ontology references in the file), `hed_errors` and the number of inspector messages per importance level.

A file with `CRITICAL` messages cannot be uploaded to DANDI. `hed_errors` should be 0. Each file is expected to have
16 `BEST_PRACTICE_SUGGESTION`s and nothing else: missing descriptions of the camera devices and model, and the
`tasks` processing module and its single-row tables, which are in the layout Spyglass reads. A file converted to
another drive than the data share also has one `BEST_PRACTICE_VIOLATION` per camera, as its video paths are absolute.

## 4. Upload to DANDI

The files go to [DANDI:001936](https://dandiarchive.org/dandiset/001936). Uploading needs the
[DANDI client](https://dandi.readthedocs.io/) (installed with the package) and a DANDI API key, from your account page
on DANDI, in the `DANDI_API_KEY` environment variable.

In `upload_to_DANDI.py`, set `nwb_folder_path` (the output folder) and `dandiset_folder_path` (an empty folder for
the organized copy, on a drive with room for the files and the videos), and run it once with `upload = False`:

```bash
python src/olveczky_lab_to_nwb/klibaite_2025/upload_to_DANDI.py
```

This copies the NWB files into `<dandiset folder>/001936/`, named as DANDI expects, with each file's videos in a
folder next to it, and prints how the upload would change the draft: files replaced, new, superseded (an older file
of the same subject and session at another path) or not reconverted. When the report is as expected, set
`upload = True` and run it again: it validates the files and uploads them. The two files of a session each get a copy
of the videos; DANDI stores identical files once.

Set `dandi_instance = "dandi-sandbox"` (and a sandbox dandiset ID) to try an upload on the
[DANDI sandbox](https://sandbox.dandiarchive.org) first. Superseded files stay on the draft until they are deleted on
the DANDI website.

## Output folder

```text
<output folder>/
├── sub-SCN2A-M1/
│   ├── sub-SCN2A-M1_ses-day-1-social-M1-M2-20220922.nwb
│   └── ...
├── nwb_stub/                 stub files
├── exceptions/               one file per failed rat-session
├── inspector_reports/
└── inspection_summary.csv
```

## Converting from Python

```python
from pathlib import Path

from olveczky_lab_to_nwb.klibaite_2025.convert_all_sessions import dataset_to_nwb
from olveczky_lab_to_nwb.klibaite_2025.convert_session import session_to_nwb
from olveczky_lab_to_nwb.klibaite_2025.inspection import inspect_output_folder

data_dir_path = Path("<data share>/ugne")
output_dir_path = Path("<output folder>")

# One rat of one session
session_dir_path = data_dir_path / "SCN2A" / "SCN2A_SOC1" / "2022_09_22_M1_M2"
session_to_nwb(
    session_dir_path=session_dir_path,
    output_dir_path=output_dir_path,
    rat_idx=1,
    cohort="SCN2A",
    rat_log_path=data_dir_path / "ugne_rat_log.xlsx",
    contacts_file_path=data_dir_path / "social_touch" / "SCN2A_SOC1" / "2022_09_22_M1_M2" / "skin_contacts_symmetric.h5",
    stub_test=True,
)

# All sessions of one cohort, then the inspection
dataset_to_nwb(data_dir_path=data_dir_path, output_dir_path=output_dir_path, cohorts=["SCN2A"], max_workers=2)
summary = inspect_output_folder(output_dir_path)
```

`get_session_to_nwb_kwargs_per_session` in `convert_all_sessions.py` returns the arguments of every rat-session, as
`dataset_to_nwb` uses them.

## Tests

`tests/` checks how session folders are read (session IDs, which prediction file is used). Run it with:

```bash
pip install pytest
pytest tests
```
