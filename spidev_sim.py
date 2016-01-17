import os
import re
import sys
import numpy as np

gamma = 2.5


class SPI(object):
    def __init__(self, devpath, mode, max_speed_hz):
        self.spidev = SpiDev()
        m = re.match(r'/dev/spidev(\d+).(\d+)', devpath)
        assert m
        bus, device = (int(n) for n in m.groups())
        self.spidev.open(bus, device)

    def transfer(self, data):
        self.spidev.xfer2(np.fromstring(data, 'uint8'))

    def close(self):
        self.spidev.close()


class SpiDev(object):
    def open(self, bus, device):
        self.bus = bus
        self.device = device

        self.pygame = None
        if not os.environ.get('SPIDEV_PYGAME'):
            return

        import pygame
        self.pygame = pygame
        pygame.init()
        self.width = 600
        self.screen = pygame.display.set_mode((self.width, self.width))
        self.screen.fill((0, 0, 0))
        self.ix = 0  # next pixel index

    @property
    def strip(self):
        # FIXME This is called after `open`, because the led_geometry->apa102->spidev_sim->led_geometry
        # circular dependency prevents PixelStrip from being defined when this object is opened.
        if not hasattr(self, '__strip'):
            from led_geometry import PixelStrip
            self.__strip = PixelStrip.get(self.bus, self.device)
        return self.__strip

    def close(self):
        if self.pygame:
            self.pygame.quit()

    def xfer2(self, data):
        pygame = self.pygame
        if not pygame:
            return

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                sys.exit()

        inverse_gamma = 1 / gamma
        led_size = 5
        width = self.width

        frames = np.array(data).reshape(-1, 4)
        for pixels in np.split(frames, np.where(np.all(frames == 0, axis=1))[0]):
            if not pixels.size:
                continue

            if np.all(pixels[0] == 0):
                self.ix = 0
                pixels = np.delete(pixels, 0, axis=0)

            rows = pixels.shape[0]
            indices = self.ix + np.arange(rows)
            self.ix += rows

            pos = np.round(self.strip.pos[indices][:, :-1] * (width - led_size)).astype(int)

            assert np.all(np.bitwise_and(pixels[:, 0], 0xe0) == 0xe0)
            rgbf = np.fliplr(pixels[:, 1:]) / 255. * (np.bitwise_and(0x1f, pixels[:, 0]) / 31)[:, np.newaxis]
            rgbi = (rgbf ** inverse_gamma * 255.).astype(int)
            for i in xrange(0, rows):
                pygame.draw.circle(self.screen, rgbi[i], pos[i], led_size)

        pygame.display.update()
