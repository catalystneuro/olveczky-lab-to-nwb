# Excluded sessions

This page lists the folders of the `ugne/` data share that are not converted, and why. It was made by checking every
folder of the share for the files the conversion needs, and by converting every session as a stub with
`convert_all_sessions.py`: the failing sessions are those with a file in `<output folder>/exceptions/`.

## Summary

The six converted cohorts have 468 social session folders. 400 of them convert, into 800 NWB files (one per rat); 68
do not.

| Cohort | Sessions | Converted | Not converted | Converted without skin contacts |
| --- | --- | --- | --- | --- |
| SCN2A | 45 | 45 | 0 | 0 |
| ARID1B | 86 | 83 | 3 | 0 |
| CHD8 | 84 | 84 | 0 | 0 |
| GRINB | 45 | 45 | 0 | 0 |
| NRXN1 | 84 | 84 | 0 | 0 |
| LONGEVANS | 124 | 59 | 65 | 14 |
| Total | 468 | 400 | 68 | 14 |

Not converted at all: the FX cohort (156 folders) and the Long-Evans solo recordings (37 folders).

The 800 files pass `inspection.py` with no critical message and no HED error, and hold 28 ontology references each.

## Sessions without pose (66 sessions)

A file needs the rat's sDANNCE prediction, `SDANNCE*/bsl0.5_FM_rat<N>/save_data_AVG0.mat`. These session folders
have no `SDANNCE*` folder at all, only videos and calibration:

| Encounter round | Sessions |
| --- | --- |
| LONGEVANS_M_SOC1 | `2022_10_24_M0_M1`, `2022_10_24_M2_M3`, `2022_10_24_M4_M5`, `2022_10_25_M0_M5`, `2022_10_25_M1_M3`, `2022_10_25_M4_M2`, `2022_10_26_M0_M4`, `2022_10_26_M1_M2`, `2022_10_26_M3_M5`, `2022_10_27_M0_M3`, `2022_10_27_M1_M4`, `2022_10_27_M2_M5`, `2022_10_28_M0_M2`, `2022_10_28_M1_M5`, `2022_10_28_M3_M4` |
| LONGEVANS_M_SOC2 | `2022_10_31_M1_M5`, `2022_10_31_M2_M4`, `2022_10_31_M3_M0`, `2022_11_01_M0_M1`, `2022_11_01_M2_M3`, `2022_11_01_M4_M5`, `2022_11_02_M0_M4`, `2022_11_02_M1_M3`, `2022_11_02_M2_M5`, `2022_11_03_M0_M2`, `2022_11_03_M1_M4`, `2022_11_03_M3_M5`, `2022_11_04_M0_M5`, `2022_11_04_M1_M2`, `2022_11_04_M3_M4` |
| LONGEVANS_M_SOC3 | `2022_11_07_M0_M1`, `2022_11_07_M2_M3`, `2022_11_07_M4_M5`, `2022_11_08_M0_M2`, `2022_11_08_M1_M4`, `2022_11_08_M3_M5`, `2022_11_09_M0_M4`, `2022_11_09_M1_M3`, `2022_11_09_M2_M5`, `2022_11_10_M0_M5`, `2022_11_10_M1_M2`, `2022_11_10_M3_M4`, `2022_11_11_M0_M3`, `2022_11_11_M1_M5`, `2022_11_11_M2_M4` |
| LONGEVANS_M_SOC4 | `2022_11_14_M0_M5`, `2022_11_14_M1_M4`, `2022_11_14_M2_M3`, `2022_11_15_M0_M4`, `2022_11_15_M1_M2`, `2022_11_15_M3_M5`, `2022_11_16_M0_M3`, `2022_11_16_M1_M5`, `2022_11_16_M2_M4`, `2022_11_17_M0_M1`, `2022_11_17_M2_M5`, `2022_11_17_M3_M4`, `2022_11_18_M1_M3`, `2022_11_18_M2_M0`, `2022_11_18_M4_M5` |
| LONGEVANS_M_SOC5 | `2022_11_21_M0_M1`, `2022_11_21_M4_M5`, `2022_11_22_M1_M3`, `2022_11_22_M2_M4` |
| LONGEVANS_M_SOC7 | `2022_12_07_M2_M5` |
| ARID1B_SOC1 | `2022_10_20_M11_M6` (only the job logs of the prediction run) |

- `LONGEVANS_M_SOC7/2022_12_07_M2_M5` was recorded again as `2022_12_07_M2_M5_take2`, which has pose and is
  converted.
- Three of these sessions also miss video files: `LONGEVANS_M_SOC3/2022_11_10_M0_M5` and `2022_11_10_M1_M2` have no
  Camera1 `frametimes.npy`, and `2022_11_10_M3_M4` has no Camera1 video either.

To convert them: add the sDANNCE predictions to the share and run `convert_all_sessions.py` again (with
`overwrite=False`, only the new sessions are converted).

## Sessions with file problems (2 sessions)

| Session | Problem | Fix |
| --- | --- | --- |
| `ARID1B_SOC1/2022_10_21_M2_M6` | `videos/Camera1/` holds `._0.mp4`, a 4 KB macOS metadata file. It is read as a second video and cannot be opened. | Delete `._0.mp4`. |
| `ARID1B_SOC1/2022_10_21_M7_M8_EXTRA` | No `calibration/` folder, and the same `._0.mp4` file in `videos/Camera1/`. | Add the calibration (`hires_cam<N>_params.mat`) and delete `._0.mp4`. |

## Sessions converted without skin contacts (14 sessions)

`social_touch/` has no folder for `LONGEVANS_M_SOC9`, so its 14 sessions are converted with pose and video only. All
other converted sessions have skin contacts.

## Folders not converted

| Folder | Content | Why |
| --- | --- | --- |
| `FX/` (156 folders) | Fragile X cohort: pairs in `FXmale_all1`, `FXmale_all2`, `FXmale_brothers1`, `FXmale_brothers2`, `FXmale_friends1` (127 sessions), solo recordings in `FXmale_wk1` (24), and `FXfemale07` (5, videos only) | The pose of both rats is in one file, `SDANNCE/predict_results/save_data_AVG0.mat` with `pred` of shape `(n_frames, 2, 3, 23)`, and nothing on the share says which animal index is which rat. The rat log gives a blue and a red rat for each session, which is not always the first rat of the folder name (for example `2021_12_09_M2_M1`: blue M1, red M2). The encounter folders are not named `SOC<N>`, and there are no skin contacts. |
| `LONGEVANS/LONGEVANS_M/` (31) and `LONGEVANS_M_AMP/` (6) | Solo recordings of one rat (`YYYY_MM_DD_M<a>`); `_AMP` after amphetamine | The conversion is built for pairs of rats. |
| `LONGEVANS_M_SOC2/TEST`, `LONGEVANS_M_SOC8/{COM,scripts,test}`, `LONGEVANS_M_SOC9/{batch1,batch2}` | Test recordings, center of mass runs and job scripts | Not sessions. |

Converting FX needs, from the lab, which animal index of `pred` is which rat (for example, whether index 0 is always
the blue rat). With that, FX can be added like the other cohorts, using `animal_index` of `DANNCEConverter` and a
`FX` entry in `COHORTS` (sheet `FRAGILEX`, strain `LE-Fmr1-em2Mcwi`, already in `general_metadata.yaml`).

## Data share details the conversion handles

These are not exclusions, but explain choices in the code:

- Some sessions keep the prediction folder in two `SDANNCE*` folders (`SCN2A_SOC3`: `2022_10_06_M3_M6`,
  `2022_10_06_M5_M1`, `2022_10_07_M1_M4`, `2022_10_07_M5_M3`); the copies are identical, and the first is read.
- `LONGEVANS_M_SOC6/2022_11_30_M0_M5` also has a test prediction, `SDANNCE/predict02_test_rat<N>` (a short run). Only
  `bsl0.5_FM_rat<N>` folders are read.
- `LONGEVANS_M_SOC8/2022_12_12_M0_M1` keeps its prediction in `SDANNCE_x3/`.
- `CHD8_SOC2/2022_12_04_M5_M8` and `2022_12_04_M7_M2` also have a `save_data_AVG0_old.mat` with 85000 frames; the
  `save_data_AVG0.mat` read has the full 90000.
- Folder suffixes (`_EXTRA`, `_take2`) are kept in the session ID; the rat is the ID before the suffix (`M8`, `M5`).
