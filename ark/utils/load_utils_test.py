import numpy as np
import pytest
import tempfile

from ark.utils import load_utils, test_utils


def test_load_imgs_from_mibitiff():

    with tempfile.TemporaryDirectory() as temp_dir:

        # config test environment
        fovs, channels = test_utils.gen_fov_chan_names(num_fovs=2, num_chans=3, use_delimiter=True)

        filelocs, data_xr = test_utils.create_paired_xarray_fovs(
            temp_dir, fovs, channels, img_shape=(10, 10), mode='mibitiff', delimiter='_',
            fills=True, dtype=np.float32
        )

        # check unspecified fov loading
        loaded_xr = load_utils.load_imgs_from_mibitiff(temp_dir,
                                                       channels=channels,
                                                       delimiter='_')

        assert loaded_xr.equals(data_xr)

        fovnames = [f'{fov}.tiff' for fov in fovs]

        # check specified fov loading
        loaded_xr = load_utils.load_imgs_from_mibitiff(temp_dir,
                                                       mibitiff_files=[fovnames[-1]],
                                                       channels=channels,
                                                       delimiter='_')

        assert loaded_xr.equals(data_xr.loc[[fovs[-1]], :, :, :])

        # test automatic all channels loading
        loaded_xr = load_utils.load_imgs_from_mibitiff(temp_dir,
                                                       delimiter='_',
                                                       dtype=np.float32)

        assert loaded_xr.equals(data_xr)

        # test delimiter agnosticism
        loaded_xr = load_utils.load_imgs_from_mibitiff(temp_dir,
                                                       mibitiff_files=fovnames,
                                                       channels=channels,
                                                       delimiter='_',
                                                       dtype=np.float32)

        assert loaded_xr.equals(data_xr)
        assert np.issubdtype(loaded_xr.dtype, np.floating)

        # test float overwrite
        with pytest.warns(UserWarning):
            loaded_xr = load_utils.load_imgs_from_mibitiff(temp_dir,
                                                           mibitiff_files=[fovnames[-1]],
                                                           channels=channels,
                                                           delimiter='_',
                                                           dtype='int16')

            assert loaded_xr.equals(data_xr.loc[[fovs[-1]], :, :, :])
            assert np.issubdtype(loaded_xr.dtype, np.floating)


def test_load_imgs_from_tree():
    # test loading from within fov directories
    with tempfile.TemporaryDirectory() as temp_dir:
        fovs, chans, imgs = test_utils.gen_fov_chan_names(num_fovs=3, num_chans=3,
                                                          return_imgs=True)

        filelocs, data_xr = test_utils.create_paired_xarray_fovs(
            temp_dir, fovs, chans, img_shape=(10, 10), delimiter='_', fills=True, sub_dir="TIFs",
            dtype="int16"
        )

        # check default loading of all files
        loaded_xr = \
            load_utils.load_imgs_from_tree(temp_dir, img_sub_folder="TIFs", dtype="int16")

        assert loaded_xr.equals(data_xr)

        # check loading of specific files
        some_fovs = fovs[:2]
        some_imgs = imgs[:2]
        some_chans = chans[:2]

        loaded_xr = \
            load_utils.load_imgs_from_tree(temp_dir, img_sub_folder="TIFs", dtype="int16",
                                           fovs=some_fovs, channels=some_imgs)

        assert loaded_xr.equals(data_xr[:2, :, :, :2])

        # check loading w/o file extension
        loaded_xr = \
            load_utils.load_imgs_from_tree(temp_dir, img_sub_folder="TIFs", dtype="int16",
                                           channels=some_chans)

        assert loaded_xr.equals(data_xr[:, :, :, :2], )

        # check mixed extension presence
        loaded_xr = \
            load_utils.load_imgs_from_tree(temp_dir, img_sub_folder="TIFs", dtype="int16",
                                           channels=[chans[i] if i % 2 else imgs[i]
                                                     for i in range(3)])

        assert loaded_xr.equals(data_xr)

    with tempfile.TemporaryDirectory() as temp_dir:
        fovs, chans, imgs = test_utils.gen_fov_chan_names(num_fovs=1, num_chans=2,
                                                          return_imgs=True)

        filelocs, data_xr = test_utils.create_paired_xarray_fovs(
            temp_dir, fovs, chans, img_shape=(10, 10), delimiter='_', fills=True, sub_dir="TIFs",
            dtype=np.float32
        )

        with pytest.warns(UserWarning):
            loaded_xr = \
                load_utils.load_imgs_from_tree(temp_dir, img_sub_folder="TIFs", dtype="int16")

            assert loaded_xr.equals(data_xr)

            # test swap int16 -> float
            assert np.issubdtype(loaded_xr.dtype, np.floating)


def test_load_imgs_from_dir():
    # invalid directory is provided
    with pytest.raises(ValueError):
        loaded_xr = \
            load_utils.load_imgs_from_dir('not_a_dir', delimiter='_', dtype=np.float32)

    # test loading from 'free' directory
    with tempfile.TemporaryDirectory() as temp_dir:
        # input directory contains no images
        with pytest.raises(ValueError):
            load_utils.load_imgs_from_dir(temp_dir, delimiter='_', dtype=np.float32)

        fovs, _ = test_utils.gen_fov_chan_names(num_fovs=3, num_chans=0, use_delimiter=True)
        filelocs, data_xr = test_utils.create_paired_xarray_fovs(temp_dir, fovs, [0],
                                                                 img_shape=(10, 10), mode='labels',
                                                                 delimiter='_', dtype=np.float32)

        # invalid list of files is provided
        with pytest.raises(ValueError):
            load_utils.load_imgs_from_dir(temp_dir, files=fovs + ['not_an_image'],
                                          delimiter='_', dtype=np.float32)
        with pytest.raises(ValueError):
            load_utils.load_imgs_from_dir(temp_dir, files=['not_an_image'],
                                          delimiter='_', dtype=np.float32)

        # check default loading
        loaded_xr = load_utils.load_imgs_from_dir(temp_dir, delimiter='_',
                                                  xr_dim_name='compartments', dtype=np.float32)

        assert loaded_xr.equals(data_xr)

        # test swap float -> int16
        with pytest.warns(UserWarning):
            loaded_xr = load_utils.load_imgs_from_dir(temp_dir, delimiter='_', force_ints=True,
                                                      xr_dim_name='compartments', dtype="int16")

            assert loaded_xr.equals(data_xr)
            assert loaded_xr.dtype == 'int16'

        # test swap int16 -> float
        with pytest.warns(UserWarning):
            loaded_xr = load_utils.load_imgs_from_dir(temp_dir, delimiter='_',
                                                      xr_dim_name='compartments', dtype="int16")

            assert loaded_xr.equals(data_xr)
            assert np.issubdtype(loaded_xr.dtype, np.floating)

    # test multitiff input
    with tempfile.TemporaryDirectory() as temp_dir:
        fovs, channels = test_utils.gen_fov_chan_names(num_fovs=2, num_chans=3, use_delimiter=True)

        filelocs, data_xr = test_utils.create_paired_xarray_fovs(
            temp_dir, fovs, channels, img_shape=(10, 10), mode='reverse_multitiff', delimiter='_',
            fills=True, dtype=np.float32
        )

        fovnames = [f'{fov}.tiff' for fov in fovs]

        # test all channels loading w/ specified file
        loaded_xr = load_utils.load_imgs_from_dir(temp_dir, files=[fovnames[-1]],
                                                  xr_dim_name='channels', delimiter='_',
                                                  dtype=np.float32)

        assert loaded_xr.equals(data_xr.loc[[fovs[-1]], :, :, :])

        # indices should be between 0-2
        with pytest.raises(ValueError):
            load_utils.load_imgs_from_dir(temp_dir, files=[fovnames[-1]], xr_dim_name='channels',
                                          delimiter='_', dtype=np.float32,
                                          channel_indices=[0, 1, 4])

        # xr_channel_names should contain 3 names (as there are 3 channels)
        with pytest.raises(ValueError):
            load_utils.load_imgs_from_dir(temp_dir, files=[fovnames[-1]], xr_dim_name='channels',
                                          delimiter='_', dtype=np.float32,
                                          xr_channel_names=['A', 'B'])

        # test all channels w/ unspecified files + delimiter agnosticism
        loaded_xr = load_utils.load_imgs_from_dir(temp_dir,
                                                  files=None,
                                                  channel_indices=None,
                                                  xr_dim_name='channels',
                                                  delimiter='_')

        assert loaded_xr.equals(data_xr)

        # test channels_first input
        fovs, channels = test_utils.gen_fov_chan_names(num_fovs=2, num_chans=5, use_delimiter=True)

        _, data_xr = test_utils.create_paired_xarray_fovs(
            temp_dir, fovs, channels, img_shape=(10, 10), mode='multitiff', delimiter='_',
            fills=True, dtype=np.float32, channels_first=True
        )

        fovnames = [f'{fov}.tiff' for fov in fovs]

        # test all channels loading w/ specified file
        loaded_xr = load_utils.load_imgs_from_dir(temp_dir, files=[fovnames[-1]],
                                                  xr_dim_name='channels', delimiter='_',
                                                  dtype=np.float32)

        assert loaded_xr.equals(data_xr.loc[[fovs[-1]], :, :, :])

        # test all channels w/ unspecified files + delimiter agnosticism
        loaded_xr = load_utils.load_imgs_from_dir(temp_dir,
                                                  files=None,
                                                  channel_indices=None,
                                                  xr_dim_name='channels',
                                                  delimiter='_')

        assert loaded_xr.equals(data_xr)