# Building a new conversion pipeline

This page outlines how to convert a new experiment to NWB, using this repository as an example. It builds on
[The conversion pipeline](conversion_pipeline.md), which describes the parts of a conversion.

## 1. List the data and metadata

Write down, for one session:

- the files of each data stream (for example videos, pose estimation, electrophysiology, fiber photometry) and how
  they are organized;
- how the streams are synchronized, and which clock is the reference;
- the metadata: subject, devices, the task, and where each value comes from (a sheet, the paper, the lab's notes).

[Data organization](../src/olveczky_lab_to_nwb/klibaite_2025/docs/data_organization.md) is this list for the
Klibaite 2025 conversion.

## 2. Find NeuroConv interfaces for each stream

[NeuroConv](https://neuroconv.readthedocs.io/) reads many acquisition formats and writes them to NWB, among them
SpikeGLX and Open Ephys recordings, Neuropixels, fiber photometry, DeepLabCut, SLEAP and DANNCE. The
[conversion gallery](https://neuroconv.readthedocs.io/en/main/conversion_examples_gallery/index.html) shows a short
example for each format.

For data no interface reads, write a small interface that subclasses `BaseDataInterface` and implements
`add_to_nwbfile` (see `src/olveczky_lab_to_nwb/klibaite_2025/interfaces/`).

## 3. Combine them in a converter

An `NWBConverter` combines the interfaces of a session and aligns their times (see
`src/olveczky_lab_to_nwb/klibaite_2025/nwbconverter.py`). Write a function that converts one session, then one that
finds and converts all sessions (`convert_session.py` and `convert_all_sessions.py` here).

In this repository, a new conversion is a new folder next to `klibaite_2025/`, named `<first author>_<year>`.
Copying `klibaite_2025/` is a quick start: rename the converter class and the imports, keep the interface slots the
new dataset needs, and rewrite the session discovery, the metadata and the time alignment. For example, a dataset that
adds electrophysiology to the same behavioral setup keeps the `DANNCE` slot and adds a recording interface (such as
`SpikeGLXRecordingInterface`), aligned to the camera clock through the sync pulses both systems record.

## 4. Keep the metadata in YAML files

Put the metadata that does not come from the data files in a YAML file and merge it into the converter's metadata
(see [Metadata](../src/olveczky_lab_to_nwb/klibaite_2025/docs/metadata.md)).

## 5. Check and share

- Convert one session with `stub_test=True` and open it with PyNWB or [Neurosift](https://neurosift.app).
- Run [NWB Inspector](https://nwbinspector.readthedocs.io/) on the files and fix its critical messages.
- Write an example notebook that loads a file and shows each stream (see `notebooks/`).
- Upload to [DANDI](https://docs.dandiarchive.org/user-guide-sharing/uploading-data/), trying the sandbox first.

## Starting a new repository

[cookiecutter-my-lab-to-nwb-template](https://github.com/catalystneuro/cookiecutter-my-lab-to-nwb-template) creates a
conversion repository with the same layout as this one. The
[nwb-convert](https://github.com/catalystneuro/claude-skills/tree/main/nwb-convert) skill for Claude Code walks
through the steps above in a conversation: it inspects the data, asks for the metadata, and writes a conversion
repository on NeuroConv and PyNWB with an example notebook. For conversions without code,
[NWB GUIDE](https://nwb-guide.readthedocs.io/) is a desktop application that walks through the same steps for the
formats NeuroConv supports.
