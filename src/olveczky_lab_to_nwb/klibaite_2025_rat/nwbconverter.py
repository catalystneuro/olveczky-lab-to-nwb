"""Primary NWBConverter class for the Klibaite 2025 Rat social behavior conversion."""

from pathlib import Path

import numpy as np
from neuroconv import NWBConverter
from neuroconv.datainterfaces import DANNCEInterface, ExternalVideoInterface

from olveczky_lab_to_nwb.klibaite_2025_rat.interfaces import SkinContactsInterface

# One ExternalVideoInterface entry per camera
_CAMERA_NAMES = [f"VideoCamera{i}" for i in range(1, 7)]


class Klibaite2025NWBConverter(NWBConverter):
    """Primary conversion class for the Klibaite 2025 Rat social behavior dataset.

    Data streams:
    - DANNCE: 3D pose estimation (save_data_AVG.mat)
    - SkinContacts (optional): pairwise vertex contact events (skin_contacts_symmetric.h5)
    - VideoCamera1–6: 6-camera behavioral video (.mp4 per camera, external link)

    Temporal alignment:
    - Video timestamps: loaded from per-camera frametimes.npy (row 1 = elapsed seconds)
    - DANNCE and SkinContacts load their own timestamps from frametimes.npy directly
    """

    data_interface_classes = dict(
        DANNCE=DANNCEInterface,
        SkinContacts=SkinContactsInterface,
        VideoCamera1=ExternalVideoInterface,
        VideoCamera2=ExternalVideoInterface,
        VideoCamera3=ExternalVideoInterface,
        VideoCamera4=ExternalVideoInterface,
        VideoCamera5=ExternalVideoInterface,
        VideoCamera6=ExternalVideoInterface,
    )

    def temporally_align_data_interfaces(self, metadata=None, conversion_options=None):
        """Set per-camera timestamps from frametimes.npy files."""

        for cam_key in _CAMERA_NAMES:
            if cam_key not in self.data_interface_objects:
                continue
            video_interface = self.data_interface_objects[cam_key]
            video_file_path = Path(video_interface.source_data["file_paths"][0])
            camera_dir = video_file_path.parent
            frametimes_file_path = camera_dir / "frametimes.npy"
            frametimes = np.load(str(frametimes_file_path))
            cam_timestamps = frametimes[1]  # row 1 = elapsed seconds
            # ExternalVideoInterface expects a list-of-arrays, one per video file
            video_interface.set_aligned_timestamps([cam_timestamps])
