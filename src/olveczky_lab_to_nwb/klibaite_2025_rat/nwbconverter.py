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
