# Conversion Notes: Olveczky Lab

## Status
Phase 1 — Experiment Discovery (complete); Phase 2 — Data Inspection (complete)

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

## Phase 2: Data Inspection Findings

### frametimes.npy — shape (2, 90000), dtype float64
- Row 0: frame indices (1 to 90000, 1-based)
- Row 1: elapsed time in **seconds** from session start (0.0 → ~1801.37 s)
- Session duration: 1800 s (30 min); 90000 frames at **50 fps** (confirmed by metadata.csv)
- Use row 1 as `timestamps` for ImageSeries

### metadata.csv — key fields per camera
- `frameRate: 50` fps
- `totalFrames: 90000`, `recTimeInSec: 1800`
- `frameWidth: 1920`, `frameHeight: 1200`
- `cameraMake: basler`, `cameraModel: a2A1920-160ucBAS`
- `codec: h264`, `numCams: 6`
- Camera names: Camera1–Camera6

### hires_camX_params.mat — camera calibration (one per camera)
Fields: `K` (3×3 intrinsic), `r` (3×3 rotation), `t` (1×3 translation, mm),
`RDistort` (1×2 radial distortion), `TDistort` (1×2 tangential distortion, zeros)
Translation z ~1113 mm → camera is ~1.1 m above arena. Coordinate units: mm.

### com3d_used.mat — center of mass 3D position
- `sampleID`: (1, 90000) frame indices 0-based
- `com`: (90000, 3) float64 — (x, y, z) position in **mm**, world coordinates

### save_data_AVG.mat — SDANNCE 3D pose keypoints
- `pred`: **(89000, 3, 23)** float64 — (n_frames, xyz, n_keypoints) — **23 keypoints**
- `data`: (89000, 3, 23) float64 — all zeros (unused / training residuals)
- `p_max`: (89000, 23) float64 — per-keypoint confidence scores
- `sampleID`: (1, 89000) float64 — frame indices 0-based
- Note: 89000 frames vs 90000 in video (SDANNCE drops ~500 frames at each end)
- **Keypoint names NOT in file** — must be confirmed with lab (standard DANNCE skeleton = 23 joints)
- Coordinate units: mm, same world frame as calibration/COM

### skin_contacts_symmetric.h5 — skin contact events
- `contacts`: (8934844, 2) int64 — [rat1_vertex_idx, rat2_vertex_idx] per event
- `frames`: (8934844,) int64 — frame index for each contact event (multiple per frame)
- `vertex_body_map`: (6880,) object — body-part label per vertex, e.g. `b'walker/foot_R'`
  → 6880 vertices total in the STAC body model; labels use format `walker/<part>`
- File size: 205 MB (many contact events per session)

### Folder structure clarified
- `ugne/social_touch/` contains **only** skin_contacts_symmetric.h5 per session
- Full data (video + SDANNCE + calibration + COM) lives in `ugne/ARID1B/` and `ugne/SCN2A/`
- CHD8, GRINB, NRXN1, LONGEVANS full sessions NOT yet in share (contacts only)
- ARID1B uses `SDANNCE_x2/` (two-rat simultaneous); SCN2A uses `SDANNCE/bsl0.5_FM_ratX/`
- SCN2A has `stac/` folder; ARID1B does not

## NWB Representation Plan

| Data | NWB type | Notes |
|------|----------|-------|
| Video (6 cameras) | `ImageSeries` (external file) | One per camera; timestamps from frametimes.npy row 1 |
| Camera calibration | `Device` + custom metadata or ndx field | K, r, t, distortion per camera |
| SDANNCE keypoints (pred) | `PoseEstimation` (ndx-pose) | 3D; shape (n_frames, n_keypoints, 3) after transpose |
| SDANNCE confidence (p_max) | within PoseEstimationSeries | confidence field |
| COM 3D position | `SpatialSeries` | (n_frames, 3) in mm |
| Skin contacts | Custom `DynamicTable` | frame, rat1_vertex, rat2_vertex, body_part1, body_part2 |

**Note on ndx-pose for 3D:** ndx-pose supports 3D PoseEstimation. Need to verify Spyglass
compatibility with ndx-pose before finalizing.

## Open Questions
- [ ] What are the 23 DANNCE/SDANNCE keypoint names in order? (standard skeleton)
- [ ] Is subject metadata available? (DOB, sex, weight, genotype per animal ID)
- [ ] Harvard Dataverse link for previously published data?
- [ ] Electrophysiology data location and format (not yet in data share)
- [ ] Is ndx-pose installed/supported in target Spyglass version?
- [ ] Species/strain of rats (Long-Evans assumed for WT; KO strain details needed)
- [ ] Does `data` field in save_data_AVG.mat have a meaning (all zeros in sample)?
- [ ] Are ARID1B session timestamps (frametimes.npy) in same format as SCN2A?
