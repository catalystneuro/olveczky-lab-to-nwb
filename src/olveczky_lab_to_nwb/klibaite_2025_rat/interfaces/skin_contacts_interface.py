"""
Skin contacts interface for the Klibaite 2025 - Rat social behavior conversion.

Reads ``skin_contacts_symmetric.h5`` and writes the events as a single shared
``pynwb.event.EventsTable`` into ``nwbfile.events``, via ``BaseEventsInterface``.
Each unique ``(rat1_body_part, rat2_body_part)`` pair is one event type,
discriminated by the table's ``event_type`` column.

File layout (from inspection):
    contacts        (N, 2)  int64  — [rat1_vertex_idx, rat2_vertex_idx]
    frames          (N,)    int64  — video frame index for each contact event
    vertex_body_map (6880,) object — body-part label per vertex index,
                                    e.g. b'walker/foot_R'
"""

import copy
from pathlib import Path

import numpy as np
from hdmf.common import MeaningsTable
from hdmf.container import Data
from pydantic import FilePath, validate_call

from neuroconv.datainterfaces.events.baseeventsinterface import BaseEventsInterface, _EventsData

# Module-level, single-slot cache of the raw (decoded, but not yet grouped) contents of one
# session's skin_contacts_symmetric.h5 + frametimes.npy. Contact files are 5-55M rows and shared
# by both rats of a session; without this cache, both rats' SkinContactsInterface instances (and
# repeated get_metadata() calls on the same instance, e.g. via neuroconv's metadata validation)
# would each independently re-read and re-decode the full file. Keeping only the most recently
# loaded session bounds memory to ~1 session's data regardless of how many sessions a batch run
# processes, as long as both rats of a session are converted from the same process (see
# `convert_all_sessions.safe_session_pair_to_nwb`).
_RAW_CACHE_KEY: tuple[str, str] | None = None
_RAW_CACHE_DATA: dict[str, np.ndarray] | None = None


def _load_raw_contacts_data(contacts_file_path: Path, frametimes_file_path: Path) -> dict[str, np.ndarray]:
    """Load and decode one session's skin-contacts file + frametimes, cached (see module docstring)."""
    global _RAW_CACHE_KEY, _RAW_CACHE_DATA

    key = (str(contacts_file_path), str(frametimes_file_path))
    if key == _RAW_CACHE_KEY:
        return _RAW_CACHE_DATA

    import h5py

    frametimes = np.load(str(frametimes_file_path))
    all_ts = frametimes[1]  # elapsed seconds, indexed by 0-based frame number

    with h5py.File(contacts_file_path, "r") as f:
        contacts: np.ndarray = np.asarray(f["contacts"])  # (N, 2)
        frames: np.ndarray = np.asarray(f["frames"])  # (N,)
        vertex_body_map_raw: np.ndarray = np.asarray(f["vertex_body_map"])  # (6880,) object

    vertex_body_map_decoded = np.array(
        [v.decode("utf-8") if isinstance(v, bytes) else str(v) for v in vertex_body_map_raw]
    )
    # Factorize the (only ~6880-entry) vertex->body-part map to small integer codes here, once,
    # so grouping below never has to hash/compare strings on the multi-million-row contacts
    # arrays -- only on this tiny per-vertex lookup table.
    unique_labels, vertex_body_part_codes = np.unique(vertex_body_map_decoded, return_inverse=True)
    rat1_vertices = contacts[:, 0]
    rat2_vertices = contacts[:, 1]

    data = {
        "frames": frames,
        "rat1_vertices": rat1_vertices,
        "rat2_vertices": rat2_vertices,
        "unique_labels": unique_labels,
        "vertex_body_part_codes": vertex_body_part_codes,
        "timestamps": all_ts[frames],
    }
    _RAW_CACHE_KEY, _RAW_CACHE_DATA = key, data
    return data


def _group_contacts_vectorized(
    *,
    timestamps: np.ndarray,
    frames: np.ndarray,
    rat1_vertices: np.ndarray,
    rat2_vertices: np.ndarray,
    unique_labels: np.ndarray,
    vertex_body_part_codes: np.ndarray,
) -> dict[str, _EventsData]:
    """Group per-occurrence contact data by ``(rat1_body_part, rat2_body_part)`` event type.

    Equivalent to a per-row Python loop building one list per group, but done with vectorized
    numpy operations on integer body-part codes (looked up per vertex, combined into one key,
    sorted, split on group boundaries) instead -- a per-row Python loop over the multi-million-row
    ``contacts`` arrays in this dataset dominated conversion time (see
    ``documentation/performance_report.md``).
    """
    if frames.shape[0] == 0:
        return {}

    n_labels = len(unique_labels)
    rat1_codes = vertex_body_part_codes[rat1_vertices]
    rat2_codes = vertex_body_part_codes[rat2_vertices]
    combined_codes = rat1_codes.astype(np.int64) * n_labels + rat2_codes.astype(np.int64)

    order = np.argsort(combined_codes, kind="stable")
    sorted_codes = combined_codes[order]
    unique_combined, group_starts = np.unique(sorted_codes, return_index=True)
    boundaries = np.append(group_starts, len(sorted_codes))
    unique_ids = np.array(
        [f"{unique_labels[code // n_labels]} x {unique_labels[code % n_labels]}" for code in unique_combined]
    )

    sorted_timestamps = timestamps[order]
    sorted_frames = frames[order]
    sorted_rat1_vertices = rat1_vertices[order]
    sorted_rat2_vertices = rat2_vertices[order]

    events_data_dict: dict[str, _EventsData] = {}
    for group_index, event_type_source_id in enumerate(unique_ids):
        start, stop = boundaries[group_index], boundaries[group_index + 1]
        events_data_dict[event_type_source_id] = _EventsData(
            event_type_source_id=event_type_source_id,
            timestamps=sorted_timestamps[start:stop].astype("float64"),
            payload={
                "frame_index": sorted_frames[start:stop].astype("int64"),
                "rat1_vertex": sorted_rat1_vertices[start:stop].astype("int64"),
                "rat2_vertex": sorted_rat2_vertices[start:stop].astype("int64"),
            },
        )
    return events_data_dict


def _humanize_body_part(raw_body_part: str) -> str:
    """Turn a raw ``vertex_body_map`` label into a human-readable body part name.

    Drops the ``"walker/"`` prefix and expands the ``_R``/``_L`` side suffix, e.g.
    ``"walker/foot_R"`` -> ``"right foot"``, ``"walker/toe_L"`` -> ``"left toe"``,
    ``"walker/jaw"`` -> ``"jaw"``.
    """
    name = raw_body_part.rsplit("/", 1)[-1]
    side = ""
    if name.endswith("_R"):
        side, name = "right ", name[: -len("_R")]
    elif name.endswith("_L"):
        side, name = "left ", name[: -len("_L")]
    return f"{side}{name.replace('_', ' ')}"


class SkinContactsInterface(BaseEventsInterface):
    """
    Skin-contact event interface for Klibaite 2025 - Rat sessions.

    Reads pairwise vertex-contact events computed from sDANNCE body meshes and writes them into a
    single shared ``SkinContacts`` ``EventsTable`` (one row per contact occurrence) in
    ``nwbfile.events``. Each unique ``(rat1_body_part, rat2_body_part)`` pair is one
    event type, named ``"<rat1_body_part> x <rat2_body_part>"`` and recorded in the table's
    ``event_type`` discriminator column; ``frame_index``, ``rat1_vertex``, and ``rat2_vertex`` columns
    carry the per-occurrence detail.

    Parameters
    ----------
    contacts_file_path : FilePath
        Path to ``skin_contacts_symmetric.h5``.
    frametimes_file_path : FilePath
        Path to a ``frametimes.npy`` file so frame indices can be converted to timestamps (elapsed
        seconds).
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
        self._timestamps = None
        self._stub_test = False
        super().__init__(
            contacts_file_path=contacts_file_path,
            frametimes_file_path=frametimes_file_path,
            verbose=verbose,
        )
        self.metadata_key = "skin_contacts"

    # ------------------------------------------------------------------
    # Temporal alignment
    # ------------------------------------------------------------------

    def get_original_timestamps(self) -> np.ndarray:
        """Return per-contact timestamps derived from frame indices."""
        raw = _load_raw_contacts_data(self.contacts_file_path, self.frametimes_file_path)
        return raw["timestamps"]

    def get_timestamps(self) -> np.ndarray:
        if self._timestamps is not None:
            return self._timestamps
        return self.get_original_timestamps()

    def set_aligned_timestamps(self, aligned_timestamps: np.ndarray) -> None:
        self._timestamps = np.asarray(aligned_timestamps, dtype="float64")

    # ------------------------------------------------------------------
    # Events
    # ------------------------------------------------------------------

    def _get_events_data_dict(self) -> dict[str, _EventsData]:
        if self._events_data_dict is not None:
            return self._events_data_dict

        raw = _load_raw_contacts_data(self.contacts_file_path, self.frametimes_file_path)
        frames = raw["frames"]
        rat1_vertices = raw["rat1_vertices"]
        rat2_vertices = raw["rat2_vertices"]
        timestamps = self.get_timestamps()

        if self._stub_test:
            n = 1000
            frames = frames[:n]
            rat1_vertices = rat1_vertices[:n]
            rat2_vertices = rat2_vertices[:n]
            timestamps = timestamps[:n]

        self._events_data_dict = _group_contacts_vectorized(
            timestamps=timestamps,
            frames=frames,
            rat1_vertices=rat1_vertices,
            rat2_vertices=rat2_vertices,
            unique_labels=raw["unique_labels"],
            vertex_body_part_codes=raw["vertex_body_part_codes"],
        )
        return self._events_data_dict

    def get_metadata(self):
        metadata = super().get_metadata()

        metadata["Events"]["EventTables"]["skin_contacts"] = {
            "table_name": "SkinContacts",
            "description": (
                "Pairwise body-part skin-contact events between two rats, computed from sDANNCE 3D "
                "body meshes. Vertex indices reference the STAC body model (6880 vertices total); "
                "the 'event_type' column names each contact type as '<rat1 body part> x <rat2 body part>' "
                "(e.g. 'right foot x left toe')."
            ),
        }

        event_types = metadata["Events"][self.metadata_key]["event_types"]
        for event_type_source_id in self._get_events_data_dict():
            raw_rat1_body_part, raw_rat2_body_part = event_type_source_id.split(" x ")
            rat1_body_part = _humanize_body_part(raw_rat1_body_part)
            rat2_body_part = _humanize_body_part(raw_rat2_body_part)
            event_types[event_type_source_id] = {
                "event_name": f"{rat1_body_part} x {rat2_body_part}",
                "event_description": f"Skin contact between rat1's {rat1_body_part} and rat2's {rat2_body_part}.",
                "table_metadata_key": "skin_contacts",
                "columns": {
                    "frame_index": {
                        "column_name": "frame_index",
                        "description": "0-based video frame index of the contact event.",
                    },
                    "rat1_vertex": {
                        "column_name": "rat1_vertex",
                        "description": "Vertex index on rat1's body mesh for the contact event.",
                    },
                    "rat2_vertex": {
                        "column_name": "rat2_vertex",
                        "description": "Vertex index on rat2's body mesh for the contact event.",
                    },
                },
            }
        return metadata

    def get_conversion_options_schema(self) -> dict:
        schema = super().get_conversion_options_schema()
        schema["properties"]["stub_test"] = {
            "type": "boolean",
            "default": False,
            "description": "If True, include only the first 1000 contact events.",
        }
        return schema

    def add_to_nwbfile(self, nwbfile, metadata: dict | None = None, stub_test: bool = False) -> None:
        # get_metadata() (built from the full, non-stubbed data) may already have run by the time this
        # is called, e.g. via NWBConverter.get_metadata(). Rebuild this interface's own event_types/
        # EventTables metadata under the requested stub_test so the declared event types always match
        # what _get_events_data_dict() actually produces (a mismatch would KeyError in the writer).
        self._stub_test = stub_test
        self._events_data_dict = None
        own_metadata = self.get_metadata()

        if metadata is None:
            metadata = own_metadata
        else:
            metadata = copy.deepcopy(metadata)
            metadata.setdefault("Events", {})
            metadata["Events"][self.metadata_key] = own_metadata["Events"][self.metadata_key]
            metadata["Events"].setdefault("EventTables", {})
            metadata["Events"]["EventTables"].update(own_metadata["Events"]["EventTables"])

        super().add_to_nwbfile(nwbfile, metadata=metadata)

    def _append_events_to_table(
        self,
        *,
        table,
        metadata: dict,
        event_type_source_ids: list,
        is_merge: bool,
    ) -> None:
        """Bulk-write this interface's events into ``table`` instead of row-by-row.

        ``BaseEventsInterface``'s default implementation calls ``table.add_row()`` once per event.
        For a table this large (millions of rows), that is not just slow but superlinear: each
        ``add_row`` call re-scans the whole column so far to check it isn't ragged
        (``hdmf.utils.is_ragged``), so total cost grows with the *square* of the row count --
        measured ~5,000 rows/s at 1K cumulative rows, dropping to ~180 rows/s by 26K (see
        ``documentation/performance_report.md``). Extrapolated to a multi-million-row session,
        that path does not finish in practical time.

        This override instead builds each column as one bulk array and writes it in a single call:
        ``DynamicTable.add_column(data=<full array>, check_ragged=False)`` for brand-new columns
        (a single O(N) construction, not one call per row), and a direct
        ``hdmf.container.Data.extend()`` call for the table's pre-existing ``id``/``timestamp``
        columns -- deliberately bypassing ``VectorData.extend()``, whose own implementation only
        does a real bulk extend for the exact ``VectorData`` class; for any subclass (which
        ``EventsTable``'s built-in ``timestamp`` column is) it silently falls back to one
        ``add_row`` call per element, i.e. exactly the slow path this method exists to avoid.

        Only handles the shape this interface actually produces: a brand-new table (SkinContacts
        never appends to a table another interface already wrote), and no per-event durations.
        Falls back to the general ``BaseEventsInterface`` implementation for anything else, so
        behavior stays correct even if that assumption ever stops holding.
        """
        event_types = metadata["Events"][self.metadata_key]["event_types"]
        event_data = self._get_events_data_dict()
        has_durations = any(event_data[source_id].durations is not None for source_id in event_type_source_ids)

        if len(table.id) != 0 or not is_merge or has_durations:
            super()._append_events_to_table(
                table=table,
                metadata=metadata,
                event_type_source_ids=event_type_source_ids,
                is_merge=is_merge,
            )
            return

        timestamps_parts: list[np.ndarray] = []
        event_type_parts: list[np.ndarray] = []
        column_value_parts: dict[str, list[np.ndarray]] = {}
        column_descriptions: dict[str, str] = {}
        described_types: list[tuple[str, str]] = []
        seen_event_names: set[str] = set()

        for event_type_source_id in event_type_source_ids:
            event = event_data[event_type_source_id]
            n_events = len(event.timestamps)
            if n_events == 0:
                continue
            entry = event_types[event_type_source_id]
            event_name = entry["event_name"]

            timestamps_parts.append(event.timestamps)
            event_type_parts.append(np.full(n_events, event_name, dtype=object))
            for field_source_id, column_spec in entry.get("columns", {}).items():
                column_name = column_spec["column_name"]
                column_descriptions.setdefault(column_name, column_spec.get("description", ""))
                column_value_parts.setdefault(column_name, []).append(np.asarray(event.payload[field_source_id]))

            event_description = entry.get("event_description", "")
            if event_description and event_name not in seen_event_names:
                described_types.append((event_name, event_description))
                seen_event_names.add(event_name)

        if not timestamps_parts:
            return

        timestamps = np.concatenate(timestamps_parts)
        event_type_values = np.concatenate(event_type_parts)
        column_values = {name: np.concatenate(parts) for name, parts in column_value_parts.items()}

        # Pre-sort by timestamp so the caller's post-write chronological re-sort (add_to_nwbfile,
        # BaseEventsInterface) sees an already-sorted table and skips its own (per-row, list-
        # comprehension-based) reordering pass.
        order = np.argsort(timestamps, kind="stable")
        timestamps = timestamps[order]
        event_type_values = event_type_values[order]
        column_values = {name: values[order] for name, values in column_values.items()}

        n_rows = len(timestamps)
        Data.extend(table.id, range(n_rows))
        Data.extend(table["timestamp"], timestamps.tolist())
        table.add_column(
            name="event_type",
            description="The event type of each event.",
            data=event_type_values.tolist(),
            check_ragged=False,
        )
        for column_name, values in column_values.items():
            table.add_column(
                name=column_name,
                description=column_descriptions[column_name],
                data=values.tolist(),
                check_ragged=False,
            )

        if described_types:
            meanings_table = MeaningsTable(target=table["event_type"], description="Meaning of each event type.")
            for event_name, event_description in described_types:
                meanings_table.add_row(value=event_name, meaning=event_description)
            table.add_meanings_table(meanings_table)
