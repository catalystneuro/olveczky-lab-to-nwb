# Excluded sessions

This page lists the folders of the `ugne/` data share that are not converted, and why. It was made by checking every
folder of the share for the files the conversion needs, and by converting every session as a stub with
`convert_all_sessions.py`: the failing sessions are those with a file in `<output folder>/exceptions/`.

## Summary

The seven converted cohorts have 595 social session folders. 525 of them convert, into 1050 NWB files (one per rat);
70 do not. 54 lone sessions convert too, into one NWB file each.

| Cohort | Social sessions | Converted | Not converted | Converted without skin contacts | Lone sessions converted |
| --- | --- | --- | --- | --- | --- |
| SCN2A | 45 | 45 | 0 | 0 | 0 |
| ARID1B | 86 | 84 | 2 | 0 | 0 |
| CHD8 | 84 | 84 | 0 | 0 | 0 |
| GRINB | 45 | 45 | 0 | 0 | 0 |
| NRXN1 | 84 | 84 | 0 | 0 | 0 |
| LONGEVANS | 124 | 59 | 65 | 14 | 30 |
| FX | 127 | 124 | 3 | 124 | 24 |
| Total | 595 | 525 | 70 | 138 | 54 |

Not converted at all: `LONGEVANS_M_AMP` (6 lone sessions after amphetamine) and `FXfemale07` (5 folders), which have
no pose.

The 800 files of the first six cohorts' social sessions pass `inspection.py` with no critical message and no HED error,
and hold 28 ontology references each. So do the stub files of `FX/FXmale_brothers1/2021_12_08_M1_M2`,
`FX/FXmale_brothers2/2021_12_09_M2_M1`, `FX/FXmale_wk1/2021_12_04_M1` and `LONGEVANS/LONGEVANS_M/2022_10_17_M0`.

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

## Session without calibration (1 session)

`ARID1B_SOC1/2022_10_21_M7_M8_EXTRA` has no `calibration/` folder. The camera parameters of its Label3D files
(`sampleCAL_BG_dannce.mat`, `20221109_124650_COM_Label3D_dannce.mat`) are the same, for all 6 cameras, as the
`calibration/` files of `ARID1B_SOC1/2022_10_21_M2_M6`, recorded the same day. Copying that folder into the session
would let it convert.

## FX sessions not in the rat log (3 sessions)

The FX prediction file holds both rats; index 0 is the rat dyed blue, and the rat log says which rat is blue (see
[Data organization](data_organization.md#sdannce-prediction-files)). These sessions are not in the log, so
`get_fx_rat_order` cannot tell which rat is which:

- `FXmale_all1/2021_12_16_M7_M4_fresh` (it also has no prediction file);
- `FXmale_all2/2022_01_21_M5_M6`;
- `FXmale_all2/2022_01_28_M2_M1`; the log lists `2022_01_25_M2_M1` (blue M2) instead, which is not on the share.

In 12 converted FX sessions the log's blue rat is the second rat of the folder name (all of `FXmale_brothers2`, and
`FXmale_friends1` `2021_12_09_M4_M1`, `2021_12_09_M6_M7`, `2021_12_09_M8_M5`, `2021_12_10_M1_M3`, `2021_12_10_M1_M4`,
`2021_12_10_M7_M5`, `2021_12_11_M2_M4`, `2021_12_11_M7_M6`); their rat1 is the blue rat of the log. In
`FXmale_friends1/2021_12_10_M8_M6` the log gives only the red rat, M6, so M8 is blue.

## Sessions converted without skin contacts (138 sessions)

`social_touch/` has no folder for `LONGEVANS_M_SOC9` or the FX cohort, so these 14 and 124 social sessions are
converted with pose and video only. All other converted social sessions have skin contacts. Lone sessions have none.

## Folders not converted

| Folder | Content | Why |
| --- | --- | --- |
| `LONGEVANS/LONGEVANS_M_AMP/` (6) | Lone sessions after amphetamine | No pose. |
| `FX/FXfemale07/` (5) | Female FX rats (`YYYY_MM_DD_V<N>`), videos only | No pose and no calibration. |
| `LONGEVANS_M_SOC2/TEST`, `LONGEVANS_M_SOC8/{COM,scripts,test}`, `LONGEVANS_M_SOC9/{batch1,batch2}`, `LONGEVANS_M/test` | Test recordings, center of mass runs and job scripts | Not sessions. |

## Data share details the conversion handles

These are not exclusions, but explain choices in the code:

- Some sessions keep the prediction folder in two `SDANNCE*` folders (`SCN2A_SOC3`: `2022_10_06_M3_M6`,
  `2022_10_06_M5_M1`, `2022_10_07_M1_M4`, `2022_10_07_M5_M3`); the copies are identical, and the first is read.
- `LONGEVANS_M_SOC6/2022_11_30_M0_M5` also has a test prediction, `SDANNCE/predict02_test_rat<N>` (a short run). Only
  `bsl0.5_FM_rat<N>` folders are read.
- `LONGEVANS_M_SOC8/2022_12_12_M0_M1` keeps its prediction in `SDANNCE_x3/`.
- `CHD8_SOC2/2022_12_04_M5_M8` and `2022_12_04_M7_M2` also have a `save_data_AVG0_old.mat` with 85000 frames; the
  `save_data_AVG0.mat` read has the full 90000.
- Folder suffixes (`_EXTRA`, `_take2`, `_fresh`) are not in the session ID: the take number tells apart two
  recordings of a pair on one day. The rat is the ID before the suffix (`M8`, `M5`).
- The Long-Evans lone sessions have up to three predictions: `SDANNCE_x2/bsl0.5_FM/save_data_AVG0.mat`, the model of
  the social sessions, is read; `SDANNCE_5camfix/`, `fix-5cam/` (a few thousand frames) and `SDANNCE/` (21 frames in
  `2022_10_17_M1`) are not. The FX lone sessions also have a single-animal `DANNCE/predictLS_xx2/` prediction of 5000
  frames, which is not read.
