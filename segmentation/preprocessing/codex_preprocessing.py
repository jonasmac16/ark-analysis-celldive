import numpy as np
import skimage.io as io
import os
import pandas as pd

from segmentation.utils import data_utils
from skimage.transform import resize
import skimage
from skimage.measure import label

base_dir = "/Users/noahgreenwald/Documents/Grad_School/Lab/Segmentation_Project/data/20191121_Codex_Download/"

channels = pd.read_csv(base_dir + "/raw/channel_names.csv", header=None)


# load multichannel data, extract relevant channels, save as TIFs
multitiff = os.listdir(base_dir + "raw")
multitiff = [file for file in multitiff if "Fused.tif" in file]
multitiff.sort()

if not os.path.exists(base_dir + "/Points/"):
    os.makedirs(base_dir + "/Points/")

for i in range(len(multitiff)):
    direc_name = base_dir + "/Points/Point" + str(i + 1)

    if not os.path.exists(direc_name):
        os.makedirs(direc_name)

    codex_stack = io.imread(base_dir + "/raw/" + multitiff[i])
    codex_data = codex_stack.astype('int16')
    io.imsave(direc_name + "/CD45_cyc1.tiff", codex_stack[2, :, :, 0])
    io.imsave(direc_name + "/Nuc_cyc16.tiff", codex_stack[16, :, :, 2])

# load voronoi diagrams, process into segmentation masks, save as TIFs

masks = os.listdir(base_dir + "/raw")
masks = [file for file in masks if "Diagram" in file]
masks.sort()

for i in range(len(masks)):
    direc_name = base_dir + "/Points/Point" + str(i + 1)
    voronoi = io.imread(base_dir + "raw/" + masks[i])

    # convert to single channel
    voronoi = voronoi[:, :, 0]

    # change text from background label to arbitrary label
    voronoi[voronoi < 10] = 14

    # find border pixels, convert to background label
    voronoi[np.logical_and(voronoi > 180, voronoi < 209)] = 0

    # convert arbitrary cell labels to 1
    voronoi[voronoi > 1] = 255

    voronoi = skimage.morphology.erosion(voronoi, selem=skimage.morphology.square(3))

    voronoi = label(voronoi)
    voronoi = voronoi.astype('int32')

    io.imsave(direc_name + "/Segmentation_Mask.tiff", voronoi)


# upsample and crop data

codex_data = data_utils.load_tifs_from_points_dir(base_dir + "Points", tif_folder="",
                                                        tifs=["CD45_cyc1.tiff", "Nuc_cyc16.tiff"])

codex_data_resized = resize(codex_data,
                            [codex_data.shape[0], codex_data.shape[1] * 2, codex_data.shape[2] * 2, codex_data.shape[3]]
                            , order=3)

segmentation_masks = data_utils.load_tifs_from_points_dir(base_dir + "Points", tif_folder="",
                                                                tifs=["Segmentation_Mask.tiff"])

segmentation_masks_resized = resize(segmentation_masks[:, :, :, :],
                                    [segmentation_masks.shape[0], codex_data_resized.shape[1], codex_data_resized.shape[2],
                                     segmentation_masks.shape[3]], order=0, anti_aliasing=False)

training_data = np.zeros(codex_data_resized.shape[:-1] + (codex_data_resized.shape[-1] + 1, ), dtype="int32")
training_data[..., :-1] = codex_data_resized
training_data[..., -1:] = segmentation_masks_resized
training_data = training_data[:, :-2, :-144, :]

training_data_cropped = data_utils.crop_image_stack(training_data[:, :, :, :], 241, 1)
os.makedirs(base_dir + "Input_Data/Point123_Crop_Small")
for i in range(training_data_cropped.shape[0]):
    save_direc = base_dir + "/Input_Data/Point123_Crop_Small/Point" + str(i + 1)
    os.makedirs(save_direc)
    os.makedirs(save_direc + "/raw")
    os.makedirs(save_direc + "/annotated")

    io.imsave(save_direc + "/raw/CD45.tiff", training_data_cropped[i, :, :, 0])
    io.imsave(save_direc + "/raw/H3.tiff", training_data_cropped[i, :, :, 1])
    io.imsave(save_direc + "/annotated/segmentation_mask.tiff", training_data_cropped[i, :, :, 2])


# use training data generated by ilastik to train network

points = os.listdir(base_dir + "Input_Data/Point1_Ilastik_Training/Point1_Crop")
points = [point for point in points if "Point" in point]

for point in points:
    ilastik = io.imread(base_dir + "Input_Data/Point1_Ilastik_Training/Point1_Crop/" + point + "/raw/___Probabilities.tiff")
    interior = ilastik[:, :, 0]
    border = ilastik[:, :, 1]

    # subtract border from interior, then label each object
    objects = interior - border
    objects[objects < 0.2] = 0
    objects[objects > 0] = 1

    unique = skimage.measure.label(objects)

    io.imsave(base_dir + "Input_Data/Ilastik_Labels/" + point + "/annotated/segmentation_labels.tiff", unique.astype('int32'))




