import logging, math, numpy
from colorsys import hsv_to_rgb
from spi_background import SpiMaster

# TODO DRY spi_background.py
try:
    import spidev
except ImportError:
    print "spidev not found; using simulator"
    import spidev_sim as spidev

logger = logging.getLogger("apa102")
# logger.setLevel(logging.INFO)

SPI_MAX_SPEED_HZ = 8000000

class APA102:
    def __init__(self, count, bus=0, device=1, master=True):
        self.count = count
        self.spi = None
        if master:
            self.spi = SpiMaster(bus=bus, device=device, max_speed_hz=SPI_MAX_SPEED_HZ)
        else:
            self.spi = spi = spidev.SpiDev()
            spi.open(bus, device)
            spi.max_speed_hz = SPI_MAX_SPEED_HZ
        self.leds = numpy.zeros((self.count, 4))
        self.clear()

    def clear(self):
        self.leds[:,:] = 0.0

    def setPixelRGB(self, x, r, g, b):
        if 0 <= x < self.count:
            # Slower alternatives:
            #   pixel = self.leds[x]; pixel[1] = g; etc. # somewhat slower
            #   self.leds[x,1:] = [g, b, r] # much slower
            leds = self.leds
            leds[x,1] = g
            leds[x,2] = b
            leds[x,3] = r

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
            # The following is much faster than self.leds[x,1:] += [g, b, r]
            led = self.leds[x]
            led[1] += g
            led[2] += b
            led[3] += r

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
