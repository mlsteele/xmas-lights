import math, numpy
from colorsys import hsv_to_rgb

try:
    import spidev
except ImportError:
    print "spidev not found; using simulator"
    import spidev_sim as spidev

def createSpiSlave(count, q):
    print 'creating background', count, q
    strip = APA102(count, queue=q, master=False)
    while True:
        command = q.get()
        if isinstance(command, str) and command == "close":
            strip.close()
            return
        strip.leds = command
        strip.show()

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

    def show(self):
        self.frame_no += 1
        if self.is_master and self.queue:
            # print 'enqueue frame #', self.frame_no
            self.queue.put(self.leds)
        if self.spi:
            # print 'send frame #', self.frame_no
            bytes = numpy.ravel(255 * numpy.clip(self.leds, 0.0, 1.0)).astype(int)
            bytes[::4] = 0xff
            self.spi.xfer2([0, 0, 0, 0])
            self.spi.xfer2(bytes.tolist())

    def close(self):
        if self.is_master and self.queue:
            self.queue.put("close")
            # TODO join?
        if self.spi:
            self.spi.close()
