"""
=====================
Image Deconvolution
=====================
In this example, we deconvolve an image using the
Richardson–Lucy algorithm ([1]_, [2]_).

The algorithm is based on a point spread function (PSF),
described as the impulse response of the
optical system. The blurred image is sharpened through a number of
iterations, which needs to be hand-tuned.

.. [1] William Hadley Richardson, "Bayesian-Based Iterative
       Method of Image Restoration",
       J. Opt. Soc. Am. A 27, 1593-1607 (1972), :DOI:`10.1364/JOSA.62.000055`

.. [2] https://en.wikipedia.org/wiki/Richardson%E2%80%93Lucy_deconvolution
"""

import numpy as np
import matplotlib.pyplot as plt
import skimage as ski

from scipy.signal import convolve2d as conv2


rng = np.random.default_rng()

# Convert astronaut image to grayscale
astro = ski.color.rgb2gray(ski.data.astronaut())

# Define PSF
psf = np.ones((5, 5)) / 25

# Convolve image with the PSF to simulate a blurred image
astro_blurred = conv2(astro, psf, 'same')

# Introduce poisson noise to the blurred image (https://en.wikipedia.org/wiki/Image_noise)
max_photon_count = 100
astro_noisy = rng.poisson(astro_blurred * max_photon_count) / max_photon_count

# Normalize noisy image
# (for images of float dtype, skimage assumes their values range from -1 to 1 or 0 to 1)
astro_noisy /= np.max(astro_noisy)

# Restore image by means of deconvolution
deconvolved_RL = ski.restoration.richardson_lucy(astro_noisy, psf, num_iter=30)

fig, ax = plt.subplots(nrows=1, ncols=3, figsize=(8, 5))
plt.gray()

for a in (ax[0], ax[1], ax[2]):
    a.axis('off')

ax[0].imshow(astro)
ax[0].set_title('Original Data')

ax[1].imshow(astro_noisy)
ax[1].set_title('Noisy data')

ax[2].imshow(deconvolved_RL, vmin=astro_noisy.min(), vmax=astro_noisy.max())
ax[2].set_title('Restoration using\nRichardson-Lucy')


fig.subplots_adjust(wspace=0.02, hspace=0.2, top=0.9, bottom=0.05, left=0, right=1)
plt.show()
