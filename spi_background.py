import logging
import os
import signal
from multiprocessing import Process, Queue
import cPickle as pickle

# TODO DRY apa102.py
try:
    import periphery
except ImportError:
    import spidev_sim as periphery

mlogger = logging.getLogger('spi-master')
wlogger = logging.getLogger('spi-worker')
if 'spidev' in os.environ.get('DEBUG', '').split(','):
    mlogger.setLevel(logging.INFO)
    wlogger.setLevel(logging.INFO)


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
        mlogger.info('enqueue frame #%d', self.frame_no)
        self.queue.put(pickle.dumps(data, protocol=-1))

    def close(self):
        mlogger.info('close SPI master')
        self.queue.put('close')
        self.p.join()


class SpiWorker(object):
    @staticmethod
    def run(q, initargs):
        wlogger.info('creating SPI worker')
        # ignore SIGINT, so that the parent can clean up and then send a 'close' command instead.
        # Maybe the worker should be in a different process group, instead?
        signal.signal(signal.SIGINT, signal.SIG_IGN)
        instance = SpiWorker(q, **initargs)
        while True:
            item = q.get()
            if isinstance(item, str) and item == 'close':
                wlogger.info('close SPI worker')
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
        wlogger.info('send frame #%d', self.frame_no)
        self.spi.transfer(data)

    def close(self):
        self.spi.close()
