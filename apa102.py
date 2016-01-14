import logging
import math
import numpy
import os
from colorsys import hsv_to_rgb
from spi_background import SpiMaster

# TODO DRY spi_background.py
try:
    import spidev
except ImportError:
    print 'spidev not found; using simulator'
    import spidev_sim as spidev

logger = logging.getLogger('apa102')
if 'apa102' in os.environ.get('DEBUG', '').split(','):
    logger.setLevel(logging.INFO)

GAMMA = 2.5
SPI_MAX_SPEED_HZ = 8000000


class APA102:
    def __init__(self, count, bus=0, device=1, multiprocessing=True):
        self.count = count
        self.spi = None
        if multiprocessing and not hasattr(spidev, 'SIMULATED'):
            self.spi = SpiMaster(bus=bus, device=device, max_speed_hz=SPI_MAX_SPEED_HZ)
        else:
            self.spi = spi = spidev.SpiDev()
            spi.open(bus, device)
            spi.max_speed_hz = SPI_MAX_SPEED_HZ
        self.leds = numpy.zeros((self.count, 4))
        self.clear()

    def clear(self):
        self.leds[:, :] = 0.0

    def set_rgb(self, x, r, g, b):
        if 0 <= x < self.count:
            # Slower alternatives:
            #   pixel = self.leds[x]; pixel[1] = g; etc. # somewhat slower
            #   self.leds[x,1:] = [g, b, r] # much slower
            leds = self.leds
            leds[x, 1] = g
            leds[x, 2] = b
            leds[x, 3] = r

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
            # The following is much faster than self.leds[x,1:] += [g, b, r]
            led = self.leds[x]
            led[1] += g
            led[2] += b
            led[3] += r

    def set_hsv(self, x, h, s, v):
        self.set_rgb(x, *hsv_to_rgb(h, s, v))

    def add_hsv(self, x, h, s, v):
        self.add_rgb(x, *hsv_to_rgb(h, s, v))

    def add_range_rgb(self, x0, x1, r, g, b):
        self.leds[x0:x1, 1:] += [g, b, r]

    def add_range_hsv(self, x0, x1, h, s, v):
        self.add_range_rgb(x0, x1, *hsv_to_rgb(h, s, v))

    """ This increments each of the pixels by the values in `rgbs`.

    Parameters
    ----------
    x0 : int
      Index of the first pixel.
    rgbs : numpy.ndarray([n, 3])
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
        leds[x0:x1, 1:] += numpy.fliplr(rgbs)

    def show(self):
        bytes = numpy.ravel(numpy.round(255 * numpy.clip(self.leds, 0.0, 1.0) ** GAMMA)).astype(int)
        bytes[::4] = 0xff
        self.spi.xfer2([0, 0, 0, 0])
        # the following alternative causes an intermittent stutter:
        # bytes = numpy.insert(bytes, 0, [0, 0, 0, 0])
        self.spi.xfer2(bytes.tolist())

    def close(self):
        self.spi.close()
