# Data streams

Each NWB file holds the streams below, for one rat of the session. `session_to_nwb` in `convert_session.py` adds
each one from the session folder (see [Data organization](data_organization.md)), and `Klibaite2025NWBConverter` in
`nwbconverter.py` registers one interface slot per stream.

| Stream | Slot | Interface | Source file | Location in the NWB file |
| --- | --- | --- | --- | --- |
| 3D pose of the rat | `DANNCE` | `DANNCEConverter` (NeuroConv) | `SDANNCE*/bsl0.5_FM_rat<N>/save_data_AVG0.mat` | `processing/behavior/PoseEstimationSDANNCE` |
| 6 camera videos and calibrated cameras | `DANNCE` | `DANNCEConverter` (NeuroConv) | `videos/`, `calibration/` | `acquisition/VideoCamera<1..6>`, `general/devices` |
| skin contacts between the two rats (when available) | `SkinContacts` | `SkinContactsInterface` | `social_touch/.../skin_contacts_symmetric.h5` | `events/SkinContacts` |
| epoch and task | `TaskEpoch` | `TaskEpochInterface` | `videos/Camera1/frametimes.npy` | `intervals/epochs`, `processing/tasks/task_table` |

The interfaces of this package are in `interfaces/`.

## Pose and video

`DANNCEConverter` writes:

- the 3D pose of the rat: a `MultiCameraPoseEstimation` container with one `PoseEstimationSeries` per landmark of
  the rat23 skeleton, in millimeters, with the confidence of each sample. The skeleton
  (`Skeletons/SkeletonPoseEstimationSDANNCE_Rat<N>`) lists the 23 landmarks and the 23 edges between them, and is
  linked to the subject of the file;
- the 6 camera videos as external files: the NWB file holds the path to each `0.mp4`, relative to the NWB file, and
  its frame times from `frametimes.npy`;
- one `CalibratedCamera` device per camera, with its intrinsics, extrinsics and distortion from `calibration/`, and
  the camera model from `metadata.csv`.

The pose of the other rat of the session is in the other NWB file of the session (same session ID).

## Skin contacts

`SkinContactsInterface` writes one `EventsTable`, `SkinContacts`, with one row per pair of touching vertices and
frame:

| Column | Content |
| --- | --- |
| `timestamp` | time of the contact, in seconds |
| `event_type` | contact type, `<rat1 body part> x <rat2 body part>`, for example `right foot x left toe` |
| `frame_index` | video frame of the contact (0-based) |
| `rat1_vertex`, `rat2_vertex` | the touching vertex of each rat's body mesh (6880 vertices) |

A meanings table attached to `event_type` describes each contact type and annotates it with HED (see
[Metadata](metadata.md#hed)). The contacts concern both rats, so both NWB files of a session hold the same table;
columns are named after rat1 and rat2, not after the subject of the file.

The body parts are those of the STAC body mesh: `vertebra_C<N>` are caudal (tail) vertebrae, `vertebra_<N>` lumbar
vertebrae and `vertebra_axis` the second cervical vertebra.

## Epoch and task

`TaskEpochInterface` writes, in the layout [Spyglass](https://lorenfranklab.github.io/spyglass/) reads:

- one epoch spanning the recording (first to last Camera1 frame time), tagged `01_social_encounter`;
- a `task_table` in the `tasks` processing module with one row: the task name, description and environment from
  `general_metadata.yaml`, the IDs of the 6 cameras, the epoch number and a `HED` annotation;
- the HED schema version and the lab's HED definitions, in `general/hed_schema` (`HedLabMetaData`).

## Time alignment

All times are seconds from the start of the recording, on the clock of the cameras' `frametimes.npy` (row 1 of each
file). The cameras are triggered together at 50 fps.

- Videos: each camera's frames are timed by that camera's `frametimes.npy`.
- Pose: each prediction is timed by Camera1's `frametimes.npy` at the frame of its `sampleID`
  (`temporally_align_data_interfaces` in `nwbconverter.py`). The conversion checks that every sampleID is a frame of
  Camera1. The pose times are regular, so NeuroConv stores them as a start time and a rate.
- Skin contacts: each contact is timed by Camera1's `frametimes.npy` at its frame.
- Epoch: Camera1's first and last frame times.

The session start time is the date of the session folder at midnight in America/New_York, since the time of day
was not recorded.

## Reading a file

```python
from pynwb import NWBHDF5IO

with NWBHDF5IO("sub-SCN2A-M1_ses-day-1-social-M1-M2-20220922.nwb", "r") as io:
    nwbfile = io.read()
    pose = nwbfile.processing["behavior"]["PoseEstimationSDANNCE"]
    snout = pose.pose_estimation_series["PoseEstimationSeriesSnout"]
    positions = snout.data[:]  # (n_samples, 3), millimeters
    contacts = nwbfile.events["SkinContacts"].to_dataframe()
```

The notebooks in [notebooks/](../../../../notebooks/) show each stream, for one rat and for both rats of a session.
Files on DANDI can also be opened in the browser with [Neurosift](https://neurosift.app).
