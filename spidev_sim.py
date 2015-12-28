import sys, pygame
from math import sin, cos, pi

class SpiDev:
    def open(self, port, slave):
        pygame.init()
        self.width = 600
        self.screen = pygame.display.set_mode((self.width, self.width))
        self.screen.fill((0, 0, 0))
        self.ix = 0

    def close(self):
        pass

    def xfer2(self, values):
        for event in pygame.event.get():
            if event.type == pygame.QUIT: sys.exit()

        spacing = 10
        radius = 5
        dotsPerRow = self.width // spacing
        windings = 9
        pixelCount = 900
        i = 0
        while i < len(values):
            frame = values[i]; i += 1
            g = values[i]; i += 1
            b = values[i]; i += 1
            r = values[i]; i += 1
            if frame == 0x0:
                self.ix = pixelCount
                continue
            assert (frame & 0xe0) == 0xe0
            brightness = frame & 0x1f
            r, g, b = (c * brightness / 0x1f for c in (r, g, b))
            self.ix -= 1
            a = self.ix * 2 * windings * pi / pixelCount
            r_ = self.ix / float(pixelCount)
            x = (1.0 + r_ * cos(a)) * (self.width - radius) / 2.0
            y = (1.0 + r_ * sin(a)) * (self.width - radius) / 2.0
            pygame.draw.circle(self.screen, (r, g, b), (int(round(x)), int(round(y))), radius)
        pygame.display.update()
