# Copyright (c) 2019, NVIDIA CORPORATION. All rights reserved.
#
# This work is licensed under the Creative Commons Attribution-NonCommercial
# 4.0 International License. To view a copy of this license, visit
# http://creativecommons.org/licenses/by-nc/4.0/ or send a letter to
# Creative Commons, PO Box 1866, Mountain View, CA 94042, USA.

import os
import pickle
import numpy as np
import PIL.Image
import dnnlib
import dnnlib.tflib as tflib
import config

def main():
    tflib.init_tf()
    _G, _D, Gs = pickle.load(open("waifunet.pkl", "rb"))
    Gs.print_layers()

    for i in range(0, 12000):
        if not os.path.exists('./%s/finbot-waifu-%s.jpg' % (config.result_dir, i)):
            print("Image number:", i)
            rnd = np.random.RandomState(None)
            latents = rnd.randn(1, Gs.input_shape[1])
            fmt = dict(func=tflib.convert_images_to_uint8, nchw_to_nhwc=True)
            images = Gs.run(latents, None, truncation_psi=0.55, randomize_noise=True, output_transform=fmt)
            os.makedirs(config.result_dir, exist_ok=True)
            png_filename = os.path.join(config.result_dir, 'finbot-waifu-'+str(i)+'.png')
            PIL.Image.fromarray(images[0], 'RGB').save(png_filename)

if __name__ == "__main__":
    main()
