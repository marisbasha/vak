"""Function that trains models in the Parametric UMAP family."""
from __future__ import annotations

import datetime
import logging
import pathlib

import pandas as pd
import pytorch_lightning as lightning
import torch.utils.data

from .. import datasets, models, transforms
from ..common import validators
from ..common.device import get_default as get_default_device
from ..common.paths import generate_results_dir_name_as_path
from ..datasets.parametric_umap import ParametricUMAPDataset

logger = logging.getLogger(__name__)


def get_split_dur(df: pd.DataFrame, split: str) -> float:
    """Get duration of a split in a dataset from a pandas DataFrame representing the dataset."""
    return df[df["split"] == split]["duration"].sum()


def get_trainer(
    max_epochs: int,
    ckpt_root: str | pathlib.Path,
    ckpt_step: int,
    log_save_dir: str | pathlib.Path,
    device: str = "cuda",
) -> lightning.Trainer:
    """Returns an instance of ``lightning.Trainer``
    with a default set of callbacks.
    Used by ``vak.core`` functions."""
    if device == "cuda":
        accelerator = "gpu"
    else:
        accelerator = None

    ckpt_callback = lightning.callbacks.ModelCheckpoint(
        dirpath=ckpt_root,
        filename="checkpoint",
        every_n_train_steps=ckpt_step,
        save_last=True,
        verbose=True,
    )
    ckpt_callback.CHECKPOINT_NAME_LAST = "checkpoint"
    ckpt_callback.FILE_EXTENSION = ".pt"

    val_ckpt_callback = lightning.callbacks.ModelCheckpoint(
        monitor="val_loss",
        dirpath=ckpt_root,
        save_top_k=1,
        mode="min",
        filename="min-val-loss-checkpoint",
        auto_insert_metric_name=False,
        verbose=True,
    )
    val_ckpt_callback.FILE_EXTENSION = ".pt"

    callbacks = [
        ckpt_callback,
        val_ckpt_callback,
    ]

    logger = lightning.loggers.TensorBoardLogger(save_dir=log_save_dir)

    trainer = lightning.Trainer(
        max_epochs=max_epochs,
        accelerator=accelerator,
        logger=logger,
        callbacks=callbacks,
    )
    return trainer


def train_parametric_umap_model(
    model_name: str,
    model_config: dict,
    dataset_path: str | pathlib.Path,
    batch_size: int,
    num_epochs: int,
    num_workers: int,
    train_transform_params: dict | None = None,
    train_dataset_params: dict | None = None,
    val_transform_params: dict | None = None,
    val_dataset_params: dict | None = None,
    checkpoint_path: str | pathlib.Path | None = None,
    root_results_dir: str | pathlib.Path | None = None,
    results_path: str | pathlib.Path | None = None,
    shuffle: bool = True,
    val_step: int | None = None,
    ckpt_step: int | None = None,
    device: str | None = None,
    split: str = "train",
) -> None:
    """Train a model from the parametric UMAP family
    and save results.

    Saves checkpoint files for model,
    label map, and spectrogram scaler.
    These are saved either in ``results_path``
    if specified, or a new directory
    made inside ``root_results_dir``.

    Parameters
    ----------
    model_name : str
        Model name, must be one of vak.models.registry.MODEL_NAMES.
    model_config : dict
        Model configuration in a ``dict``,
        as loaded from a .toml file,
        and used by the model method ``from_config``.
    dataset_path : str
        Path to dataset, a directory generated by running ``vak prep``.
    batch_size : int
        number of samples per batch presented to models during training.
    num_epochs : int
        number of training epochs. One epoch = one iteration through the entire
        training set.
    num_workers : int
        Number of processes to use for parallel loading of data.
        Argument to torch.DataLoader.
    train_dataset_params: dict, optional
        Parameters for training dataset.
        Passed as keyword arguments to
        :class:`vak.datasets.parametric_umap.ParametricUMAP`.
        Optional, default is None.
    val_dataset_params: dict, optional
        Parameters for validation dataset.
        Passed as keyword arguments to
        :class:`vak.datasets.parametric_umap.ParametricUMAP`.
        Optional, default is None.
    checkpoint_path : str, pathlib.Path, optional
        path to a checkpoint file,
        e.g., one generated by a previous run of ``vak.core.train``.
        If specified, this checkpoint will be loaded into model.
        Used when continuing training.
        Default is None, in which case a new model is initialized.
    root_results_dir : str, pathlib.Path, optional
        Root directory in which a new directory will be created
        where results will be saved.
    results_path : str, pathlib.Path, optional
        Directory where results will be saved.
        If specified, this parameter overrides ``root_results_dir``.
    val_step : int
        Computes the loss using validation set every ``val_step`` epochs.
        Default is None, in which case no validation is done.
    ckpt_step : int
        Step on which to save to checkpoint file.
        If ckpt_step is n, then a checkpoint is saved every time
        the global step / n is a whole number, i.e., when ckpt_step modulo the global step is 0.
        Default is None, in which case checkpoint is only saved at the last epoch.
    device : str
        Device on which to work with model + data.
        Default is None. If None, then a device will be selected with vak.split.get_default.
        That function defaults to 'cuda' if torch.cuda.is_available is True.
    shuffle: bool
        if True, shuffle training data before each epoch. Default is True.
    split : str
        Name of split from dataset found at ``dataset_path`` to use
        when training model. Default is 'train'. This parameter is used by
        `vak.learncurve.learncurve` to specify specific subsets of the
        training set to use when training models for a learning curve.
    """
    for path, path_name in zip(
        (checkpoint_path,),
        ("checkpoint_path",),
    ):
        if path is not None:
            if not validators.is_a_file(path):
                raise FileNotFoundError(
                    f"value for ``{path_name}`` not recognized as a file: {path}"
                )

    dataset_path = pathlib.Path(dataset_path)
    if not dataset_path.exists() or not dataset_path.is_dir():
        raise NotADirectoryError(
            f"`dataset_path` not found or not recognized as a directory: {dataset_path}"
        )

    logger.info(
        f"Loading dataset from path: {dataset_path}",
    )
    metadata = datasets.parametric_umap.Metadata.from_dataset_path(
        dataset_path
    )
    dataset_csv_path = dataset_path / metadata.dataset_csv_filename
    dataset_df = pd.read_csv(dataset_csv_path)
    # ---------------- pre-conditions ----------------------------------------------------------------------------------
    if val_step and not dataset_df["split"].str.contains("val").any():
        raise ValueError(
            f"val_step set to {val_step} but dataset does not contain a validation set; "
            f"please run `vak prep` with a config.toml file that specifies a duration for the validation set."
        )

    # ---- set up directory to save output -----------------------------------------------------------------------------
    if results_path:
        results_path = pathlib.Path(results_path).expanduser().resolve()
        if not results_path.is_dir():
            raise NotADirectoryError(
                f"results_path not recognized as a directory: {results_path}"
            )
    else:
        results_path = generate_results_dir_name_as_path(root_results_dir)
        results_path.mkdir()

    # ---------------- load training data  -----------------------------------------------------------------------------
    logger.info(f"using training dataset from {dataset_path}")
    # below, if we're going to train network to predict unlabeled segments, then
    # we need to include a class for those unlabeled segments in labelmap,
    # the mapping from labelset provided by user to a set of consecutive
    # integers that the network learns to predict
    train_dur = get_split_dur(dataset_df, "train")
    logger.info(
        f"Total duration of training split from dataset (in s): {train_dur}",
    )

    if train_transform_params is None:
        train_transform_params = {}
    if (
        "padding" not in train_transform_params
        and model_name == "ConvEncoderUMAP"
    ):
        padding = models.convencoder_umap.get_default_padding(metadata.shape)
        train_transform_params["padding"] = padding
    transform = transforms.defaults.get_default_transform(
        model_name, "train", train_transform_params
    )

    if train_dataset_params is None:
        train_dataset_params = {}
    train_dataset = ParametricUMAPDataset.from_dataset_path(
        dataset_path=dataset_path,
        split=split,
        transform=transform,
        **train_dataset_params,
    )
    logger.info(
        f"Duration of ParametricUMAPDataset used for training, in seconds: {train_dataset.duration}",
    )
    train_loader = torch.utils.data.DataLoader(
        dataset=train_dataset,
        shuffle=shuffle,
        batch_size=batch_size,
        num_workers=num_workers,
    )

    # ---------------- load validation set (if there is one) -----------------------------------------------------------
    if val_step:
        if val_transform_params is None:
            val_transform_params = {}
        if (
            "padding" not in val_transform_params
            and model_name == "ConvEncoderUMAP"
        ):
            padding = models.convencoder_umap.get_default_padding(
                metadata.shape
            )
            val_transform_params["padding"] = padding
        transform = transforms.defaults.get_default_transform(
            model_name, "eval", val_transform_params
        )
        if val_dataset_params is None:
            val_dataset_params = {}
        val_dataset = ParametricUMAPDataset.from_dataset_path(
            dataset_path=dataset_path,
            split="val",
            transform=transform,
            **val_dataset_params,
        )
        logger.info(
            f"Duration of ParametricUMAPDataset used for validation, in seconds: {val_dataset.duration}",
        )
        val_loader = torch.utils.data.DataLoader(
            dataset=val_dataset,
            shuffle=False,
            batch_size=batch_size,
            num_workers=num_workers,
        )
    else:
        val_loader = None

    if device is None:
        device = get_default_device()

    model = models.get(
        model_name,
        model_config,
        input_shape=train_dataset.shape,
    )

    if checkpoint_path is not None:
        logger.info(
            f"loading checkpoint for {model_name} from path: {checkpoint_path}",
        )
        model.load_state_dict_from_path(checkpoint_path)

    results_model_root = results_path.joinpath(model_name)
    results_model_root.mkdir()
    ckpt_root = results_model_root.joinpath("checkpoints")
    ckpt_root.mkdir()
    logger.info(f"training {model_name}")
    trainer = get_trainer(
        max_epochs=num_epochs,
        log_save_dir=results_model_root,
        device=device,
        ckpt_root=ckpt_root,
        ckpt_step=ckpt_step,
    )
    train_time_start = datetime.datetime.now()
    logger.info(f"Training start time: {train_time_start.isoformat()}")
    trainer.fit(
        model=model,
        train_dataloaders=train_loader,
        val_dataloaders=val_loader,
    )
    train_time_stop = datetime.datetime.now()
    logger.info(f"Training stop time: {train_time_stop.isoformat()}")
    elapsed = train_time_stop - train_time_start
    logger.info(f"Elapsed training time: {elapsed}")