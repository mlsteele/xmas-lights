import logging
import math
import os
from colorsys import hsv_to_rgb
import numpy as np
from spi_background import SpiMaster

# TODO DRY spi_background.py
try:
    import periphery as spi_driver
except ImportError:
    # print 'spi_driver not found; using simulator'
    import spidev_sim as spi_driver

logger = logging.getLogger('apa102')
if 'apa102' in os.environ.get('DEBUG', '').split(','):
    logger.setLevel(logging.INFO)

gamma = 2.5
spi_max_speed_hz = 8000000
pixel_global_brightness = False


class APA102(object):
    def __init__(self, count, bus=0, device=1, multiprocessing=None):
        if multiprocessing is None:
            multiprocessing = not hasattr(spi_driver, 'SIMULATED')
        self.count = count
        self.spi = None
        if multiprocessing:
            self.spi = SpiMaster(bus=bus, device=device, max_speed_hz=spi_max_speed_hz)
        else:
            self.spi = spi_driver.SPI('/dev/spidev%d.%d' % (bus, device), 0, spi_max_speed_hz)
            # self.spi = spi = spidev.SpiDev()
            # spi.open(bus, device)
            # spi.max_speed_hz = spi_max_speed_hz
        self.leds = np.zeros((self.count, 3))
        self.clear()

    def clear(self):
        self.leds[:, :] = 0.0

    def set_rgb(self, x, r, g, b):
        if 0 <= x < self.count:
            # Slower alternatives:
            #   pixel = self.leds[x]; pixel[1] = g; etc. # somewhat slower
            #   self.leds[x,1:] = [g, b, r] # much slower
            leds = self.leds
            leds[x, 0] = r
            leds[x, 1] = g
            leds[x, 2] = b

    def add_rgb(self, x, r, g, b):
        if isinstance(x, float):
            f, x = math.modf(x)
            x = int(x)
            f = 1.0 - f
            self.add_rgb(x, f * r, f * g, f * b)
            f = 1.0 - f
            self.add_rgb(x + 1, f * r, f * g, f * b)
            return
        if 0 <= x < self.count:
            # The following is much faster than self.leds[x] += [g, b, r]
            led = self.leds[x]
            led[0] += r
            led[1] += g
            led[2] += b

    def set_hsv(self, x, h, s, v):
        self.set_rgb(x, *hsv_to_rgb(h, s, v))

    def add_hsv(self, x, h, s, v):
        self.add_rgb(x, *hsv_to_rgb(h, s, v))

    def add_range_rgb(self, x0, x1, r, g, b):
        self.leds[x0:x1] += [r, g, b]

    def add_range_hsv(self, x0, x1, h, s, v):
        self.add_range_rgb(x0, x1, *hsv_to_rgb(h, s, v))

    """ This increments each of the pixels by the values in `rgbs`.

    Parameters
    ----------
    x0 : int
      Index of the first pixel.
    rgbs : np.ndarray([n, 3])
    """
    def add_rgb_array(self, x0, rgbs):
        leds = self.leds
        n = leds.shape[0]
        x1 = x0 + rgbs.shape[0]
        if x1 < 0 or n <= x0:
            return
        if x0 < 0:
            rgbs = rgbs[-x0:]
            x0 = 0
        if x1 > n:
            x1 = n
            rgbs = rgbs[:x1 - x0, :]
        leds[x0:x1] += rgbs

    def show(self):
        components = np.clip(self.leds, 0.0, 1.0) ** gamma
        if pixel_global_brightness:
            brightness = np.clip(np.ceil(np.amax(components, axis=1) * 31), 1, 31)
            bytes = np.floor(self.leds * (np.array(255. * 31) / brightness).reshape(-1, 1))
        else:
            bytes = np.round(255 * components)
            brightness = 0xff
        bytes = np.insert(np.fliplr(bytes), 0, brightness, 1)
        bytes = np.ravel(bytes).astype('uint8')

        header = np.array([0, 0, 0, 0], 'uint8')
        self.spi.transfer(header.tobytes())
        self.spi.transfer(bytes.tobytes())

    def close(self):
        logger.info('close')
        self.spi.close()
