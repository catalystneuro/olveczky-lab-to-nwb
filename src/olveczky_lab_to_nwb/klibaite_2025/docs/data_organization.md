# Data organization

The conversion reads the `ugne/` folder of the lab's data share as it is organized there. This page describes the
layout it expects, so that new recordings can be added and converted without changing the code.

## The experiment

Two male rats of the same cohort behave freely together in an arena for about 30 minutes, recorded by 6 synchronized
Basler cameras at 50 fps (campy). sDANNCE (social DANNCE) estimates the 3D pose of each rat on the 23-landmark rat23
skeleton. Skin contacts between the two rats are computed from body meshes fitted to the pose (STAC). The dataset is
described in [Klibaite et al. (2025), Cell](https://doi.org/10.1016/j.cell.2025.01.044).

## Folder layout

```text
ugne/
├── ugne_rat_log.xlsx                         one sheet per cohort
├── <cohort>/                                 SCN2A, ARID1B, CHD8, GRINB, NRXN1, LONGEVANS
│   └── <cohort>_SOC<N>/                      encounter round N (LONGEVANS_M_SOC<N> for Long-Evans)
│       └── YYYY_MM_DD_M<a>_M<b>/             one session: rats M<a> (rat1) and M<b> (rat2)
│           ├── videos/
│           │   └── Camera<1..6>/
│           │       ├── 0.mp4
│           │       ├── frametimes.npy        frame number and time in seconds of each frame
│           │       └── metadata.csv          campy settings (camera model, frame rate)
│           ├── calibration/
│           │   └── hires_cam<N>_params.mat   intrinsics and extrinsics of each camera
│           └── SDANNCE/ (or SDANNCE_x2/, SDANNCE_x3/)
│               ├── bsl0.5_FM_rat1/save_data_AVG0.mat   3D pose of rat1
│               └── bsl0.5_FM_rat2/save_data_AVG0.mat   3D pose of rat2
└── social_touch/
    └── <encounter folder>/<session folder>/skin_contacts_symmetric.h5
```

- A session folder is named `YYYY_MM_DD_M<a>_M<b>`, optionally followed by a suffix (`_EXTRA`, `_take2`), which is
  kept in the session ID. Other folders (`TEST`, `COM`, `scripts`, `test`, and the `batch1` and `batch2` folders of
  `LONGEVANS_M_SOC9`) are not sessions and are skipped.
- Rat1 is the first rat of the folder name. It is colored blue in the videos, and rat2 red.
- Solo recordings (`LONGEVANS_M`, `LONGEVANS_M_AMP`) and the `FX` cohort are not converted (see
  [Excluded sessions](excluded_sessions.md)).
- The skin contacts are in `social_touch/`, under the same encounter and session folder names. A session without a
  contacts file is converted without skin contacts.

## Cohorts

| Cohort folder | Rat log sheet | Strain | Encounter rounds |
| --- | --- | --- | --- |
| SCN2A | SCN2A | LE-Scn2a-em1Mcwi | SOC1 to SOC3 |
| ARID1B | ARID1B | LE-Arid1b-em1Mcwi | SOC1 to SOC3 |
| CHD8 | CHD8 | LE-Chd8-em1Mcwi | SOC1 to SOC3 |
| GRINB | GRINB | LE-Grin2b-em1Mcwi | SOC1 to SOC3 |
| NRXN1 | NRXN1 | LE-Nrxn1-em1Mcwi | SOC1 to SOC3 |
| LONGEVANS | LongEvans | Long-Evans (Charles River) | SOC1 to SOC9 (SOC1 to SOC5 have no pose) |

The knockout lines come from the Medical College of Wisconsin. The cohorts are listed in `COHORTS` in
`utils/subject_metadata.py`.

## Subjects and sessions

- The subject ID is `<cohort>-<rat ID>`, for example `SCN2A-M1`: rat IDs are unique within a cohort only.
- The session ID is `day-<N>-social-<rat1>-<rat2>-<YYYYMMDD>`, where N is the encounter round, for example
  `day-1-social-M1-M2-20220922`. Both NWB files of a session have the same session ID.
- The session start time is the date at midnight in America/New_York; the time of day was not recorded.

## Rat log (ugne_rat_log.xlsx)

Each cohort's sheet has a banner row, then a table of rats (one row per rat), a blank row, and a table of recordings.
The conversion reads the table of rats: `Rat ID`, `DOB`, `Genotype` (`WT` or `Het`, in ARID1B `KO wt` or `KO Het`;
see [Metadata](metadata.md#subjects) for how it is written), `Markings`, `Cage` and `Mother`. `Cage` and
`Mother` are merged cells shared by the rats of a cage, and are filled down. Some sheets lack columns: CHD8 and NRXN1
have no `Genotype`, LongEvans no dates of birth; for the Long-Evans rats the files hold the age range of the paper's
methods, 9 to 14 weeks (`P9W/P14W`). The `Age` columns of the sheets compute the age on the day the sheet is opened
and are not read. All rats are male; weights were not recorded.

## sDANNCE prediction files

`save_data_AVG0.mat` holds `pred`, of shape `(n_frames, 3, 23)`: the x, y, z position in millimeters of each of the
23 landmarks, `p_max`, the confidence of each landmark, and `sampleID`, the Camera1 frame of each prediction. The
other files of the prediction folder are not read: `save_data_AVG.mat` misses the last 1000 frames,
`init_save_data_AVG.mat` is an earlier prediction pass and `com3d_used.mat` the center of mass that guided it.
Some sessions keep the prediction folder in more than one `SDANNCE*` folder; the copies are identical and the first
is read. Prediction folders not named `bsl0.5_FM_rat<N>` (test runs) are not read.

## Skin contacts file (skin_contacts_symmetric.h5)

One row per pair of touching mesh vertices and frame: `contacts`, of shape `(n, 2)`, the vertex of rat1's and of
rat2's body mesh, and `frames`, the video frame. `vertex_body_map` gives the body part of each of the 6880 vertices of
the mesh (for example `walker/foot_R`).

## Not converted

- Center of mass (`COM/`), the STAC fit (`stac/`), the prediction configuration and job files (`io.yaml`,
  `predict.sh`, `_batch_params.p`, `slurm-*.out`): intermediate steps of the pose pipeline.
- Label3D files (`*Label3D_dannce.mat`, `sampleCAL_*_dannce.mat`): labeling and calibration drafts. Their sync tables
  map each sampleID to the same Camera1 frame, which the conversion uses directly.
- `ugne_recording_info.xlsx`: a summary of the recordings per rat and the behavioral analysis of the paper (action
  and joint cluster descriptions, group comparisons).
