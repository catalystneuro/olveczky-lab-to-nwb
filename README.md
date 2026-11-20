# olveczky-lab-to-nwb

Conversion of the Olveczky Lab's behavior recordings to the
[Neurodata Without Borders](https://nwb-overview.readthedocs.io/) (NWB) format, built on
[NeuroConv](https://neuroconv.readthedocs.io/).

The `klibaite_2025` conversion covers the social behavior dataset of
[Klibaite et al. (2025), Cell](https://doi.org/10.1016/j.cell.2025.01.044): pairs of rats from autism model lines
(SCN2A, ARID1B, CHD8, GRIN2B, NRXN1, and Fmr1 for Fragile X) and Long-Evans rats behave freely together in an arena, recorded by 6 cameras,
with the 3D pose of each rat estimated by sDANNCE. Each rat of a session becomes one NWB file, holding its 3D pose,
the 6 camera videos (linked as external files) with the camera calibrations, the skin contacts between the two rats,
the session's task and epoch annotated with HED, and the subject metadata. FX and Long-Evans rats were also recorded
alone in the arena (lone sessions), which become one file each. The files are shared on the EMBER archive, in
[dandiset 000637](https://dandi.emberarchive.org/dandiset/000637).

## Installation

Install [git](https://github.com/git-guides/install-git) and [conda](https://docs.conda.io/en/latest/miniconda.html),
then, from a terminal:

```bash
git clone https://github.com/catalystneuro/olveczky-lab-to-nwb
cd olveczky-lab-to-nwb
conda env create --file make_env.yml
conda activate olveczky-lab-to-nwb-env
```

This creates a conda environment with the package installed in editable mode, so that changes to the code and
metadata files apply without installing again. Without conda, use Python 3.11 or 3.12 and run `pip install --editable .`
in the cloned folder.

NeuroConv is installed from its `main` branch, which holds the DANNCE and HERD features this conversion needs and
which are not released yet.

## Quick start

Set the data share and output folder paths in the `if __name__ == "__main__":` block of each script, then:

```bash
python src/olveczky_lab_to_nwb/klibaite_2025/convert_all_sessions.py
python src/olveczky_lab_to_nwb/klibaite_2025/inspection.py
```

The first writes two NWB files per session (one per rat) to the output folder; the second inspects them with NWB
Inspector and validates their HED annotations. See
[Converting sessions](src/olveczky_lab_to_nwb/klibaite_2025/docs/converting_sessions.md).

## Documentation

The conversion pipeline in general, in [docs/](docs/):

- [The conversion pipeline](docs/conversion_pipeline.md): NWB, NeuroConv, the parts of a conversion and the steps from
  recordings to a public archive.
- [Building a new conversion pipeline](docs/new_conversion_pipeline.md): converting another experiment to NWB.

The Klibaite 2025 conversion, in [klibaite_2025/docs/](src/olveczky_lab_to_nwb/klibaite_2025/docs/):

- [Data organization](src/olveczky_lab_to_nwb/klibaite_2025/docs/data_organization.md): the data share layout,
  cohorts, encounter rounds and lab files.
- [Converting sessions](src/olveczky_lab_to_nwb/klibaite_2025/docs/converting_sessions.md): converting sessions,
  inspecting and uploading the files, and the output files.
- [Data streams](src/olveczky_lab_to_nwb/klibaite_2025/docs/data_streams.md): pose, video, skin contacts, task and
  epoch, and how their times are aligned.
- [Metadata](src/olveczky_lab_to_nwb/klibaite_2025/docs/metadata.md): editing the metadata file, adding a cohort,
  HED tags and ontology terms.
- [Excluded sessions](src/olveczky_lab_to_nwb/klibaite_2025/docs/excluded_sessions.md): the sessions of the data share
  that are not converted, and why.

The notebooks in [notebooks/](notebooks/) stream the files from the EMBER archive or read them from disk:
[000637_demo.ipynb](notebooks/000637_demo.ipynb) shows each data stream of one rat, and
[000637_two_subject_demo.ipynb](notebooks/000637_two_subject_demo.ipynb) the two rats of a session together.

## Repository layout

```text
src/olveczky_lab_to_nwb/klibaite_2025/
├── convert_session.py        conversion of one rat of one session (social or lone)
├── convert_all_sessions.py   conversion of all sessions
├── nwbconverter.py           NWBConverter of the dataset and time alignment
├── interfaces/               data interfaces (skin contacts, task and epoch)
├── utils/                    session folders, cohorts and subject metadata from the rat log
├── inspection.py             NWB Inspector reports, HED validation and inspection summary
├── upload_to_EMBER.py        organizing and uploading to the EMBER archive
├── general_metadata.yaml     experiment, conditions (social, lone), skeleton, HED and ontology terms
└── docs/                     documentation of this conversion
docs/                         documentation of the conversion pipeline in general
notebooks/                    example notebooks
```

## Citation

If you use these files, please cite [Klibaite et al. (2025)](https://doi.org/10.1016/j.cell.2025.01.044), and
[NeuroConv](https://github.com/catalystneuro/neuroconv) and [NWB](https://www.nwb.org/) for the conversion.
