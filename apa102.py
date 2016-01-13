import logging, math, numpy
from colorsys import hsv_to_rgb
import cPickle as pickle

try:
    import spidev
except ImportError:
    print "spidev not found; using simulator"
    import spidev_sim as spidev

logger = logging.getLogger('apa102')
# logger.setLevel(logging.INFO)

def createSpiSlave(count, q):
    logger.info('creating background %d', count)
    strip = APA102(count, queue=q, master=False)
    while True:
        item = q.get()
        if isinstance(item, str) and item == "close":
            strip.close()
            return
        bytes = pickle.loads(item)
        strip.show(bytes)

class APA102:
    def __init__(self, count, master=False, queue=None):
        self.count = count
        self.spi = None
        self.is_master = master
        self.frame_no = 0
        if master:
            from multiprocessing import Process, Queue
            queue = queue or Queue(1)
            p = Process(target=createSpiSlave, args=(count,queue))
            p.start()
        else:
            self.spi = spi = spidev.SpiDev()
            spi.open(0, 1)
            spi.max_speed_hz = 8000000
        self.queue = queue
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

    def show(self, bytes=None):
        self.frame_no += 1
        if bytes is None:
            bytes = numpy.ravel(255 * numpy.clip(self.leds, 0.0, 1.0)).astype(int)
            bytes[::4] = 0xff
        if self.is_master and self.queue:
            logger.info('enqueue frame #%d', self.frame_no)
            self.queue.put(pickle.dumps(bytes, protocol=-1))
        if self.spi:
            logger.info('send frame #%d', self.frame_no)
            self.spi.xfer2([0, 0, 0, 0])
            self.spi.xfer2(bytes.tolist())

    def close(self):
        if self.is_master and self.queue:
            self.queue.put("close")
            # TODO join?
        if self.spi:
            self.spi.close()
