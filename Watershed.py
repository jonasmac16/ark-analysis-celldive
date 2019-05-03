# generates a watershed transform of probability masks

import numpy as np
import skimage.measure
import matplotlib.pyplot as plt
from scipy import ndimage as ndi

from skimage.morphology import watershed
from skimage.feature import peak_local_max
import skimage.io as io
import copy

# read in relavant files
image_dir = '/Users/noahgreenwald/Documents/Grad_School/Lab/Segmentation_Project/Contours/First_Run/cnn_data/Deepcell_docker/output/190430_watershed_test/'
mask_nuc = io.imread(image_dir + 'interior_border_30_nucleus.tiff')
mask_border = io.imread(image_dir + 'interior_border_30_border.tiff')
mask_truth = io.imread('/Users/noahgreenwald/Documents/Grad_School/Lab/Segmentation_Project/Contours/First_Run/Point23/Nuclear_Interior_Mask_Label.tif')

# create array to hold thresholded probabilities at different values to determine optimal cutoff
mask = np.zeros((1024,1024,5))
temp_mask = np.zeros((1024,1024,1))
temp_mask[:, :, 0] = mask_nuc
mask[:, :, :] = copy.copy(temp_mask)

io.imshow(mask[:, :, 0])
mask[mask[:, :, 0] < 0.8, 1] = 0
mask[np.logical_or(mask[:, :, 0] < 0.7, mask[:, :, 0] > 0.8), 2] = 0
mask[np.logical_or(mask[:, :, 0] < 0.6, mask[:, :, 0] > 0.7), 3] = 0
mask[mask[:, :, 0] < 0.7, 4] = 0

# plot thresholded probabilities
fig, ax = plt.subplots(ncols=2)
ax[0].imshow(mask[:, :, 4])
ax[1].imshow(mask_truth)
fig.tight_layout()

# identify maxs for watershed
maxs = peak_local_max(mask[:, :, 4], indices=False, min_distance=3)
markers = skimage.measure.label(mask[:, :, 4] > 0, connectivity=1)
labels = watershed(-mask_nuc, markers, mask=mask_nuc > 0.15, watershed_line=1)
io.imsave(image_dir + 'mask_python_watershed_15.tiff', labels)

fig, axes = plt.subplots(ncols=3, figsize=(9, 3), sharex=True, sharey=True)
ax = axes.ravel()

ax[0].imshow(mask_nuc, cmap=plt.cm.gray, interpolation='nearest')
ax[0].set_title('Nuclear Probs')
ax[1].imshow(mask_nuc_thresh, cmap=plt.cm.gray, interpolation='nearest')
ax[1].set_title('Distances')
ax[2].imshow(maxs, cmap=plt.cm.nipy_spectral, interpolation='nearest')
ax[2].set_title('Separated objects')




# Generate an initial image with two overlapping circles
x, y = np.indices((80, 80))
x1, y1, x2, y2 = 28, 28, 44, 52
r1, r2 = 16, 20
mask_circle1 = (x - x1)**2 + (y - y1)**2 < r1**2
mask_circle2 = (x - x2)**2 + (y - y2)**2 < r2**2
image = np.logical_or(mask_circle1, mask_circle2)

# Now we want to separate the two objects in image
# Generate the markers as local maxima of the distance to the background
distance = ndi.distance_transform_edt(image)
local_maxi = peak_local_max(distance, indices=False, footprint=np.ones((3, 3)),
                            labels=image)

markers = ndi.label(local_maxi)[0]
labels = watershed(-distance, markers, mask=image)

fig, axes = plt.subplots(ncols=3, figsize=(9, 3), sharex=True, sharey=True)
ax = axes.ravel()

ax[0].imshow(image, cmap=plt.cm.gray, interpolation='nearest')
ax[0].set_title('Overlapping objects')
ax[1].imshow(-distance, cmap=plt.cm.gray, interpolation='nearest')
ax[1].set_title('Distances')
ax[2].imshow(labels, cmap=plt.cm.nipy_spectral, interpolation='nearest')
ax[2].set_title('Separated objects')

for a in ax:
    a.set_axis_off()

fig.tight_layout()
plt.show()

# blurring prior to watershed: only works on integer arrays, will transform from decimal
import skimage.filters.rank as rank
fig, ax = plt.subplots(nrows=1, ncols=2)
temp = rank.mean(mask_nuc, np.ones((5, 5)))
ax[0].imshow(mask_nuc)
ax[1].imshow(temp)
fig.tight_layout()