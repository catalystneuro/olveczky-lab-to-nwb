"""
sDANNCE interface for the Olveczky Lab social behavior conversion.

Wraps the NeuroConv DANNCEInterface to load per-frame timestamps from the
lab's frametimes.npy files rather than reading them from the video.

frametimes.npy layout (shape: 2 × n_frames):
    row 0 — 1-based frame indices
    row 1 — elapsed seconds from session start
"""

from pathlib import Path

import numpy as np
from pydantic import FilePath, validate_call

from neuroconv.datainterfaces.behavior.dannce.danncedatainterface import DANNCEInterface


# Placeholder keypoint names for the standard sDANNCE 23-joint rat skeleton.
# UPDATE these once the lab confirms the ordered list (see metadata_request_email.md).
SDANNCE_LANDMARK_NAMES_PLACEHOLDER = [f"landmark_{i}" for i in range(23)]


class SDANNCEInterface(DANNCEInterface):
    """
    sDANNCE 3D pose estimation interface for Olveczky Lab.

    Extends :class:`DANNCEInterface` with support for loading timestamps
    directly from a ``frametimes.npy`` file (the Olveczky lab standard) rather
    than from video metadata or a fixed sampling rate.

    Parameters
    ----------
    file_path : FilePath
        Path to the SDANNCE prediction file (``save_data_AVG.mat``).
    frametimes_file_path : FilePath
        Path to ``frametimes.npy`` for the corresponding camera (e.g.,
        ``videos/Camera1/frametimes.npy``).  Row 1 of this array contains
        per-frame timestamps in seconds from session start.
    landmark_names : list of str, optional
        Ordered keypoint names matching the 23 joints in the ``pred`` array.
        Defaults to ``["landmark_0", …, "landmark_22"]`` until the lab
        provides the official list.
    subject_name : str
        Identifier for this rat within the session (``"rat1"`` or ``"rat2"``).
    verbose : bool
        Verbosity flag passed to the parent class.
    """

    @validate_call
    def __init__(
        self,
        file_path: FilePath,
        frametimes_file_path: FilePath,
        landmark_names: list[str] | None = None,
        subject_name: str = "rat1",
        verbose: bool = False,
    ):
        if landmark_names is None:
            landmark_names = SDANNCE_LANDMARK_NAMES_PLACEHOLDER

        pose_estimation_metadata_key = f"PoseEstimationSDANNCE{subject_name.capitalize()}"

        super().__init__(
            file_path=file_path,
            landmark_names=landmark_names,
            subject_name=subject_name,
            pose_estimation_metadata_key=pose_estimation_metadata_key,
            verbose=verbose,
        )

        # Load timestamps from frametimes.npy and index by SDANNCE sampleID.
        frametimes = np.load(str(frametimes_file_path))  # shape (2, n_video_frames)
        all_timestamps = frametimes[1]  # row 1 = elapsed seconds, 0-based columns
        frame_indices = self._sample_id.astype(int)  # 0-based, shape (n_sdannce_frames,)
        aligned_timestamps = all_timestamps[frame_indices]
        self.set_aligned_timestamps(aligned_timestamps)

    def get_metadata(self) -> dict:
        metadata = super().get_metadata()
        # NWB Inspector requires "millimeters" not the abbreviation "mm".
        container_key = self.pose_estimation_metadata_key
        series_meta = (
            metadata.get("PoseEstimation", {})
            .get("PoseEstimationContainers", {})
            .get(container_key, {})
            .get("PoseEstimationSeries", {})
        )
        for series in series_meta.values():
            if series.get("unit") == "mm":
                series["unit"] = "millimeters"
        return metadata

    def get_conversion_options_schema(self) -> dict:
        schema = super().get_conversion_options_schema()
        schema["properties"]["stub_test"] = {
            "type": "boolean",
            "default": False,
            "description": "If True, write only the first 100 frames for quick testing.",
        }
        return schema

    def add_to_nwbfile(self, nwbfile, metadata: dict | None = None, stub_test: bool = False) -> None:
        if stub_test:
            # Temporarily truncate internal data arrays before calling the parent.
            _pred, _pmax, _sid, _ts = self._pred, self._p_max, self._sample_id, self._timestamps
            n = 100
            self._pred = _pred[:n]
            self._p_max = _pmax[:n]
            self._sample_id = _sid[:n]
            self._timestamps = _ts[:n] if _ts is not None else None
            try:
                super().add_to_nwbfile(nwbfile=nwbfile, metadata=metadata)
            finally:
                self._pred, self._p_max, self._sample_id, self._timestamps = _pred, _pmax, _sid, _ts
        else:
            super().add_to_nwbfile(nwbfile=nwbfile, metadata=metadata)
