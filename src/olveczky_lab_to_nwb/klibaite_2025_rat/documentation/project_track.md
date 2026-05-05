# SFARI ARC – Olveczky Lab Conversion Progress

## Social Behavior / sDANNCE Dataset Conversion Progress

**Progress: 0 / TBD**

---

## Pre-Conversion

- [x] Repo Setup (local; GitHub remote pending)
- [x] Initial Inspection and Notes: Data streams, directory structure, session naming — see [`conversion_notes.md`](conversion_notes.md)
- [x] Phase 2 byte-level inspection of `.mat`, `.npy`, `.h5` streams ([`inspect_data.py`](inspect_data.py))
- [x] Phase 3: all metadata YAMLs drafted ([`social_behavior_metadata.yaml`](src/olveczky_lab_to_nwb/social_behavior/social_behavior_metadata.yaml))
- [x] Phase 4: synchronization analysis — single clock (frametimes.npy row 1), sampleID indexing confirmed
- [x] Phase 5: all 3 conversion interfaces written and stub tested (SCN2A SOC1 — all streams pass)
- [x] Phase 6: NWBInspector run on stub — 1 pending warning (`check_image_series_external_file_relative`), no structural errors
- [x] Confirm `save_data_AVG.mat` format: 3D pred (n_frames, 3, n_landmarks), per-rat single-animal output → use `DANNCEInterface`
- [x] Confirm frametimes.npy layout: shape (2, 90000), row 1 = elapsed seconds
- [x] Confirm skin_contacts_symmetric.h5 schema (frames, contacts, vertex_body_map)
- [x] Lab metadata reply received (2026-04-29) — keypoint names, DOB source, WT/KO mapping, publication DOI, Dataverse URL, experimenter list, SFARI grant
- [x] Integrate lab reply: constants.py (23 rat23 joints + edges), subject_metadata.py (xlsx loaders), updated metadata YAML and converter
- [ ] **Pending** — per-rat exact weights, per-rat sex, exact session start times of day
- [ ] Acquire full session data for CHD8, GRINB, NRXN1, LONGEVANS (currently contacts-only in share)
- [x] Create GitHub remote for this repo

---

## Project 1: Social Behavior (Klibaite et al. 2025 — published line)

- Convert all sessions (PR TBD)

### Behavior

#### Conversion with Spyglass compatibility

- 3D pose estimation, 23 joints, sDANNCE output, per-rat (`DANNCEInterface`) → `PoseEstimation` (ndx-pose ≥ 0.2.0) (PR TBD)
- rat23 skeleton (Snout … FootR) with 23 edges from Label3D (PR TBD)
- 6-camera video (`OlveczkyVideoInterface`) → 6 `ImageSeries` in `acquisition` (PR TBD)
- Light-cycle / session timing — `frametimes.npy` timestamps applied to all streams (PR TBD)

#### Cohorts with full data (video + sDANNCE + skin contacts)

- SCN2A: SOC1, SOC2, SOC3
- ARID1B: SOC1, SOC2, SOC3

#### Cohorts with skin contacts only (no video/sDANNCE in share yet)

- CHD8, GRINB, NRXN1, LONGEVANS

#### Ingest in Spyglass

- PoseEstimation (ndx-pose)
- ImageSeries (external links)

### External Stimuli

*None — naturalistic social behavior recording (no programmed stimulus).*

### Ephys

*None in current share. Future placeholder: flexible probes (256ch, PFC), Neuropixels, tetrodes.*

### Events

#### Conversion with Spyglass compatibility

- Skin contacts (`SkinContactsInterface`) → `DynamicTable` in `processing/behavior` (PR TBD)
  - Columns: frame_index, timestamp, rat1_vertex, rat2_vertex, rat1_body_part, rat2_body_part

#### Ingest in Spyglass

- Skin contact table

### Temporal Alignment

#### Conversion with Spyglass compatibility

- `frametimes.npy` row 1 (elapsed seconds from session start) used as timestamps for all streams
- sDANNCE `sampleID` (0-based frame indices) used to index frametimes → per-prediction timestamps
- `session_start_time` populated with UTC date only (exact time of day pending lab)

#### Ingest in Spyglass

- Aligned pose + contact timestamps

### Post-Conversion

- [x] NWBInspector validation (stub) — 1 `check_image_series_external_file_relative` warning only
- [ ] Setup Dandiset (public — line is published)
- [ ] Example Notebooks (streaming + Spyglass query demo)

---

## Project 2: Future Ephys + Behavior (TBD)

*Name/cohort to be confirmed when ephys data lands in share.*

- Flexible probes (256ch, PFC) → SpikeGLX/OpenEphys interfaces
- Neuropixels → SpikeGLX interface
- Tetrodes (raw + snippeted)
- Behavior (video + sDANNCE) from same sessions

### Post-Conversion
- Setup Dandiset (embargoed until publication)
- Inspection / Validation
- README / Documentation
- Example Notebooks

---

## Project 3: Future Fiber Photometry (TBD)

*Planned collection; not yet in share.*

- Fiber photometry → FiberPhotometryInterface
- Combined with social behavior sessions (same arena)

### Post-Conversion
- Setup Dandiset (embargoed until collection complete)
- Inspection / Validation
- Example Notebooks

---

## Cross-Project Deliverables (Aim 4 — Demonstrate NWB usage)

- Tutorial notebook: read converted NWB locally
- Tutorial notebook: stream NWB directly from DANDI
- Tutorial notebook: query data via Spyglass
- Lab-facing README and onboarding doc
