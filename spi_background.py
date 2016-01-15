import logging
import os
from multiprocessing import Process, Queue
import cPickle as pickle

# TODO DRY apa102.py
try:
    import periphery
except ImportError:
    import spidev_sim as periphery

logger = logging.getLogger("spidev")
if "spidev" in os.environ.get("DEBUG", "").split(","):
    logger.setLevel(logging.INFO)


class SpiMaster(object):
    def __init__(self, **kwargs):
        self.frame_no = 0
        self.queue = queue = Queue(1)
        self.p = p = Process(name='spi_slave', target=SpiWorker.run, args=(queue, kwargs))
        p.daemon = True
        p.start()

    def transfer(self, data):
        self.xfer2(data)

    def xfer2(self, data):
        self.frame_no += 1
        logger.info('enqueue frame #%d', self.frame_no)
        self.queue.put(pickle.dumps(data, protocol=-1))

    def close(self):
        self.queue.put("close")
        self.p.join()


class SpiWorker(object):
    @staticmethod
    def run(q, initargs):
        logger.info('creating SPI worker')
        instance = SpiWorker(q, **initargs)
        while True:
            item = q.get()
            if isinstance(item, str) and item == "close":
                instance.close()
                return
            data = pickle.loads(item)
            instance.xfer2(data)

    def __init__(self, queue, bus=0, device=1, max_speed_hz=0):
        self.frame_no = 0
        self.queue = queue
        self.spi = periphery.SPI('/dev/spidev%d.%d' % (bus, device), 0, max_speed_hz)

    def xfer2(self, data):
        self.frame_no += 1
        logger.info('send frame #%d', self.frame_no)
        self.spi.transfer(data)

    def close(self):
        self.spi.close()
