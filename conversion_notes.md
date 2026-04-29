# Conversion Notes: Olveczky Lab

## Status
Phase 1 — Experiment Discovery (complete); Phase 2 — Data Inspection (complete);
Phase 3 — Metadata YAML drafted (complete); Phase 4 — Sync analysis (complete);
Phase 5 — All interfaces written, stub tested (complete); Phase 6 — NWBInspector run on stub (complete)

## Experiment Overview
Reference paper ["Mapping the landscape of social behavior", U. Klibaite et al., 2025](https://www.cell.com/cell/fulltext/S0092-8674(25)00154-0)

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
| 3D pose estimation (per rat) | .mat (SDANNCE) | sDANNCE/DANNCE | `SDANNCE/bsl0.5_FM_ratX/save_data_AVG.mat` | `DANNCEInterface` (neuroconv main) |
| Center of mass | .mat | DANNCE | `COM/predictXX/com3d*.mat` | Custom |
| STAC skeleton | .p + videos | STAC | `stac/` | Custom |
| Skin contacts | .h5 | Custom | `social_touch/.../skin_contacts_symmetric.h5` | `SkinContactsInterface` (custom) |
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
- Species: *Rattus norvegicus*; strain: **Long-Evans** for all cohorts (confirmed by lab 2026-04-29)
- KO backgrounds also on Long-Evans
- IDs per dataset: M1–M12 approx per cohort; unique within cohort
- Global `subject_id` = `f"{cohort}-{rat_id}"` (e.g., `"SCN2A-M1"`)
- Sex: in the subject id `f"M{rat_index}"`--> male /`f"F{rat_index}"`--> female
- Weight: approximate range 350–600 g (no per-rat numbers available)
- DOB: available per cohort in `ugne_rat_log.xlsx` (sheet = cohort name)

## Existing Resources
- Publication: Klibaite et al. (2025), *Cell*, DOI: `10.1016/j.cell.2025.02.005`
- Harvard Dataverse: https://dataverse.harvard.edu/dataverse/socialDANNCE_data
- GitHub repo: https://github.com/catalystneuro/olveczky-lab-to-nwb (not yet created)
- Data source: `remoteCN:data/Olveczky-CN-data-share` (Google Drive, shared-with-me)
  → Access via: `rclone lsf/cat "remoteCN:..." --drive-shared-with-me`

## Lab-confirmed metadata (2026-04-29)

Lab contact Lily Cao replied to the metadata request email. Confirmed:

- **Keypoint names (23 joints, rat23 skeleton):** Snout, EarL, EarR, SpineF, SpineM, SpineL,
  TailBase, ShoulderL, ElbowL, WristL, HandL, ShoulderR, ElbowR, WristR, HandR,
  HipL, KneeL, AnkleL, FootL, HipR, KneeR, AnkleR, FootR
  (from `diegoaldarondo/Label3D` rat23.mat)
- **Skeleton edges:** 23 edges from rat23.mat `joints_idx`, stored in `constants.py`
- **Frame rate:** 50 fps (confirmed; 30-min sessions → 90000 frames)
- **Units:** millimeters (same world frame as calibration)
- **Subject metadta**: `ugne_rat_log.xlsx`(per-cohort sheet: Strain, Rat ID, DOB, Markings, Mother, Initial Weight, Genotype)
- **Skin contact "symmetric":** touch identification repeated for both rats (symmetric)
- **Publication DOI:** `10.1016/j.cell.2025.02.005`
- **Harvard Dataverse URL:** https://dataverse.harvard.edu/dataverse/socialDANNCE_data
- **Experimenter list (full):** Klibaite Ugne, Li Tianqing, Aldarondo Diego, Alkoad Jumana,
  Olveczky Bence, Dunn Timothy, Cao Lily
- **SFARI funding:** grant 272165

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

### save_data_AVG.mat — sDANNCE 3D pose keypoints (per-rat file, single-animal format)
- `pred`: **(89000, 3, 23)** float64 — (n_frames, xyz, n_keypoints) — **23 keypoints**
- `data`: (89000, 3, 23) float64 — all zeros (unused / training residuals)
- `p_max`: (89000, 23) float64 — per-keypoint confidence scores
- `sampleID`: (1, 89000) float64 — frame indices 0-based
- Note: 89000 frames vs 90000 in video (sDANNCE drops ~500 frames at each end)
- **Array is 3D (n_frames, 3, n_landmarks)** — single-animal DANNCE format, NOT 4D
- **Use `DANNCEInterface` (neuroconv main)**, not `SDANNCEInterface` (which expects 4D)
- Coordinate units: mm, same world frame as calibration/COM

### skin_contacts_symmetric.h5 — skin contact events
- `contacts`: (8934844, 2) int64 — [rat1_vertex_idx, rat2_vertex_idx] per event
- `frames`: (8934844,) int64 — frame index for each contact event (multiple per frame)
- `vertex_body_map`: (6880,) object — body-part label per vertex, e.g. `b'walker/foot_R'`
  → 6880 vertices total in the STAC body model; labels use format `walker/<part>`
- File size: 205 MB (many contact events per session)
- "symmetric" = touch identification repeated for both rats

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
| sDANNCE keypoints (pred) | `PoseEstimation` (ndx-pose ≥ 0.2.0) | 3D; uses `DANNCEInterface` from neuroconv main |
| sDANNCE confidence (p_max) | within PoseEstimationSeries | confidence field |
| COM 3D position | `SpatialSeries` | (n_frames, 3) in mm |
| Skin contacts | Custom `DynamicTable` | frame, rat1_vertex, rat2_vertex, body_part1, body_part2 |

**Note on ndx-pose for 3D:** ndx-pose ≥ 0.2.0 supports 3D PoseEstimation. Spyglass
compatibility confirmed via CatalystNeuro discussions.

## Phase 5: Interface Implementation Notes

Custom `SDANNCEInterface` wrapper is **removed**. The NeuroConv `DANNCEInterface`
(merged to main) now natively supports:
- `frametimes_file_path` parameter (was the wrapper's only added feature)
- `unit="millimeters"` default
- `stub_test=True` support in `add_to_nwbfile`
- `get_metadata` / `get_conversion_options_schema` overrides

The upstream `SDANNCEInterface` (also in neuroconv main) requires a 4D pred array
(n_frames, n_animals, 3, n_landmarks) in a single combined file — NOT compatible with
our per-rat 3D files.

Skeleton edges (23 edges from rat23.mat) are injected at conversion time from `constants.py`.

## Open Questions (as of 2026-04-29)
- [ ] Exact session start times of day (frametimes.npy gives elapsed seconds, not wall clock)
- [ ] Timezone of recording (Edinburgh? Harvard? — need to confirm lab location for sessions)
- [ ] CHD8, GRINB, NRXN1, LONGEVANS full session data (video + SDANNCE) — not yet in share
