import pytest

import vak
import vak.datasets.frame_classification


class TestWindowDataset:
    @pytest.mark.parametrize(
        'config_type, model_name, audio_format, spect_format, annot_format, split',
        [
            ('train', 'teenytweetynet', 'cbin', None, 'notmat', 'train'),
            ('train', 'teenytweetynet', None, 'mat', 'yarden', 'train'),
            ('learncurve', 'teenytweetynet', 'cbin', None, 'notmat', 'train'),
        ]
    )
    def test_from_dataset_path(self, config_type, model_name, audio_format, spect_format, annot_format, split,
                               specific_config):
        """Test we can get a WindowDataset instance from the classmethod ``from_csv``"""
        toml_path = specific_config(config_type,
                                    model_name,
                                    audio_format=audio_format,
                                    spect_format=spect_format,
                                    annot_format=annot_format)
        cfg = vak.config.parse.from_toml_path(toml_path)
        cfg_command = getattr(cfg, config_type)

        transform, target_transform = vak.transforms.defaults.get_default_transform(
            model_name, config_type
        )

        dataset = vak.datasets.frame_classification.WindowDataset.from_dataset_path(
            dataset_path=cfg_command.dataset_path,
            split=split,
            window_size=cfg_command.train_dataset_params['window_size'],
            transform=transform,
            target_transform=target_transform,
        )
        assert isinstance(dataset, vak.datasets.frame_classification.WindowDataset)
