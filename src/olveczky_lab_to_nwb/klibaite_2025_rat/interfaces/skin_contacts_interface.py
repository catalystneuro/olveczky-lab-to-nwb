"""
Skin contacts interface for the Klibaite 2025 - Rat social behavior conversion.

Reads ``skin_contacts_symmetric.h5`` and writes an ``AnnotatedEventsTable``
(ndx-events 0.2.2) into the NWB behavior processing module.

File layout (from inspection):
    contacts        (N, 2)  int64  — [rat1_vertex_idx, rat2_vertex_idx]
    frames          (N,)    int64  — video frame index for each contact event
    vertex_body_map (6880,) object — body-part label per vertex index,
                                    e.g. b'walker/foot_R'
"""

from pathlib import Path

import numpy as np
from pydantic import FilePath, validate_call

from neuroconv.basetemporalalignmentinterface import BaseTemporalAlignmentInterface


class SkinContactsInterface(BaseTemporalAlignmentInterface):
    """
    Skin-contact event interface for Klibaite 2025 - Rat sessions.

    Reads pairwise vertex-contact events computed from sDANNCE body meshes
    and writes them as an :class:`ndx_events.AnnotatedEventsTable` in
    ``nwbfile.processing["behavior"]``.

    Each row of the table is one unique ``(rat1_body_part, rat2_body_part)``
    contact type.  The ``event_times`` column (VectorIndex) holds all
    timestamps for that contact type, and indexed columns ``frame_indices``,
    ``rat1_vertices``, and ``rat2_vertices`` carry the per-event details.

    Parameters
    ----------
    contacts_file_path : FilePath
        Path to ``skin_contacts_symmetric.h5``.
    frametimes_file_path : FilePath
        Path to a ``frametimes.npy`` file so frame indices can be converted
        to timestamps (elapsed seconds).
    verbose : bool
    """

    @validate_call
    def __init__(
        self,
        contacts_file_path: FilePath,
        frametimes_file_path: FilePath,
        verbose: bool = False,
    ):
        self.contacts_file_path = Path(contacts_file_path)
        self.frametimes_file_path = Path(frametimes_file_path)
        self.verbose = verbose
        self._timestamps = None
        super().__init__(
            contacts_file_path=contacts_file_path,
            frametimes_file_path=frametimes_file_path,
            verbose=verbose,
        )

    # ------------------------------------------------------------------
    # Temporal alignment interface
    # ------------------------------------------------------------------

    def get_original_timestamps(self) -> np.ndarray:
        """Return per-contact timestamps derived from frame indices."""
        import h5py

        frametimes = np.load(str(self.frametimes_file_path))
        all_ts = frametimes[1]  # elapsed seconds, indexed by 0-based frame number

        with h5py.File(self.contacts_file_path, "r") as f:
            frames: np.ndarray = np.asarray(f["frames"])  # shape (N,)

        return all_ts[frames]

    def get_timestamps(self) -> np.ndarray:
        if self._timestamps is not None:
            return self._timestamps
        return self.get_original_timestamps()

    def set_aligned_timestamps(self, aligned_timestamps: np.ndarray) -> None:
        self._timestamps = np.asarray(aligned_timestamps, dtype="float64")

    # ------------------------------------------------------------------
    # Conversion
    # ------------------------------------------------------------------

    def get_conversion_options_schema(self) -> dict:
        schema = super().get_conversion_options_schema()
        schema["properties"]["stub_test"] = {
            "type": "boolean",
            "default": False,
            "description": "If True, include only the first 1000 contact events.",
        }
        return schema

    def add_to_nwbfile(self, nwbfile, metadata: dict | None = None, stub_test: bool = False) -> None:
        """
        Add a ``SkinContacts`` AnnotatedEventsTable to the behavior processing module.

        Table structure (one row per unique body-part contact type)
        ----------------------------------------------------------
        event_times : VectorIndex[float]
            Timestamps (seconds from session start) for each contact event
            of this type.
        label : str
            ``"<rat1_body_part> x <rat2_body_part>"``.
        event_description : str
            Human-readable description of the contact type.
        frame_indices : VectorIndex[int]
            0-based video frame indices, parallel to ``event_times``.
        rat1_vertices : VectorIndex[int]
            Vertex index on rat1's body mesh, parallel to ``event_times``.
        rat2_vertices : VectorIndex[int]
            Vertex index on rat2's body mesh, parallel to ``event_times``.
        """
        import h5py
        from collections import defaultdict
        from ndx_events import AnnotatedEventsTable
        from neuroconv.tools.nwb_helpers import get_module

        with h5py.File(self.contacts_file_path, "r") as f:
            contacts: np.ndarray = np.asarray(f["contacts"])  # (N, 2)
            frames: np.ndarray = np.asarray(f["frames"])  # (N,)
            vertex_body_map_raw: np.ndarray = np.asarray(f["vertex_body_map"])  # (6880,) object

        vertex_body_map = np.array([v.decode("utf-8") if isinstance(v, bytes) else str(v) for v in vertex_body_map_raw])

        rat1_vertices = contacts[:, 0]
        rat2_vertices = contacts[:, 1]

        if stub_test:
            n = 1000
            frames = frames[:n]
            rat1_vertices = rat1_vertices[:n]
            rat2_vertices = rat2_vertices[:n]

        timestamps = self.get_timestamps()
        if stub_test:
            timestamps = timestamps[:n]

        rat1_body_parts = vertex_body_map[rat1_vertices]
        rat2_body_parts = vertex_body_map[rat2_vertices]

        # Group per-event data by (rat1_body_part, rat2_body_part) contact type.
        groups: dict[tuple, dict] = defaultdict(
            lambda: {"event_times": [], "frame_indices": [], "rat1_vertices": [], "rat2_vertices": []}
        )
        for i in range(len(timestamps)):
            key = (rat1_body_parts[i], rat2_body_parts[i])
            groups[key]["event_times"].append(float(timestamps[i]))
            groups[key]["frame_indices"].append(int(frames[i]))
            groups[key]["rat1_vertices"].append(int(rat1_vertices[i]))
            groups[key]["rat2_vertices"].append(int(rat2_vertices[i]))

        table = AnnotatedEventsTable(
            name="SkinContacts",
            description=(
                "Pairwise body-part skin-contact events between two rats, "
                "computed from sDANNCE 3D body meshes.  Each row is one unique "
                "contact type (rat1_body_part × rat2_body_part pair).  "
                "Vertex indices reference the STAC body model (6880 vertices total); "
                "body-part labels use the format 'walker/<part_name>'."
            ),
        )

        # Define custom indexed columns before adding any rows.
        table.add_column(
            name="frame_indices",
            description="0-based video frame indices for each contact event of this type.",
            index=True,
        )
        table.add_column(
            name="rat1_vertices",
            description="Vertex index on rat1's body mesh for each contact event of this type.",
            index=True,
        )
        table.add_column(
            name="rat2_vertices",
            description="Vertex index on rat2's body mesh for each contact event of this type.",
            index=True,
        )

        for (bp1, bp2), group in sorted(groups.items()):
            table.add_event_type(
                label=f"{bp1} x {bp2}",
                event_description=f"Skin contact between rat1's {bp1} and rat2's {bp2}.",
                event_times=group["event_times"],
                frame_indices=group["frame_indices"],
                rat1_vertices=group["rat1_vertices"],
                rat2_vertices=group["rat2_vertices"],
            )

        behavior_module = get_module(nwbfile=nwbfile, name="behavior", description="processed behavioral data")
        behavior_module.add(table)
