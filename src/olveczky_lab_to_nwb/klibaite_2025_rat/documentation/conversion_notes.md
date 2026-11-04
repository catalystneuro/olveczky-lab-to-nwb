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
- **Publication:** Klibaite U, Li T, Aldarondo D, Akoad J, Olveczky B, Dunn T, Cao L. Mapping the
  landscape of social behavior. *Cell.* 2025. doi:10.1016/j.cell.2025.01.044
- **SFARI funding:** grant 272165.
- Electrophysiology (flexible probes, Neuropixels, tetrodes) and fiber photometry are planned by
  the lab but not yet present in the data share — see Open Questions/TODOs.

## Data Streams

| Stream | Format | File Pattern | NeuroConv Interface |
|---|---|---|---|
| 3D pose estimation (per rat) | sDANNCE `.mat`, single-animal 3D format | `SDANNCE(_x2)/bsl0.5_FM_rat{N}/save_data_AVG0.mat` (falls back to `save_data_AVG.mat`) | `DANNCEConverter` (neuroconv), one call per rat |
| Multi-camera video (6 cameras) | `.mp4` per camera, external file | `videos/Camera{1..6}/0.mp4` | via `DANNCEConverter` (linked automatically, shared across both rats' NWB files) |
| Camera calibration | `.mat` per camera | `calibration/hires_cam{N}_params.mat` | via `DANNCEConverter` (`calibration_path`) — writes calibrated `Device`s |
| Video frame times | `.npy`, shape `(2, n_frames)` | `videos/Camera{1..6}/frametimes.npy` | time each camera's video; Camera1's also times the sDANNCE pose and the skin-contact events (see Temporal Alignment) |
| Skin contacts *(optional, when available)* | `.h5` | `social_touch/<cohort>_<encounter>/<session>/skin_contacts_symmetric.h5` | `SkinContactsInterface` (custom) → `EventsTable` in `nwbfile.events` |
| Subject metadata | XLSX (lab rat log) | `ugne_rat_log.xlsx` (one sheet per cohort) | `Subject`, via `utils/subject_metadata.get_subject_metadata()` |

Not converted / not yet in the data share:

- **Center of mass** (`COM/predict{00,01}/com3d*.mat`, merged per-rat as `instance{0,1}com3d.mat`) — the
  3D crop-anchor the sDANNCE network was targeted around for each frame, not a keypoint itself, but
  superseded by (not literally reproducible from) the sDANNCE pose keypoints; kept out of NWB as a
  pipeline-internal targeting signal, not an independent measurement.
- **STAC skeleton fit** (`stac/`, SCN2A only) — intermediate model-fitting artifact, not converted.
- **Experiment config/orchestration** (`io.yaml`, `predict.sh`, `_batch_params.p`) — DANNCE/sDANNCE
  pipeline run recipe and SLURM job-splitting bookkeeping, not lab/session metadata. `io.yaml` does
  usefully record the exact checkpoint used per session (e.g. `bsl0.5_FM/checkpoint-epoch100.pth`,
  `train_mode: finetune`) and a `left_keypoints`/`right_keypoints` cross-check for the rat23 skeleton
  ordering in `utils/constants.py`.
- **SLURM job logs** (`slurm-{jobid}.out`) — HPC stdout/stderr from COM/sDANNCE training (finetune,
  often resubmitted 3-4x per session on Duke's `tdunn` partition) and the chunked prediction run
  (`slurm-{jobid}_{0..17}.out` array job, one task per 5000-frame chunk). Provenance only, no NWB
  content.
- **`save_data_AVG.mat` / `init_save_data_AVG.mat` / `com3d_used.mat`** (sibling files next to the
  ingested `save_data_AVG0.mat` in each `SDANNCE(_x2)/bsl0.5_FM_rat{N}/` folder) — see **known
  issue** below for why `save_data_AVG.mat` itself is no longer the ingested file;
  `init_save_data_AVG.mat` is an earlier/superseded prediction pass (joint positions differ from
  the final `pred` by up to ~43 units) and `com3d_used.mat` is a provenance copy of the COM
  trajectory fed into that specific sDANNCE run.
- **`sampleCAL_BG_dannce.mat`** — a Label3D GUI calibration/background companion file; its per-camera
  `params` (K/r/t) are a rawer, less-refined draft than `calibration/hires_cam{N}_params.mat` (already
  ingested), and its `sync` channel is all-zero/unused in these sessions. Nothing not already better
  represented by the calibration files we ingest.
- **`videos/Camera{1-6}/metadata.csv`** — campy capture-software metadata (`cameraModel`,
  `cameraSerialNo`, `frameRate`, resolution). Not currently pulled into `Device`/`ImageSeries`
  metadata; low-effort enrichment opportunity, not a data gap.
- **Electrophysiology** (flexible probes, Neuropixels, tetrodes) and **fiber photometry** — planned by the lab, not yet collected/shared.

### Known issue (resolved 2026-09-08): `save_data_AVG.mat` was missing the last chunk of every session

Verified 2026-08-06 across 60 ARID1B session/rat folders (all with both files present): the ingested
`save_data_AVG.mat` (`sampleID` 0-88999, 89000 frames) is byte-identical, frame-for-frame, to the
full-session `save_data_AVG0.mat` (`sampleID` 0-89999, 90000 frames) sitting in the same folder — it is
simply missing the final 1000-frame prediction chunk (the last of 18 SLURM-array chunks defined in
`_batch_params.p`). This is ~20s (at 50 fps) dropped from the end of every rat-session currently
converted. 1197/1198 `save_data_AVG.mat` files in the full `ugne/` share have a matching
`save_data_AVG0.mat` sibling; this looks like a systematic artifact of the lab's own chunk-merge
script, not session-specific. See full file-inventory report:
[sDANNCE Output Inventory](https://claude.ai/code/artifact/7a302e24-7a54-4b47-8ac8-5b4db3dd5a8b)

**Lab confirmed (Lily Cao, 2026-09-08): read `save_data_AVG0.mat` instead.** `find_sdannce_mat()`
in `convert_session.py` now prefers `save_data_AVG0.mat`, falling back to `save_data_AVG.mat` only
for the 1/1198 session missing the sibling. Sessions already converted from `save_data_AVG.mat`
are missing their last ~20s and should be re-run.

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
│   │   └── save_data_AVG0.mat             # ~115 MB, per-rat pose, full session (see below)
│   └── bsl0.5_FM_rat2/
│       └── save_data_AVG0.mat
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
├── notebooks/
│   ├── dandi_001936_tutorial.ipynb   # single-subject: stream/read one rat's NWB file, explore + visualize
│   └── two_subject_tutorial.ipynb    # two-subject: load a rat pair (shared session_id) together,
│                                      # paired visualizations (rat1=blue, rat2=red convention)
└── documentation/
    ├── conversion_notes.md        # this file
    ├── project_track.md           # conversion progress tracker
    └── metadata_request_email.md  # metadata request sent to the lab (2026-04-21) and reply
```

Each session folder is shared by both rats; `convert_session.py::session_to_nwb()` converts one
rat (selected via `rat_idx`) to one NWB file, and `convert_all_sessions.py` calls it twice per
session (once per rat) so both NWB files reference the same external video files.

## File Inventory & Counts

- **Cohorts with full data** (video + calibration + sDANNCE + skin contacts): **SCN2A, ARID1B, CHD8,
  GRINB, NRXN1** (SOC1–3) and **LONGEVANS** (`LONGEVANS_M_SOC1`–`SOC8`), all listed in
  `convert_all_sessions.py`'s `DEFAULT_COHORTS`. 468 social sessions in total (survey, 2026-11-04).
- Roughly 10–30 sessions per cohort × encounter round; each session = 2 NWB files (one per rat).
- ARID1B uses `SDANNCE_x2/` (two-rat simultaneous fit); SCN2A uses `SDANNCE/bsl0.5_FM_rat{N}/`.
  `find_sdannce_mat()` in `convert_session.py` searches both folder-name variants.

## Sessions / Subjects

- **Session folder naming:** `YYYY_MM_DD_M{rat1_id}_M{rat2_id}` (e.g. `2022_09_22_M1_M2`),
  parsed by `parse_session_folder_name()`. Multiple encounter rounds (SOC1, SOC2, SOC3) are
  repeat pairings of the same or different rats across days.
- **Species / strain:** *Rattus norvegicus*; Long-Evans background for all cohorts, including KO
  lines (confirmed by lab, 2026-04-29). Per-cohort strain/supplier/RRID lookup table is in
  `utils/subject_metadata.py::STRAINS`. The LONGEVANS cohort is `"Long-Evans"` / `RRID:RGD_2308852`,
  taken from the rat log's `Strain` column (corrected 2026-08-12, confirmed 2026-11-04). NWB files
  converted for this cohort before 2026-08-12 need to be re-run to fix `Subject.strain`.
- **Subject IDs:** `f"{cohort}-{rat_id}"` (e.g. `"SCN2A-M1"`); `rat_id` (e.g. `"M1"`) is unique
  within a cohort, not globally.
- **Per-rat metadata source:** `ugne_rat_log.xlsx`, one sheet per cohort, two-row header
  (banner + column names): `Rat ID`, `DOB`, `Genotype`, `Markings`, `Cage`, `Mother`. Read by
  `utils/subject_metadata.get_subject_metadata(rat_id, cohort, rat_log_path)`.
- **Weight:** per-rat weights were not recorded (confirmed 2026-11-04), so `Subject.weight` is left
  empty. The paper gives an approximate range of 350–600 g, which is not written to NWB.
- **Sex:** not present in the rat log; lab confirmed all rats are male, so
  `get_subject_metadata()` sets `"sex": "M"` for every rat.

## Existing Resources

- **Publication:** Klibaite et al. (2025), *Cell*, doi:10.1016/j.cell.2025.01.044.
- **Harvard Dataverse:** <https://dataverse.harvard.edu/dataverse/socialDANNCE_data>
- **Data source:** Google Drive share (`ugne/` folder), mounted locally (e.g.
  `H:/Olveczky-CN-data-share/ugne/`); also accessible via `rclone` (`--drive-shared-with-me`).
  
## Interface Mapping

| Interface | Writes | Notes |
|---|---|---|
| `DANNCEConverter` (neuroconv, ×1 per rat) | `PoseEstimation` (ndx-pose) + 6 `ImageSeries` (external video) + calibrated `Device`s | Reads the per-rat, single-animal `save_data_AVG0.mat` (3D `pred` array, shape `(n_frames, 3, 23)` — NOT the 4D multi-animal format `SDANNCEInterface` expects). Skeleton (`SDANNCE_LANDMARK_NAMES`/`SDANNCE_SKELETON_EDGES` from `utils/constants.py`) is injected into `Behavior/Pose` metadata at conversion time (`session_to_nwb()`), keyed by `pose_key` ("PoseEstimationSDANNCE") to match `DANNCEInterface`'s own lookup; the descriptive per-rat name (`SkeletonPoseEstimationSDANNCE_Rat{N}`) is only the Skeleton's `name` field, since each rat is written to a separate NWB file. |
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
- **External resources (HERD) annotation (updated 2026-11-03):** NeuroConv
  (`neuroconv.tools.external_resources.add_external_resources_to_nwbfile`, on neuroconv main) writes
  machine-readable ontology references in-file (`/general/external_resources`) for the terms stated
  in `metadata["ExternalResources"]`. Nothing is inferred. Each map is keyed by the exact string it
  annotates, and each term is a `{"id": <CURIE>, "uri": <URI>}` dict. All terms are stated in
  `general_metadata.yaml` (see catalystneuro/neuroconv#1771 for the design):
  - `species`: *Rattus norvegicus* -> `NCBITaxon:10116`.
  - `strain`: every `STRAINS` designation -> its RRID (Long-Evans and the MCW knockout lines).
    `convert_session.py` raises if a subject's strain is missing from the YAML or its RRID differs
    from `STRAINS`, which also writes the RRID into the subject description.
  - `anatomical_structures` (was `anatomy`): all 23 rat23 nodes -> UBERON. Left and right share one
    term (YAML anchors), the three spine points share the vertebral column term, and `"TailBase"`
    uses the tail term because UBERON has no tail-base term.
  - `institution`: Harvard University -> `ror:03vek6s52`.
  - `experimenter`: ORCID iDs for Klibaite and Aldarondo, whose ORCID records list Olveczky lab
    papers. The other five experimenters have no verified iD and are left out. TODO: ask the lab
    for the missing ORCID iDs.

  Verified on an ARID1B stub conversion against neuroconv main: each rat's file has 28 references
  (1 species, 1 strain, 23 skeleton nodes, 2 experimenters, 1 institution). No brain-region
  annotation applies to this dataset (pose/behavior only, with no electrodes,
  imaging planes or fiber photometry).

## Temporal Alignment

Single-clock design per session — every stream derives from the shared per-camera
`frametimes.npy` (elapsed seconds from session start):

```text
Reference clock:   Camera1 frametimes.npy row 1 (elapsed seconds), 50 fps, 90000 frames (~30 min)
Video (6 cameras): each camera's own frametimes.npy, linked internally by DANNCEConverter
sDANNCE pose:      Camera1 frametimes.npy row 1, indexed by each prediction's video frame (see below)
Skin contacts:     frametimes.npy row 1, indexed by each event's frame number (from `frames` in the .h5)
```

The sDANNCE prediction files (`save_data_AVG0.mat`) record a `sampleID` per prediction, which is a row
label, not a frame index. The video frame comes from the `sync` table of the Label3D file
(`*Label3D_dannce.mat`) in the session folder, which `convert_session.py` passes to `DANNCEConverter` as
`sync_path`. When a session has several Label3D files, the newest (by timestamped name) is used.

Only 181 of the 468 social sessions have a Label3D file (survey of the data share, 2026-11-04):

| Cohort | Sessions without a Label3D file |
|---|---|
| ARID1B | 63/86 |
| CHD8 | 83/84 |
| GRINB | 33/45 |
| NRXN1 | 72/84 |
| SCN2A | 36/45 |
| LONGEVANS | 0/124 |

All 321 Label3D files on the share (social and solo sessions) have a Camera1 sync table that maps
`sampleID` 0-89999 to frames 0-89999, which covers all 90000 Camera1 frametimes. For sessions without a
Label3D file, `convert_session.py` therefore takes each `sampleID` as the Camera1 frame, checks that the
sampleIDs are integers within the frametimes, sets the pose times to `frametimes[sampleID]`, and prints a
warning. Confirmed 2026-11-04: in these sessions each `sampleID` is the Camera1 frame it was predicted on.

Three LONGEVANS_M_SOC3 sessions (`2022_11_10_M0_M5`, `2022_11_10_M1_M2`, `2022_11_10_M3_M4`) have no
Camera1 `frametimes.npy`, so their pose and video cannot be timed from it.

`session_start_time` is the session date parsed from the folder name, at midnight US/Eastern
(`America/New_York`, so UTC-4 or UTC-5 depending on daylight saving time). Sessions were recorded in
US/Eastern time, and the time of day was not recorded (both confirmed 2026-11-04): `frametimes.npy`
holds elapsed seconds from the start of the recording, and campy's `metadata.csv` holds only the
duration and frame rate.

## Batch Conversion Run Summary (2026-07-28)

Report: https://claude.ai/code/artifact/e4fd756e-cd18-4c8f-a367-f08cda919134

Ran a stub-test (100 frames/session) conversion cohort-by-cohort across all 6 groups. **468 unique sessions / 936 rat-sessions** expected; **797 converted successfully (85%)**.

| Cohort | Rat-sessions OK | Failed |
|---|---|---|
| SCN2A | 90/90 | 0 |
| ARID1B | 166/172 | 6 |
| CHD8 | 168/168 | 0 |
| GRINB | 90/90 | 0 |
| NRXN1 | 168/168 | 0 |
| LONGEVANS | 115/248 | 133 |

**Bugs fixed in the pipeline** (in `convert_all_sessions.py` and `utils/subject_metadata.py`):
- `GRINB`/`GRIN2B` and `LONGEVANS`/`LongEvans` naming mismatches were causing metadata lookups to throw `KeyError` for entire cohorts.
- LONGEVANS solo-rat baseline folders crashed session discovery for the **whole cohort** (0/248 before the fix) — now skipped gracefully.
- LONGEVANS skin-contacts files were silently never found (wrong path reconstruction).
- Missing rat-log columns (Genotype/DOB) for NRXN1/CHD8/LongEvans previously discarded a rat's *entire* metadata record, including `strain`; now degrades individual fields to `"unknown"` instead.

**Genuine data gaps flagged (need lab input), not code bugs:**
- LONGEVANS SOC1–5 (~132 sessions) have no sDANNCE pose data uploaded at all — video/calibration only.
- 1 ARID1B session and rat IDs `M8_EXTRA`/`M5_take2` missing sDANNCE data / not in the rat log.
- 2 ARID1B sessions blocked by stray macOS `._0.mp4` sidecar files confusing neuroconv's video-segment discovery — a data-hygiene issue, not our code.
- 3 NRXN1 `MemoryError`s were transient (resolved on retry at lower parallelism) — worth capping worker count for the full run.

All details are in the report, including a per-cohort, per-session table with pass/fail per rat and metadata-completeness indicators. `documentation/project_track.md` was updated with this status for future sessions. Next step, when ready: the full (non-stub) conversion run.

