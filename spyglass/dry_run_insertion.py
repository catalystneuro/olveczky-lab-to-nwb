"""Dry run: insert an UNMODIFIED standard NWB file (ndx-pose 0.4.0) with Spyglass's own
`insert_sessions()` and report what populated.

Nothing Spyglass-specific is added to the file: the point is that Spyglass itself
accepts the standard file (cameras, multicamera pose, videos, skin-contact events).
Run inside the `spyglass-olveczky` WSL env:

    cd /mnt/c/Users/algab/CatalystNeuro/olveczky-lab-to-nwb/spyglass
    python dry_run_insertion.py <file.nwb in the Spyglass raw dir>
"""

import sys
import traceback
from pathlib import Path

import datajoint as dj

dj.config.load(str(Path(__file__).with_name("dj_local_conf.json")))  # BEFORE spyglass
dj.conn(use_tls=False)

import spyglass.common as sgc  # noqa: E402
import spyglass.data_import as sgi  # noqa: E402
from spyglass.common.common_usage import InsertError  # noqa: E402
from spyglass.position.v1.imported_multicam_pose import (  # noqa: E402
    CameraCalibration,
    ImportedMultiCameraPose,
)
from spyglass.position.v1.imported_pose import ImportedPose  # noqa: E402
from spyglass.settings import raw_dir  # noqa: E402
from spyglass.utils.nwb_helper_fn import get_nwb_copy_filename  # noqa: E402

nwb_file_name = sys.argv[1]
assert (Path(raw_dir) / nwb_file_name).exists(), f"{nwb_file_name} not in {raw_dir}"
key = {"nwb_file_name": get_nwb_copy_filename(nwb_file_name)}

# Nwbfile is keyed on the COPY filename; clean up a previous run by that name.
if sgc.Nwbfile & key:
    (sgc.Nwbfile & key).delete(safemode=False)
(InsertError & key).delete(safemode=False)

print("=" * 70, f"\ninsert_sessions({nwb_file_name}, raise_err=True)\n", "=" * 70, sep="")
try:
    sgi.insert_sessions(nwb_file_name, rollback_on_fail=False, raise_err=True)
    print("insert_sessions() completed with no exception.")
except Exception as exc:  # noqa: BLE001 -- report everything
    print(f"insert_sessions() RAISED {type(exc).__name__}: {exc}")
    traceback.print_exc()

print("\n===== ROW COUNTS (this file unless noted)")
for table in (sgc.Session, sgc.IntervalList, sgc.TaskEpoch, sgc.VideoFile, CameraCalibration,
              ImportedMultiCameraPose, ImportedMultiCameraPose.BodyPart,
              ImportedMultiCameraPose.Camera, ImportedPose, sgc.ImportedEvents):
    print(f"{table.__name__:<24} {len(table & key)}")
for table in (sgc.CameraDevice, sgc.Task):
    print(f"{table.__name__ + ' (whole DB)':<24} {len(table())}")
print(f"{'InsertError':<24} {len(InsertError & key)}")
for row in (InsertError & key).fetch(as_dict=True):
    print(f"  {row['table']}: {row['error_type']}: {row['error_raw'][:500]}")

print("\n===== DETAILS")
print(sgc.CameraDevice.fetch(format="frame"))
print("intervals:", list((sgc.IntervalList & key).fetch("interval_list_name")))
print((sgc.TaskEpoch & key).fetch("task_name", "interval_list_name", "camera_names", as_dict=True))
print((sgc.VideoFile & key).fetch("camera_name", "video_file_num", as_dict=True))
print((ImportedMultiCameraPose.Camera & key).fetch("camera_name", "video_file_num", as_dict=True))
if ImportedMultiCameraPose & key:
    pose = ImportedMultiCameraPose & key
    print(pose.fetch("pose_estimation_name", "source_software", "scorer", as_dict=True))
    df = pose.fetch_pose_dataframe()
    print("pose:", df.shape, list(df.columns[:4]))
    print("skeleton nodes:", len(pose.fetch_skeleton()["nodes"]))
    print("calibrations:", {k: sorted(v) for k, v in list(pose.fetch_calibrations().items())[:1]})
    print("video paths:", list(pose.fetch_video_paths().items())[:1])
if sgc.ImportedEvents & key:
    print((sgc.ImportedEvents & key).fetch("events_name", "n_events", as_dict=True))
