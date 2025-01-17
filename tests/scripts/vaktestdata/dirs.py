"""Helper functions for setting up directories."""
import logging

from . import constants


logger = logging.getLogger(__name__)


def make_subdirs_in_generated(config_paths):
    """make sub-directories inside ./tests/data_for_tests/generated

    do this after copying configs,
    before using those configs to generate results.
    We use configs to decide which dirs we need to make

    makes three directories in data_for_tests/generated:
    configs, prep, and results.
    prep has one sub-directory for every data "type".
    results does also, but in addition will have sub-directories
    within those for models.
    """
    logger.info(
        "Making sub-directories in ./tests/data_for_tests/generated/ where files generated by `vak` will go"
    )

    for top_level_dir in constants.TOP_LEVEL_DIRS:  # datasets / results
        subdir_to_make = (
                constants.GENERATED_TEST_DATA / top_level_dir
        )
        logger.info(
            f"Making sub-directory: {subdir_to_make}"
        )
        subdir_to_make.mkdir(parents=True)

    for config_metadata in constants.CONFIG_METADATA:
        config_type = config_metadata.config_type  # train, eval, predict, etc.
        if config_metadata.audio_format:
            data_dir = f"audio_{config_metadata.audio_format}_annot_{config_metadata.annot_format}"
        elif config_metadata.spect_format:
            data_dir = f"spect_{config_metadata.spect_format}_annot_{config_metadata.annot_format}"
        else:
            raise ValueError(
                f'could not determine data dir for config metadata:\n{config_metadata}'
            )
        model = config_metadata.model

        if config_metadata.use_dataset_from_config is None:  # we need to make dataset dir
            subdir_to_make = (
                    constants.GENERATED_TEST_DATA / 'prep' / config_type / data_dir / model
            )
            logger.info(
                f"Making sub-directory: {subdir_to_make}"
            )
            subdir_to_make.mkdir(parents=True)

        subdir_to_make = (
                constants.GENERATED_TEST_DATA / 'results' / config_type / data_dir / model
        )
        logger.info(
            f"Making sub-directory: {subdir_to_make}"
        )
        subdir_to_make.mkdir(parents=True)
