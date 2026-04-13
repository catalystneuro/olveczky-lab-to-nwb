# Conversion Notes: Olveczky Lab

## Status
Phase 1 — Experiment Discovery (complete); Phase 2 — Data Inspection (up next)

## Experiment Overview
The Olveczky Lab (Harvard) studies the neural basis of learned and natural behaviors.
Point person: **Lily Cao**. Data contact: **Ugne Klibaite** (folder `ugne/` in data share).
Behavioral setup overlaps substantially with the Uchida lab (same facility; Hannah Phillips).

Current data share (`remoteCN:data/Olveczky-CN-data-share`) contains exclusively
behavioral data from **multi-genotype social behavior experiments** in rats.
Electrophysiology data (flexible probes, Neuropixels, tetrodes) not yet present in share.

## Data Streams Identified
| Stream | Format | System/Tool | File Pattern | NeuroConv Interface? |
|--------|--------|-------------|--------------|---------------------|
| Multi-camera video | .mp4 (per camera) | 6-camera rig | `videos/CameraX/0.mp4` | VideoInterface? |
| Video frame times | .npy | Custom | `videos/CameraX/frametimes.npy` | Custom |
| Camera metadata | .csv | Custom | `videos/CameraX/metadata.csv` | Custom |
| Camera calibration | .mat | DANNCE rig | `calibration/hires_camX_params.mat` | Custom |
| 3D pose estimation (per rat) | .mat (SDANNCE) | sDANNCE/DANNCE | `SDANNCE/bsl0.5_FM_ratX/save_data_AVG.mat` | Custom |
| Center of mass | .mat | DANNCE | `COM/predictXX/com3d*.mat` | Custom |
| STAC skeleton | .p + videos | STAC | `stac/` | Custom |
| Skin contacts | .h5 | Custom | `social_touch/.../skin_contacts_symmetric.h5` | Custom |
| Experiment config | .yaml | DANNCE | `io.yaml` | Metadata |

**Future streams (not yet in data share):**
- Extracellular ephys: flexible probes (256ch, PFC), Neuropixels → SpikeGLX/OpenEphys interfaces
- Continuous tetrode recordings (raw + snippeted)
- Fiber photometry (planned, not yet collected)

## Directory Structure
```
remoteCN:data/Olveczky-CN-data-share/
└── ugne/
    ├── ARID1B/
    │   ├── ARID1B_SOC1/     # Encounter 1
    │   ├── ARID1B_SOC2/
    │   └── ARID1B_SOC3/
    ├── SCN2A/
    │   ├── README.txt
    │   ├── SCN2A_SOC1/
    │   ├── SCN2A_SOC2/
    │   └── SCN2A_SOC3/
    └── social_touch/
        ├── README.txt       # Describes skin_contacts files
        ├── ARID1B_SOC1/     # Skin contact .h5 files only (derived from SDANNCE)
        ├── SCN2A_SOC1/
        ├── CHD8_SOC1/
        ├── GRINB_SOC1/
        ├── NRXN1_SOC1/
        └── LONGEVANS_M_SOC6/  (7, 8)

Per session folder (e.g., 2022_09_22_M1_M2/):
├── videos/
│   └── CameraX/  (1-6)
│       ├── 0.mp4
│       ├── frametimes.npy
│       └── metadata.csv
├── calibration/
│   └── hires_camX_params.mat  (1-6)
├── SDANNCE/
│   ├── bsl0.5_FM_rat1/
│   │   ├── save_data_AVG.mat   (~115 MB)
│   │   ├── save_data_AVG0.mat
│   │   ├── com3d_used.mat
│   │   └── init_save_data_AVG.mat
│   └── bsl0.5_FM_rat2/
├── COM/
│   ├── predict00/
│   └── predict01/
├── stac/
├── io.yaml
└── [ARID1B/SCN2A: also skin_contacts_symmetric.h5 in social_touch folder]
```

## Sessions
- Naming convention: `{date}_{subjectA}_{subjectB}` (e.g., `2022_09_22_M1_M2`)
- Two rats per session (blue = rat1 = first in folder name, red = rat2)
- Multiple encounter rounds (SOC1, SOC2, SOC3) = repeat pairings across days
- Datasets: SCN2A, ARID1B, CHD8, GRINB, NRXN1, LONGEVANS (WT control)
- ~10–30 sessions per genotype group × encounter round

## Subjects
- Species: rat (likely *Rattus norvegicus* — need to confirm strain)
- Sex: need to confirm
- IDs per dataset: M1–M12 approx per cohort
- Two per session (social pairs)
- Genotypes: SCN2A KO vs WT, ARID1B, CHD8, GRINB, NRXN1; WT = Long-Evans rats

## Existing Resources
- Publication: Some behavioral data published on Harvard Dataverse (URL TBD)
- GitHub repo: https://github.com/catalystneuro/olveczky-lab-to-nwb (not yet created)
- Analysis code: TBD
- Data source: `remoteCN:data/Olveczky-CN-data-share` (Google Drive, shared-with-me)
  → Access via: `rclone lsf/cat "remoteCN:..." --drive-shared-with-me`

## Open Questions
- [ ] What genotype groups/datasets should we prioritize for the first conversion?
- [ ] Are `ARID1B/` and `SCN2A/` subfolders duplicates of what's in `social_touch/`? Or different experiments?
- [ ] Structure of `save_data_AVG.mat` — keypoint names, coordinate frame, units, timestamps?
- [ ] What does `frametimes.npy` contain — wall clock times, frame indices, or elapsed seconds?
- [ ] Are raw video frames the primary data, or is SDANNCE output preferred?
- [ ] Is there a subject metadata spreadsheet (DOB, sex, genotype per animal ID)?
- [ ] Harvard Dataverse link for previously published data?
- [ ] Electrophysiology data location and format (not yet in data share)
- [ ] Does this data need Spyglass compatibility from the start?
- [ ] Species/strain of rats (Long-Evans assumed for WT, need KO strain details)
