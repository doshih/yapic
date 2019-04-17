from unittest import TestCase
from yapic_io.ilastik_connector import IlastikConnector
from yapic_io.dataset import Dataset
from yapic.session import Session
import os
import skimage
import numpy as np
import pytest
import shutil

base_path = os.path.dirname(__file__)


class TestSessionMethods(TestCase):

    def test_set_augmentation(self):

        img_path = os.path.join(
            base_path,
            '../test_data/shapes/pixels/*')
        label_path = os.path.join(
            base_path,
            '../test_data/shapes/labels.ilp')

        t = Session()
        t.load_training_data(img_path, label_path)
        t.make_model('unet_2d', (1, 572, 572))

        t.set_augmentation('flip+rotate')
        self.assertEqual(t.data.augmentation, {'rotate', 'flip'})
        t.set_augmentation('flip+rotate+shear')
        self.assertEqual(t.data.augmentation, {'rotate', 'flip', 'shear'})
        t.set_augmentation('flip')
        self.assertEqual(t.data.augmentation, {'flip'})

    def test_set_normalization(self):

        img_path = os.path.join(
            base_path,
            '../test_data/shapes/pixels/*')
        label_path = os.path.join(
            base_path,
            '../test_data/shapes/labels.ilp')

        t = Session()
        t.load_training_data(img_path, label_path)
        t.make_model('unet_2d', (1, 572, 572))

        t.set_normalization('local')
        assert t.data.normalize_mode == 'local'
        assert t.data.global_norm_minmax is None

        t.set_normalization('global_0+255')
        assert t.data.normalize_mode == 'global'
        assert t.data.global_norm_minmax == (0, 255)


class TestEnd2End(TestCase):

    def test_shape_data_fast(self):

        # train a classifier and predict training data
        os.environ['CUDA_VISIBLE_DEVICES'] = '2'

        img_path = os.path.join(
            base_path,
            '../test_data/shapes/pixels/*')
        label_path = os.path.join(
            base_path,
            '../test_data/shapes/labels.ilp')
        savepath = os.path.join(
            base_path,
            '../test_data/tmp')

        os.makedirs(savepath, exist_ok=True)

        t = Session()
        t.load_training_data(img_path, label_path)
        t.make_model('convnet_for_unittest', (1, 100, 100))

        t.train(max_epochs=5,
                steps_per_epoch=20,
                log_filename=os.path.join(savepath, 'log.csv'),
                model_filename=os.path.join(savepath, 'model.h5'))
        t.load_prediction_data(img_path, savepath)
        t.predict()

        artifacts = os.listdir(savepath)
        assert 'log.csv' in artifacts
        assert 'pixels_1_class_1.tif' in artifacts
        assert 'pixels_1_class_2.tif' in artifacts
        assert 'pixels_1_class_3.tif' in artifacts
        assert 'pixels_2_class_1.tif' in artifacts
        assert 'pixels_2_class_2.tif' in artifacts
        assert 'pixels_2_class_3.tif' in artifacts

        shutil.rmtree(savepath)

    @pytest.mark.slow
    def test_shape_data(self):

        # train a classifier and predict training data
        os.environ['CUDA_VISIBLE_DEVICES'] = '2'

        img_path = os.path.join(
            base_path,
            '../test_data/shapes/pixels/*')
        label_path = os.path.join(
            base_path,
            '../test_data/shapes/labels.ilp')
        savepath = os.path.join(
            base_path,
            '../test_data/tmp')

        os.makedirs(savepath, exist_ok=True)

        t = Session()
        t.load_training_data(img_path, label_path)
        t.make_model('unet_2d', (1, 572, 572))

        t.train(max_epochs=15,
                steps_per_epoch=6,
                log_filename=os.path.join(savepath, 'log.csv'),
                model_filename=os.path.join(savepath, 'model.h5'))
        t.load_prediction_data(img_path, savepath)
        t.predict()

        # read prediction images and compare with validation data
        def read_images(image_nr, class_nr):
            if class_nr == 1:
                shape = 'circles'
            if class_nr == 2:
                shape = 'triangles'

            filename = os.path.join(
                                savepath,
                                'pixels_{}_class_{}.tif'.format(image_nr,
                                                                class_nr))
            print(filename)
            prediction_img = np.squeeze(skimage.io.imread(filename))
            filename = os.path.join(
                                    savepath,
                                    '../shapes/val/{}_{}.tiff'.format(
                                        shape,
                                        image_nr))
            print(filename)
            val_img = np.squeeze(skimage.io.imread(filename))
            return prediction_img, val_img

        prediction_img, val_img = read_images(1, 1)
        accuracy = np.mean(prediction_img[val_img > 0][:])
        print(accuracy)
        self.assertTrue(accuracy > 0.6)

        prediction_img, val_img = read_images(1, 2)
        accuracy = np.mean(prediction_img[val_img > 0][:])
        print(accuracy)
        self.assertTrue(accuracy > 0.6)

        prediction_img, val_img = read_images(2, 1)
        accuracy = np.mean(prediction_img[val_img > 0][:])
        print(accuracy)
        self.assertTrue(accuracy > 0.6)

        prediction_img, val_img = read_images(2, 2)
        accuracy = np.mean(prediction_img[val_img > 0][:])
        print(accuracy)
        self.assertTrue(accuracy > 0.6)

        shutil.rmtree(savepath)
