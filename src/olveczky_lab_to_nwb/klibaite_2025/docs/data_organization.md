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
├── FX/
│   └── FXmale_<group>/                       pairing group: all1, all2, brothers1, brothers2, friends1
│       └── YYYY_MM_DD_M<a>_M<b>/             videos/ and calibration/ as above
│           └── SDANNCE/predict_results/save_data_AVG0.mat   3D pose of both rats
│   └── FXmale_wk1/YYYY_MM_DD_M<a>/            lone session of one rat (also LONGEVANS/LONGEVANS_M/)
└── social_touch/
    └── <encounter folder>/<session folder>/skin_contacts_symmetric.h5
```

- A session folder is named `YYYY_MM_DD_M<a>_M<b>`, optionally followed by a suffix (`_EXTRA`, `_take2`, `_fresh`).
  Other folders (`TEST`, `COM`, `scripts`, `test`, and the `batch1` and `batch2` folders of
  `LONGEVANS_M_SOC9`) are not sessions and are skipped.
- Rat1 is the rat dyed blue, and rat2 the rat dyed red. It is the first rat of the folder name, except in some FX
  sessions, where the rat log gives the colors (see [sDANNCE prediction files](#sdannce-prediction-files)).
- There are two conditions: social sessions, the pairs above, and lone sessions, one rat alone in the arena, in
  `FX/FXmale_wk1/` and `LONGEVANS/LONGEVANS_M/`, named `YYYY_MM_DD_M<a>`. `LONGEVANS_M_AMP` (lone sessions after
  amphetamine) and `FXfemale07` have no pose and are not converted (see [Excluded sessions](excluded_sessions.md)).
  `utils/session_folders.py` reads the folders of both conditions.
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
| FX | FRAGILEX | LE-Fmr1-em2Mcwi | pairing groups FXmale_all1, all2, brothers1, brothers2, friends1 (no skin contacts) |

The knockout lines come from the Medical College of Wisconsin. The cohorts are listed in `COHORTS` in
`utils/subject_metadata.py`.

## Subjects and sessions

- The subject ID is `<cohort>-<rat ID>`, for example `SCN2A-M1`: rat IDs are unique within a cohort only.
- A social session's ID is `social-<round>-<YYYYMMDD>[-<take>]-<rat a>-<rat b>`, with the rats in the order of the
  folder name. The round is the encounter round, or the pairing group for FX. For example
  `SCN2A_SOC1/2022_09_22_M1_M2` is `social-1-20220922-M1-M2`, and `FXmale_brothers2/2021_12_09_M2_M1` is
  `social-brothers2-20211209-M2-M1`. Both NWB files of the session have this ID, so only the subject differs in their
  names. The take is written only for the second recording of a pair on one day, counted in folder name order:
  `LONGEVANS_M_SOC7/2022_12_07_M2_M5_take2` is `social-7-20221207-2-M2-M5`, and `FXmale_all1/2021_12_19_M7_M3`
  (after `2021_12_19_M3_M7`) is `social-all1-20211219-2-M7-M3`.
- A lone session's ID is `lone-<YYYYMMDD>-<rat>`, for example `lone-20211205-M1` for `FXmale_wk1/2021_12_05_M1`.
- The session start time is the date at midnight in America/New_York; the time of day was not recorded.

## Rat log (ugne_rat_log.xlsx)

Each cohort's sheet has a banner row, then a table of rats (one row per rat), a blank row, and a table of recordings.
The conversion reads the table of rats: `Rat ID`, `DOB`, `Genotype` (`WT` or `Het`, in ARID1B `KO wt` or `KO Het`,
in FRAGILEX `WT` or `Hemi`, written `Fmr1<+>/Y` or `Fmr1<em2Mcwi>/Y` as Fmr1 is on the X chromosome; see
[Metadata](metadata.md#subjects) for how it is written), `Markings`, `Cage` and `Mother`. `Cage` and
`Mother` are merged cells shared by the rats of a cage, and are filled down. Some sheets lack columns: CHD8 and NRXN1
have no `Genotype`, LongEvans no dates of birth; for the Long-Evans rats the files hold the age range of the paper's
methods, 9 to 14 weeks (`P9W/P14W`). The `Age` columns of the sheets compute the age on the day the sheet is opened
and are not read. All rats are male; weights were not recorded.

Of the table of recordings, only the FRAGILEX sheet's is read: its `Blue` column gives the blue rat of each FX session,
looked up by `Path` (the pairing group, a merged cell filled down) and `Experiment File` (the session folder). The
recordings tables of the other cohorts list only their lone sessions.

## sDANNCE prediction files

`save_data_AVG0.mat` holds `pred`, of shape `(n_frames, 3, 23)`: the x, y, z position in millimeters of each of the
23 landmarks, `p_max`, the confidence of each landmark, and `sampleID`, the Camera1 frame of each prediction. The
other files of the prediction folder are not read: `save_data_AVG.mat` misses the last 1000 frames,
`init_save_data_AVG.mat` is an earlier prediction pass and `com3d_used.mat` the center of mass that guided it.
Some sessions keep the prediction folder in more than one `SDANNCE*` folder; the copies are identical and the first
is read. Prediction folders not named `bsl0.5_FM_rat<N>` (test runs) are not read.

FX sessions have one prediction file for both rats, `SDANNCE/predict_results/save_data_AVG0.mat`, with `pred` of shape
`(n_frames, 2, 3, 23)` (180000 frames, an hour). Animal index 0 is the rat dyed blue and index 1 the rat dyed red:
projected onto Camera1 frames with the calibration, index 0 lands on the blue-marked rat in
`FXmale_brothers2/2021_12_09_M2_M1`, `FXmale_friends1/2021_12_10_M1_M3` and `FXmale_brothers1/2021_12_08_M1_M2`. The
rat log says which rat ID is blue; it is the first rat of the folder name in most sessions, but not in 12. In every FX
session, rat1 is the blue rat of the log and index 0 (`get_fx_rat_order` in `utils/session_folders.py`); when the log gives
only the red rat, the other rat is blue. The session ID keeps the folder name's order. The per-rat
`DANNCE/predictLS_xx2_rat<N>` folders of FX sessions hold single-animal DANNCE predictions and are not read.

The per-rat files of the other cohorts follow the same rule: projected onto Camera1 frames, `bsl0.5_FM_rat1` lands on
the blue-marked rat and `bsl0.5_FM_rat2` on the red-marked one, in one session of each cohort
(`SCN2A_SOC1/2022_09_22_M5_M6`, `ARID1B_SOC2/2022_10_24_M3_M4`, `ARID1B_SOC3/2022_11_02_M11_M2`,
`CHD8_SOC3/2022_12_11_M6_M5`, `GRINB_SOC1/2022_09_22_M5_M6`, `NRXN1_SOC2/2022_12_03_M6_M5`,
`LONGEVANS_M_SOC6/2022_11_28_M3_M5`). Which rat ID is blue is not logged for their pairs; the conversion takes the
first rat of the folder name, which matches the log in all 117 logged Long-Evans pairs.

Lone sessions have one rat: `FXmale_wk1` sessions have `SDANNCE/predict_results/save_data_AVG0.mat` (`pred` of shape
`(90000, 1, 3, 23)`) and `LONGEVANS_M` sessions `SDANNCE_x2/bsl0.5_FM/save_data_AVG0.mat` (`(90000, 3, 23)`). Their
session description and task (`lone_session`, `Def/Lone-session`) are under `Conditions: lone` in
`general_metadata.yaml`.

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
