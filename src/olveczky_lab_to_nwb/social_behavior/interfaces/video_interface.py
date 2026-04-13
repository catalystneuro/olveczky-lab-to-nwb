"""
Multi-camera video interface for the Olveczky Lab social behavior conversion.

Creates one NWB ImageSeries per camera with:
- external file link to the .mp4 (no data copied into the NWB file)
- per-frame timestamps loaded from frametimes.npy

Camera metadata (frame rate, resolution, model) is read from metadata.csv.
"""

from pathlib import Path

import numpy as np
import pandas as pd
from pydantic import DirectoryPath, validate_call

from neuroconv.basetemporalalignmentinterface import BaseTemporalAlignmentInterface
from neuroconv.utils import DeepDict


class OlveczkyVideoInterface(BaseTemporalAlignmentInterface):
    """
    Six-camera video interface for Olveczky Lab sessions.

    Reads MP4 files and frametimes.npy from the session ``videos/`` directory
    and writes one :class:`pynwb.image.ImageSeries` per camera into
    ``nwbfile.acquisition``.  Videos are stored as external file links — the
    .mp4 files are **not** embedded in the NWB file.

    Parameters
    ----------
    session_videos_dir : DirectoryPath
        Path to the ``videos/`` subdirectory of a session folder.  Expected
        layout::

            videos/
              Camera1/
                0.mp4
                frametimes.npy
                metadata.csv
              Camera2/
                ...

    n_cameras : int, default 6
        Number of cameras.  Cameras are assumed to be named ``Camera1``
        through ``Camera{n_cameras}``.
    verbose : bool
        Verbosity flag.
    """

    @validate_call
    def __init__(
        self,
        session_videos_dir: DirectoryPath,
        n_cameras: int = 6,
        verbose: bool = False,
    ):
        self.session_videos_dir = Path(session_videos_dir)
        self.n_cameras = n_cameras
        self.verbose = verbose
        self._timestamps = None

        # Verify expected structure and read Camera1 metadata as the canonical source.
        cam1_dir = self.session_videos_dir / "Camera1"
        if not cam1_dir.exists():
            raise FileNotFoundError(f"Expected Camera1 directory not found in {self.session_videos_dir}")

        meta_path = cam1_dir / "metadata.csv"
        self._camera_metadata = pd.read_csv(meta_path, header=None, index_col=0).squeeze("columns")

        super().__init__(session_videos_dir=session_videos_dir, verbose=verbose)

    # ------------------------------------------------------------------
    # Temporal alignment interface
    # ------------------------------------------------------------------

    def get_original_timestamps(self) -> np.ndarray:
        """Return timestamps from Camera1 frametimes.npy (elapsed seconds)."""
        frametimes = np.load(str(self.session_videos_dir / "Camera1" / "frametimes.npy"))
        return frametimes[1]  # row 1 = elapsed seconds

    def get_timestamps(self) -> np.ndarray:
        if self._timestamps is not None:
            return self._timestamps
        return self.get_original_timestamps()

    def set_aligned_timestamps(self, aligned_timestamps: np.ndarray) -> None:
        self._timestamps = np.asarray(aligned_timestamps, dtype="float64")

    # ------------------------------------------------------------------
    # Metadata
    # ------------------------------------------------------------------

    def get_metadata(self) -> DeepDict:
        metadata = super().get_metadata()

        frame_rate = float(self._camera_metadata.get("frameRate", 50))
        frame_width = int(self._camera_metadata.get("frameWidth", 1920))
        frame_height = int(self._camera_metadata.get("frameHeight", 1200))
        camera_model = str(self._camera_metadata.get("cameraModel", "Basler"))

        metadata["Behavior"]["Videos"] = {
            f"Camera{i}": {
                "name": f"VideoCamera{i}",
                "description": (
                    f"Video from camera {i} of {self.n_cameras}. "
                    f"Camera model: {camera_model}. "
                    f"Resolution: {frame_width}x{frame_height} px at {frame_rate:.0f} fps. "
                    "External file link — the .mp4 is not embedded in the NWB file."
                ),
            }
            for i in range(1, self.n_cameras + 1)
        }
        return metadata

    # ------------------------------------------------------------------
    # Conversion
    # ------------------------------------------------------------------

    def get_conversion_options_schema(self) -> dict:
        schema = super().get_conversion_options_schema()
        schema["properties"]["stub_test"] = {
            "type": "boolean",
            "default": False,
            "description": "If True, include only the first 100 frames of timestamps.",
        }
        return schema

    def add_to_nwbfile(self, nwbfile, metadata: dict | None = None, stub_test: bool = False) -> None:
        """
        Add one ImageSeries per camera to ``nwbfile.acquisition``.

        Parameters
        ----------
        nwbfile : NWBFile
        metadata : dict, optional
        stub_test : bool
            If True, include only the first 100 frames of timestamps.
        """
        from pynwb.image import ImageSeries

        from neuroconv.utils import DeepDict

        default_metadata = DeepDict(self.get_metadata())
        if metadata:
            default_metadata.deep_update(metadata)

        base_timestamps = self.get_timestamps()
        if stub_test:
            base_timestamps = base_timestamps[:100]

        for i in range(1, self.n_cameras + 1):
            cam_dir = self.session_videos_dir / f"Camera{i}"
            video_path = cam_dir / "0.mp4"

            if not video_path.exists():
                if self.verbose:
                    print(f"  [VideoInterface] Camera{i}: video file not found, skipping.")
                continue

            # Use per-camera frametimes if they differ (all cameras are synchronised
            # but we load independently to be safe).
            ft_path = cam_dir / "frametimes.npy"
            if ft_path.exists():
                frametimes = np.load(str(ft_path))
                cam_timestamps = frametimes[1]
            else:
                cam_timestamps = base_timestamps

            if stub_test:
                cam_timestamps = cam_timestamps[:100]

            cam_meta = default_metadata["Behavior"]["Videos"].get(f"Camera{i}", {})
            image_series = ImageSeries(
                name=cam_meta.get("name", f"VideoCamera{i}"),
                description=cam_meta.get("description", f"Video from camera {i}."),
                external_file=[str(video_path)],
                format="external",
                timestamps=cam_timestamps,
                unit="n.a.",
            )
            nwbfile.add_acquisition(image_series)
