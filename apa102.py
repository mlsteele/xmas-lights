import math, numpy
from colorsys import hsv_to_rgb

try:
    import spidev
except ImportError:
    print "spidev not found; using simulator"
    import spidev_sim as spidev

class APA102:
    def __init__(self, count):
        self.count = count
        self.spi = spi = spidev.SpiDev()
        spi.open(0, 1)
        spi.max_speed_hz = 8000000
        self.leds = numpy.zeros((self.count, 4))
        self.clear()

    def clear(self):
        self.leds[:,:] = 0.0

    def setPixelRGB(self, x, r, g, b):
        if 0 <= x < self.count:
            self.leds[x,1:] = [g, b, r]

    def addPixelRGB(self, x, r, g, b):
        if isinstance(x, float):
            f, x = math.modf(x)
            x = int(x)
            f = 1.0 - f
            self.addPixelRGB(x, f * r, f * g, f * b)
            f = 1.0 - f
            self.addPixelRGB(x + 1, f * r, f * g, f * b)
            return
        if 0 <= x < self.count:
            self.leds[x,1:] += [g, b, r]

    def setPixelHSV(self, x, h, s, v):
        self.setPixelRGB(x, *hsv_to_rgb(h, s, v))

    def addPixelHSV(self, x, h, s, v):
        self.addPixelRGB(x, *hsv_to_rgb(h, s, v))

    def show(self):
        bytes = numpy.ravel(255 * numpy.clip(self.leds, 0.0, 1.0)).astype(int)
        bytes[::4] = 0xff
        self.spi.xfer2([0, 0, 0, 0])
        self.spi.xfer2(bytes.tolist())

    def close(self):
        self.spi.close()
