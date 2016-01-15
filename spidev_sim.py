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

    def xfer2(self, bytes):
        pygame = self.pygame
        if not pygame:
            return
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                sys.exit()

        width = self.width
        led_size = 5
        ix = self.ix
        inverse_gamma = 1 / gamma
        for i in xrange(0, len(bytes), 4):
            frame = bytes[i]
            g = bytes[i + 1]
            b = bytes[i + 2]
            r = bytes[i + 3]
            i += 4

            if frame == 0x0:
                ix = 0
                continue

            assert (frame & 0xe0) == 0xe0
            brightness = frame & 0x1f
            r, g, b = (c * brightness / 0x1f for c in (r, g, b))
            r, g, b = (int(255 * ((c / 255.0) ** inverse_gamma)) for c in (r, g, b))
            ix += 1
            x, y = self.strip.pos(ix)
            x = x * (width - led_size)
            y = y * (width - led_size)
            pygame.draw.circle(self.screen, (r, g, b), (int(round(x)), int(round(y))), led_size)
        self.ix = ix
        pygame.display.update()
