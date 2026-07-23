"""Primary NWBConverter class for the Klibaite 2025 Rat social behavior conversion."""

from pathlib import Path

import numpy as np
from neuroconv import NWBConverter
from neuroconv.converters import DANNCEConverter

from olveczky_lab_to_nwb.klibaite_2025_rat.interfaces import SkinContactsInterface


class Klibaite2025NWBConverter(NWBConverter):
    """Primary conversion class for the Klibaite 2025 Rat social behavior dataset.

    Data streams:
    - DANNCE: 3D pose estimation (save_data_AVG.mat) combined with the 6-camera behavioral video
      (.mp4 per camera, external link) via ``DANNCEConverter``, which links each camera's source
      video and calibrated Device (from calibration/hires_camN_params.mat) automatically.
    - SkinContacts (optional): pairwise vertex contact events (skin_contacts_symmetric.h5)

    Temporal alignment:
    - Video timestamps: loaded from per-camera frametimes.npy (row 1 = elapsed seconds)
    - DANNCE and SkinContacts load their own timestamps from frametimes.npy directly
    """

    data_interface_classes = dict(
        DANNCE=DANNCEConverter,
        SkinContacts=SkinContactsInterface,
    )

    def temporally_align_data_interfaces(self, metadata=None, conversion_options=None):
        """Set per-camera timestamps from frametimes.npy files."""

        dannce_converter = self.data_interface_objects.get("DANNCE")
        if dannce_converter is None:
            return

        for interface_name, video_interface in dannce_converter.data_interface_objects.items():
            if not interface_name.startswith("Video"):
                continue
            video_file_path = Path(video_interface.source_data["file_paths"][0])
            camera_dir = video_file_path.parent
            frametimes_file_path = camera_dir / "frametimes.npy"
            frametimes = np.load(str(frametimes_file_path))
            cam_timestamps = frametimes[1]  # row 1 = elapsed seconds
            # ExternalVideoInterface expects a list-of-arrays, one per video file
            video_interface.set_aligned_timestamps([cam_timestamps])
