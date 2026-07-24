# Conversion Notes — Olveczky Lab (Klibaite 2025 — Rat social behavior)

## Project Overview

Conversion of multi-genotype social behavior recordings from the Olveczky Lab (Harvard
University) to NWB, as described in
[Klibaite et al. (2025), *Cell*](https://www.cell.com/cell/fulltext/S0092-8674(25)00154-0)
(DOI: [10.1016/j.cell.2025.01.044](https://doi.org/10.1016/j.cell.2025.01.044)). Two rats of
defined genotype are placed together in an arena and recorded with six synchronized cameras;
3D pose is estimated per rat using sDANNCE (social DANNCE). The behavioral setup overlaps
substantially with the Uchida lab conversion (same facility; see `uchida-lab-to-nwb`).

- **Lab POC:** Lily Cao. **Data contact:** Ugne Klibaite (`ugne/` folder in the data share).
- **PI:** Prof. Bence Olveczky, Harvard University.
- **Repo:** <https://github.com/catalystneuro/olveczky-lab-to-nwb>
- **Genotype groups:** SCN2A, ARID1B, CHD8, GRIN2B ("GRINB"), NRXN1, and Long-Evans WT.
- **Downstream target:** DANDI Archive (public — this is a published line) + Spyglass ingestion
  (PoseEstimation via ndx-pose, ImageSeries external links).
- **Publication:** Klibaite U, Li T, Aldarondo D, Alkoad J, Olveczky B, Dunn T, Cao L. Mapping the
  landscape of social behavior. *Cell.* 2025. doi:10.1016/j.cell.2025.01.044
- **SFARI funding:** grant 272165.
- Electrophysiology (flexible probes, Neuropixels, tetrodes) and fiber photometry are planned by
  the lab but not yet present in the data share — see Open Questions/TODOs.

## Data Streams

| Stream | Format | File Pattern | NeuroConv Interface |
|---|---|---|---|
| 3D pose estimation (per rat) | sDANNCE `.mat`, single-animal 3D format | `SDANNCE(_x2)/bsl0.5_FM_rat{N}/save_data_AVG.mat` | `DANNCEConverter` (neuroconv), one call per rat |
| Multi-camera video (6 cameras) | `.mp4` per camera, external file | `videos/Camera{1..6}/0.mp4` | via `DANNCEConverter` (linked automatically, shared across both rats' NWB files) |
| Camera calibration | `.mat` per camera | `calibration/hires_cam{N}_params.mat` | via `DANNCEConverter` (`calibration_path`) — writes calibrated `Device`s |
| Video frame times | `.npy`, shape `(2, n_frames)` | `videos/Camera1/frametimes.npy` | used to index skin-contact event timestamps only (DANNCE/video use their own internal timestamp logic) |
| Skin contacts *(optional, when available)* | `.h5` | `social_touch/<cohort>_<encounter>/<session>/skin_contacts_symmetric.h5` | `SkinContactsInterface` (custom) → `EventsTable` in `nwbfile.events` |
| Subject metadata | XLSX (lab rat log) | `ugne_rat_log.xlsx` (one sheet per cohort) | `Subject`, via `utils/subject_metadata.get_subject_metadata()` |

Not converted / not yet in the data share:
- **Center of mass** (`COM/predict{00,01}/com3d*.mat`) — redundant with sDANNCE keypoints, not written to NWB.
- **STAC skeleton fit** (`stac/`, SCN2A only) — intermediate model-fitting artifact, not converted.
- **Experiment config** (`io.yaml`) — DANNCE pipeline config, not lab/session metadata.
- **Electrophysiology** (flexible probes, Neuropixels, tetrodes) and **fiber photometry** — planned by the lab, not yet collected/shared.

## Directory Structure

Raw data share (`ugne/` folder, e.g. mounted at `H:/Olveczky-CN-data-share/ugne/`):

```text
ugne/
├── ARID1B/
│   ├── ARID1B_SOC1/                        # encounter round 1
│   ├── ARID1B_SOC2/
│   └── ARID1B_SOC3/
├── SCN2A/
│   ├── SCN2A_SOC1/
│   ├── SCN2A_SOC2/
│   └── SCN2A_SOC3/
├── ugne_rat_log.xlsx                       # per-cohort sheet: Strain, Rat ID, DOB, Markings, Cage, Mother, Genotype
└── social_touch/                           # skin_contacts .h5 files only, for ALL cohorts
    ├── ARID1B_SOC1/
    ├── SCN2A_SOC1/
    ├── CHD8_SOC1/
    ├── GRINB_SOC1/
    ├── NRXN1_SOC1/
    └── LONGEVANS_M_SOC{6,7,8}/

Per session folder (e.g. 2022_09_22_M1_M2/):
├── videos/
│   └── Camera{1..6}/
│       ├── 0.mp4
│       ├── frametimes.npy                 # shape (2, n_frames): row 0 = frame index, row 1 = elapsed seconds
│       └── metadata.csv                   # frameRate, totalFrames, frameWidth/Height, cameraMake/Model
├── calibration/
│   └── hires_cam{1..6}_params.mat         # K, r, t, RDistort, TDistort per camera
├── SDANNCE/  (SCN2A)  or  SDANNCE_x2/  (ARID1B)
│   ├── bsl0.5_FM_rat1/
│   │   └── save_data_AVG.mat              # ~115 MB, per-rat pose (see below)
│   └── bsl0.5_FM_rat2/
│       └── save_data_AVG.mat
└── [only in social_touch/<cohort>_<encounter>/<session>/: skin_contacts_symmetric.h5]
```

Repository (`src/olveczky_lab_to_nwb/klibaite_2025_rat/`):

```text
klibaite_2025_rat/
├── nwbconverter.py              # Klibaite2025NWBConverter — DANNCE + SkinContacts interfaces
├── convert_session.py           # session_to_nwb() — one rat, one NWB file
├── convert_all_sessions.py      # discovers sessions, resolves subject metadata, converts both rats per session
├── general_metadata.yaml        # static NWBFile/Subject metadata
├── interfaces/
│   └── skin_contacts_interface.py   # SkinContactsInterface (custom, subclasses BaseEventsInterface)
├── utils/
│   ├── constants.py              # rat23 skeleton: 23 landmark names + 23 edges
│   └── subject_metadata.py       # STRAINS dict + get_subject_metadata() (reads ugne_rat_log.xlsx)
└── documentation/
    ├── conversion_notes.md        # this file
    ├── project_track.md           # conversion progress tracker
    └── metadata_request_email.md  # metadata request sent to the lab (2026-04-21) and reply
```

Each session folder is shared by both rats; `convert_session.py::session_to_nwb()` converts one
rat (selected via `rat_idx`) to one NWB file, and `convert_all_sessions.py` calls it twice per
session (once per rat) so both NWB files reference the same external video files.

## File Inventory & Counts

- **Cohorts with full data** (video + calibration + sDANNCE + skin contacts): **SCN2A** (SOC1–3),
  **ARID1B** (SOC1–3).
- **Cohorts with skin contacts only** (no video/sDANNCE in share yet): **CHD8, GRINB, NRXN1,
  LONGEVANS** — `social_touch/<cohort>_SOC{N}/` folders exist, but `convert_all_sessions.py`'s
  `DEFAULT_COHORTS` only includes `SCN2A`/`ARID1B` until full data lands.
- Roughly 10–30 sessions per cohort × encounter round; each session = 2 NWB files (one per rat).
- ARID1B uses `SDANNCE_x2/` (two-rat simultaneous fit); SCN2A uses `SDANNCE/bsl0.5_FM_rat{N}/`.
  `find_sdannce_mat()` in `convert_session.py` searches both folder-name variants.

## Sessions / Subjects

- **Session folder naming:** `YYYY_MM_DD_M{rat1_id}_M{rat2_id}` (e.g. `2022_09_22_M1_M2`),
  parsed by `parse_session_folder_name()`. Multiple encounter rounds (SOC1, SOC2, SOC3) are
  repeat pairings of the same or different rats across days.
- **Species / strain:** *Rattus norvegicus*; Long-Evans background for all cohorts, including KO
  lines (confirmed by lab, 2026-04-29). Per-cohort strain/supplier/RRID lookup table is in
  `utils/subject_metadata.py::STRAINS`.
- **Subject IDs:** `f"{cohort}-{rat_id}"` (e.g. `"SCN2A-M1"`); `rat_id` (e.g. `"M1"`) is unique
  within a cohort, not globally.
- **Per-rat metadata source:** `ugne_rat_log.xlsx`, one sheet per cohort, two-row header
  (banner + column names): `Rat ID`, `DOB`, `Genotype`, `Markings`, `Cage`, `Mother`. Read by
  `utils/subject_metadata.get_subject_metadata(rat_id, cohort, rat_log_path)`.
- **Weight:** not available per-rat in any source seen so far (approximate range 350–600 g from
  the paper, not written to NWB).
- **Sex:** not present in the rat log; `get_subject_metadata()` currently hardcodes `"U"`
  (unknown) — see Open Questions.

## Existing Resources

- **Publication:** Klibaite et al. (2025), *Cell*, doi:10.1016/j.cell.2025.01.044.
- **Harvard Dataverse:** <https://dataverse.harvard.edu/dataverse/socialDANNCE_data>
- **Data source:** Google Drive share (`ugne/` folder), mounted locally (e.g.
  `H:/Olveczky-CN-data-share/ugne/`); also accessible via `rclone` (`--drive-shared-with-me`).
  
## Interface Mapping

| Interface | Writes | Notes |
|---|---|---|
| `DANNCEConverter` (neuroconv, ×1 per rat) | `PoseEstimation` (ndx-pose) + 6 `ImageSeries` (external video) + calibrated `Device`s | Reads the per-rat, single-animal `save_data_AVG.mat` (3D `pred` array, shape `(n_frames, 3, 23)` — NOT the 4D multi-animal format `SDANNCEInterface` expects). Skeleton (`SDANNCE_LANDMARK_NAMES`/`SDANNCE_SKELETON_EDGES` from `utils/constants.py`) is injected into `Behavior/Pose` metadata at conversion time (`session_to_nwb()`), keyed per rat (`SkeletonPoseEstimationSDANNCE_Rat{N}`). |
| `SkinContactsInterface` (custom, `BaseEventsInterface`) | Shared `SkinContacts` `EventsTable` in `nwbfile.events` | One event type per unique `(rat1_body_part, rat2_body_part)` pair (e.g. `"right foot x left toe"`), with `frame_index`/`rat1_vertex`/`rat2_vertex` columns. Vertex indices reference the 6880-vertex STAC body mesh; body-part labels are humanized from the raw `walker/<part>_{L,R}` format. Timestamps come from `frametimes.npy` row 1, indexed by the contact event's frame. Written once per session (referenced identically from both rats' NWB files). |

`Klibaite2025NWBConverter` (`nwbconverter.py`) registers two interface slots: `DANNCE` and
`SkinContacts` (the latter only present when a contacts file exists for the session).
`convert_session.py::session_to_nwb()` builds `source_data`/`conversion_options` for one rat and
runs the conversion; `convert_all_sessions.py` discovers all sessions under a data root, resolves
each rat's subject metadata via `get_subject_metadata()` (with a warning fallback if a rat is
missing from the log), and calls `session_to_nwb()` twice per session.

Dependencies (`pyproject.toml`, `[social_behavior]` extra): `neuroconv` (DANNCE support currently
requires installing from `main`, not yet on PyPI), `ndx-pose>=0.4.0`, `scipy`, `h5py`, `numpy`,
`pandas`, `openpyxl`, `python-dateutil`, `opencv-python-headless`.

## Metadata

- **`general_metadata.yaml`**: static `NWBFile` fields (experiment/session description,
  institution, lab, `related_publications`, full experimenter list, keywords) and a placeholder
  `Subject.species`; all other `Subject` fields (`strain`, `sex`, `subject_id`, `date_of_birth`,
  `genotype`) are set programmatically from `ugne_rat_log.xlsx` via `get_subject_metadata()`
  (falling back to a minimal `subject_id`/`description` if the rat log lookup fails or is not
  provided).
- **`utils/constants.py`**: `SDANNCE_LANDMARK_NAMES` (23 rat23 joints: Snout, EarL/R, Spine{F,M,L},
  TailBase, Shoulder/Elbow/Wrist/Hand ×2, Hip/Knee/Ankle/Foot ×2) and `SDANNCE_SKELETON_EDGES` (23
  edges, from `diegoaldarondo/Label3D`'s `rat23.mat`, converted from 1- to 0-based indices).
- **`utils/subject_metadata.py`**: `STRAINS` dict (per-cohort strain/supplier/RRID, from the paper
  and lab correspondence) and `get_subject_metadata(rat_id, cohort, rat_log_path)`, which reads
  the matching sheet of `ugne_rat_log.xlsx` and returns `subject_id`, `sex` (currently always
  `"U"`), `date_of_birth`, `strain`, `genotype`, `description`.

## Temporal Alignment

Single-clock design per session — every stream derives from the shared per-camera
`frametimes.npy` (elapsed seconds from session start):

```text
Reference clock:   Camera1 frametimes.npy row 1 (elapsed seconds), 50 fps, 90000 frames (~30 min)
Video (6 cameras): each camera's own frametimes.npy, linked internally by DANNCEConverter
sDANNCE pose:      DANNCEConverter's built-in sampleID-based timestamp handling
Skin contacts:     frametimes.npy row 1, indexed by each event's frame number (from `frames` in the .h5)
```

`session_start_time` is set to `session_date` (midnight UTC, parsed from the session folder name)
— no time-of-day is currently encoded (see Open Questions).

## Open Questions

Items that need input from the lab (Lily Cao / Ugne Klibaite) before they can be resolved:

- **Exact session start times of day** — `frametimes.npy` only gives elapsed seconds from session
  start, not wall-clock time; `session_start_time` is currently set to midnight UTC of the session
  date.
- **Recording timezone** — need to confirm whether sessions were recorded on Harvard local time
  (Eastern) or another timezone, to correctly localize `session_start_time`.
- **Full session data for CHD8, GRIN2B, NRXN1, Long-Evans WT** — currently only skin-contacts
  `.h5` files are in the share for these cohorts; video/calibration/sDANNCE are pending upload.
- **Per-rat sex** — not present in `ugne_rat_log.xlsx`; currently hardcoded to `"U"` in
  `get_subject_metadata()`.
- **Per-rat weight** — not available in any source seen so far; only an approximate cohort-level
  range (350–600 g) is known from the paper.

## TODOs

Internal code/repo work, not blocked on the lab:

- **No automated tests** exist for the interfaces or conversion pipeline.
- **Sex inference**: `get_subject_metadata()` could derive sex from the rat ID (`M{n}` prefix in
  the log is a rat index, not a sex marker in this dataset — confirm before attempting to infer
  sex from ID text).
- **Batch conversion for CHD8/GRIN2B/NRXN1/Long-Evans WT** once full session data is uploaded —
  `convert_all_sessions.py::DEFAULT_COHORTS` will need to be extended.
- **Ephys and fiber photometry interfaces** — placeholders only; no design work started, pending
  the lab collecting and sharing this data.
