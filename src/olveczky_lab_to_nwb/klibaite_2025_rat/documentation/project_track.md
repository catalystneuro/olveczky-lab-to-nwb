# SFARI ARC – Olveczky Lab Conversion Progress

## Social Behavior / sDANNCE Dataset Conversion Progress


---

## Batch Conversion Status (stub test, 2026-07-28)

All 6 cohorts (SCN2A, ARID1B, CHD8, GRINB, NRXN1, LONGEVANS) discovered and stub-converted
(100 frames/session) via `convert_all_sessions.py`. 468 unique sessions / 936 rat-sessions found.

| Cohort | Sessions | Rat-sessions OK | Rat-sessions failed | Notes |
|---|---|---|---|---|
| SCN2A | 45 | 90/90 | 0 | Clean |
| ARID1B | 86 | 166/172 | 6 | 1 session missing sDANNCE data; 2 sessions blocked by stray macOS `._0.mp4` files |
| CHD8 | 84 | 168/168 | 0 | Clean (no Genotype column in rat log — defaults to "unknown") |
| GRINB | 45 | 90/90 | 0 | Clean after fixing `GRINB`/`GRIN2B` cohort-name mismatch |
| NRXN1 | 84 | 168/168 | 0 | Clean (no Genotype column in rat log — defaults to "unknown"); 3 transient MemoryErrors resolved on retry at lower parallelism |
| LONGEVANS | 124 | 115/248 | 133 | SOC1–5 almost entirely missing sDANNCE pose data (video+calibration only); SOC6–9 essentially complete |

**Fixes applied to the pipeline this session** (see commit history / `subject_metadata.py`,
`convert_all_sessions.py`):
- `STRAINS` dict keys and rat-log sheet-name lookup aligned to data-share cohort directory names
  (`GRINB` not `GRIN2B`; `LONGEVANS` mapped to sheet `LongEvans` via `SHEET_NAME_OVERRIDES`).
- `get_subject_metadata()` no longer raises on missing columns (Genotype, DOB, Cage, Mother,
  Markings) — degrades individual fields to `"unknown"`/omitted instead of discarding the whole
  record (previously a NRXN1/CHD8/LONGEVANS rat would silently lose even its `strain`).
- Session discovery no longer crashes an entire cohort when one session folder doesn't match the
  two-rat naming pattern (LONGEVANS has solo baseline/`_AMP` folders); non-`SOC<N>` encounter
  folders and unparseable session folders are now skipped with a warning.
- LONGEVANS skin-contacts path fixed: was reconstructing `{cohort}_{encounter}` (→
  `LONGEVANS_SOC6`), but the actual `social_touch/` folder is `LONGEVANS_M_SOC6` — now uses the
  raw encounter folder name.

**Open items requiring lab input:**
- LONGEVANS SOC1–5: no `SDANNCE`/`SDANNCE_x2` folder at all in ~132 sessions — pose pipeline
  apparently never uploaded for these rounds (see `metadata_request_email.md` candidates).
- ARID1B `2022_10_20_M11_M6`: missing sDANNCE data (only SLURM batch logs present).
- Rat IDs `M8_EXTRA` (ARID1B) and `M5_take2` (LONGEVANS) appear in session folder names but have
  no row in `ugne_rat_log.xlsx`.
- ARID1B `2022_10_21_M2_M6` and `2022_10_21_M7_M8_EXTRA`: stray macOS `._0.mp4` AppleDouble
  sidecar files in `videos/Camera1/` are picked up by neuroconv's `DANNCEConverter` as a second
  video segment and fail to open — needs either share cleanup (strip `._*` files) or an upstream
  neuroconv fix to filter hidden files during video discovery.

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

- SCN2A, ARID1B, CHD8, GRINB, NRXN1, LONGEVANS

#### Ingest in Spyglass

- PoseEstimation (ndx-pose)
- ImageSeries (external links)

### External Stimuli

*None — naturalistic social behavior recording (no programmed stimulus).*

### Ephys

*None in current share. Future placeholder: flexible probes (256ch, PFC), Neuropixels, tetrodes.*

### Events

#### Conversion with Spyglass compatibility

- Skin contacts (`SkinContactsInterface`, subclasses `BaseEventsInterface`) → `pynwb.event.EventsTable`
  named `SkinContacts` in `nwbfile.events` (`ndx_events.AnnotatedEventsTable` is deprecated)
  - Columns: timestamp, event_type (`"<rat1_body_part> x <rat2_body_part>"`), frame_index,
    rat1_vertex, rat2_vertex

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

- [x] NWBInspector validation (stub)
- [x] Setup Dandiset - [DANDI:001936](https://dandiarchive.org/dandiset/001936/draft)
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
