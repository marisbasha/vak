"""A dataclass that represents metadata
associated with a frame classification dataset,
as generated by
:func:`vak.core.prep.frame_classification.prep_frame_classification_dataset`"""
from __future__ import annotations

import json
import pathlib
from typing import ClassVar

import attr


def is_valid_dataset_csv_filename(instance, attribute, value):
    valid = "_prep_" in value and value.endswith(".csv")
    if not valid:
        raise ValueError(
            f"Invalid dataset csv filename: {value}."
            f'Filename should contain the string "_prep_" '
            f"and end with the extension .csv."
            f"Valid filenames are generated by "
            f"vak.core.prep.generate_dataset_csv_filename"
        )


def is_valid_audio_format(instance, attribute, value):
    import vak.common.constants

    if value not in vak.common.constants.VALID_AUDIO_FORMATS:
        raise ValueError(
            f"Not a valid audio format: {value}. Valid audio formats are: {vak.common.constants.VALID_AUDIO_FORMATS}"
        )


def is_valid_spect_format(instance, attribute, value):
    import vak.common.constants

    if value not in vak.common.constants.VALID_SPECT_FORMATS:
        raise ValueError(
            f"Not a valid spectrogram format: {value}. "
            f"Valid spectrogram formats are: {vak.common.constants.VALID_SPECT_FORMATS}"
        )


@attr.define
class Metadata:
    """A dataclass that represents metadata
    associated with a dataset that was
    generated by :func:`vak.core.prep.prep`.

    Attributes
    ----------
    dataset_csv_filename : str
        Name of csv file representing the source files in the dataset.
        Csv file will be located in root of directory representing dataset,
        so only the filename is given.
    frame_dur: float, optional
        Duration of a frame, i.e., a single sample in audio
        or a single timebin in a spectrogram.
    input_type : str
        The modality of the input data "frames", either audio signals
        or spectrograms. One of {'audio', 'spect'}.
    """

    # declare this as a constant to avoid
    # needing to remember this in multiple places, and to use in unit tests
    METADATA_JSON_FILENAME: ClassVar = "metadata.json"

    dataset_csv_filename: str = attr.field(
        converter=str, validator=is_valid_dataset_csv_filename
    )

    input_type: str = attr.field()

    @input_type.validator
    def is_valid_input_type(self, attribute, value):
        if not isinstance(value, str):
            raise TypeError(
                f"{attribute.name} value should be a string but was type {type(value)}"
            )
        from ...prep.constants import INPUT_TYPES

        if value not in INPUT_TYPES:
            raise ValueError(
                f"Value for {attribute.name} is not a valid input type: '{value}'\n"
                f"Valid input types are: {INPUT_TYPES}"
            )

    frame_dur: float = attr.field(converter=float)

    @frame_dur.validator
    def is_valid_frame_dur(self, attribute, value):
        if not isinstance(value, float):
            raise ValueError(f"{attribute.name} should be a float value.")
        if not value > 0.0:
            raise ValueError(f"{attribute.name} should be greater than zero.")

    audio_format: str = attr.field(
        converter=attr.converters.optional(str),
        validator=attr.validators.optional(is_valid_audio_format),
        default=None,
    )

    spect_format: str = attr.field(
        converter=attr.converters.optional(str),
        validator=attr.validators.optional(is_valid_spect_format),
        default=None,
    )

    @classmethod
    def from_path(cls, json_path: str | pathlib.Path):
        """Load dataset metadata from a json file.

        Class method that returns an instance of
        :class:`~vak.datasets.frame_classification.FrameClassificationDatatsetMetadata`.

        Parameters
        ----------
        json_path : string, pathlib.Path
            Path to a 'metadata.json' file created by
            :func:`vak.core.prep.prep` when generating
            a dataset.

        Returns
        -------
        metadata : vak.datasets.frame_classification.FrameClassificationDatatsetMetadata
            Instance of :class:`~vak.datasets.frame_classification.FrameClassificationDatatsetMetadata`
            with metadata loaded from json file.
        """
        json_path = pathlib.Path(json_path)
        with json_path.open("r") as fp:
            metadata_json = json.load(fp)
        return cls(**metadata_json)

    @classmethod
    def from_dataset_path(cls, dataset_path: str | pathlib.Path):
        dataset_path = pathlib.Path(dataset_path)
        if not dataset_path.exists() or not dataset_path.is_dir():
            raise NotADirectoryError(
                f"`dataset_path` not found or not recognized as a directory: {dataset_path}"
            )

        metadata_json_path = dataset_path / cls.METADATA_JSON_FILENAME
        if not metadata_json_path.exists():
            raise FileNotFoundError(
                f"Metadata file not found: {metadata_json_path}"
            )

        return cls.from_path(metadata_json_path)

    def to_json(self, dataset_path: str | pathlib.Path) -> None:
        """Dump dataset metadata to a json file.

        This method is called by :func:`vak.core.prep.prep`
        after it generates a dataset and then creates an
        instance of :class:`~vak.datasets.frame_classification.FrameClassificationDatatsetMetadata`
        with metadata about that dataset.

        Parameters
        ----------
        dataset_path : string, pathlib.Path
            Path to root of a directory representing a dataset
            generated by :func:`vak.core.prep.prep`.
            where 'metadata.json' file
            should be saved.
        """
        dataset_path = pathlib.Path(dataset_path)
        if not dataset_path.exists() or not dataset_path.is_dir():
            raise NotADirectoryError(
                f"dataset_path not recognized as a directory: {dataset_path}"
            )

        json_dict = attr.asdict(self)
        json_path = dataset_path / self.METADATA_JSON_FILENAME
        with json_path.open("w") as fp:
            json.dump(json_dict, fp, indent=4)
