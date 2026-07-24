# olveczky-lab-to-nwb

NWB conversion scripts, functions, and classes for the [Olveczky Lab](https://olveczkylab.oeb.harvard.edu/) (Harvard University), which studies the neural basis of learned and natural behaviors.

## Conversions

### Klibaite 2025 — Rat social behavior

Converts multi-genotype social behavior recordings of freely interacting rat pairs, as described in
[Klibaite et al. (2025), *Cell*](https://www.cell.com/cell/fulltext/S0092-8674(25)00154-0)
(DOI: [10.1016/j.cell.2025.01.044](https://doi.org/10.1016/j.cell.2025.01.044)).

Each session pairs two rats in an arena recorded from 6 synchronized cameras. Every session is
converted to **two NWB files**, one per rat, both referencing the same external video files.

Data streams converted:

- **3D pose estimation** — per-rat sDANNCE keypoints (23-joint `rat23` skeleton), via NeuroConv's
  `DANNCEConverter`, which also links each camera's video file and calibrated `Device`.
- **Multi-camera video** — 6 synchronized camera streams, stored as external-file `ImageSeries`.
- **Skin contacts** *(optional, when available)* — pairwise inter-rat body-contact events derived
  from the sDANNCE body mesh, written as an `EventsTable` in `nwbfile.events`.

All streams are temporally aligned using per-camera `frametimes.npy` files (elapsed seconds from
session start).

Code for this conversion is located at
[`src/olveczky_lab_to_nwb/klibaite_2025_rat`](src/olveczky_lab_to_nwb/klibaite_2025_rat), including:

- [`nwbconverter.py`](src/olveczky_lab_to_nwb/klibaite_2025_rat/nwbconverter.py) — the
  `Klibaite2025NWBConverter` class, combining the `DANNCE` and `SkinContacts` interfaces and
  handling temporal alignment.
- [`interfaces/skin_contacts_interface.py`](src/olveczky_lab_to_nwb/klibaite_2025_rat/interfaces/skin_contacts_interface.py) —
  custom `SkinContactsInterface` for the lab's `skin_contacts_symmetric.h5` files.
- [`convert_session.py`](src/olveczky_lab_to_nwb/klibaite_2025_rat/convert_session.py) — converts
  one rat from one session directory to one NWB file.
- [`convert_all_sessions.py`](src/olveczky_lab_to_nwb/klibaite_2025_rat/convert_all_sessions.py) —
  discovers all sessions under a data root and converts both rats of each session (two NWB files
  per session), resolving per-rat subject metadata along the way.
- [`general_metadata.yaml`](src/olveczky_lab_to_nwb/klibaite_2025_rat/general_metadata.yaml) —
  static NWBFile/Subject/device metadata.
- [`utils/`](src/olveczky_lab_to_nwb/klibaite_2025_rat/utils) — skeleton/landmark constants and
  per-rat subject metadata lookup (from the lab's rat log spreadsheet).
- [`documentation/conversion_notes.md`](src/olveczky_lab_to_nwb/klibaite_2025_rat/documentation/conversion_notes.md) —
  detailed notes on data streams, directory structure, and conversion decisions.

## Installation

Clone the repository and install in editable mode with the conversion-specific extra:

```bash
git clone https://github.com/catalystneuro/olveczky-lab-to-nwb
cd olveczky-lab-to-nwb
pip install -e ".[social_behavior]"
```

> **Note:** `DANNCEConverter` requires a version of `neuroconv` with DANNCE support. If it is not
> yet available on PyPI, install NeuroConv from the `main` branch:
>
> ```bash
> pip install "git+https://github.com/catalystneuro/neuroconv.git@main"
> ```

## Usage

Convert a single rat from a session (writes one NWB file):

```python
from olveczky_lab_to_nwb.klibaite_2025_rat.convert_session import session_to_nwb
from olveczky_lab_to_nwb.klibaite_2025_rat.utils.subject_metadata import get_subject_metadata
from pathlib import Path

rat_log_path = Path("/path/to/ugne_rat_log.xlsx")
subject_metadata = get_subject_metadata(rat_id="M1", cohort="SCN2A", rat_log_path=rat_log_path)

session_to_nwb(
    session_dir_path=Path("/path/to/2022_09_22_M1_M2"),
    output_dir_path=Path("/path/to/nwb_output"),
    rat_idx=1,
    cohort="SCN2A",
    encounter="SOC1",
    subject_metadata=subject_metadata,
    contacts_file_path=Path("/path/to/social_touch/.../skin_contacts_symmetric.h5"),
    stub_test=True,
)
```

Batch-convert all sessions under a data root (writes two NWB files per session, one per rat):

```bash
python -m olveczky_lab_to_nwb.klibaite_2025_rat.convert_all_sessions \
    --data_root  /path/to/ugne \
    --output_dir /path/to/nwb_output \
    --cohorts    SCN2A ARID1B \
    --rat_log_path /path/to/ugne_rat_log.xlsx
```

Drop `--stub_test` to run a full conversion.

## Repository structure

```text
src/olveczky_lab_to_nwb/
└── klibaite_2025_rat/
    ├── nwbconverter.py
    ├── convert_session.py
    ├── convert_all_sessions.py
    ├── general_metadata.yaml
    ├── interfaces/
    │   └── skin_contacts_interface.py
    ├── utils/
    │   ├── constants.py
    │   └── subject_metadata.py
    └── documentation/
        ├── conversion_notes.md
        └── project_track.md
```
