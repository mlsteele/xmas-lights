import random
import time
from led_geometry import PixelStrip

def bound(x):
    return x % PixelStrip.count

class Sprite(object):
    def handle_game_keys(self, keys):
        pass

    # step is guaranteed to be called before render
    def step(self):
        pass

    def render(self, strip, t):
        raise NotImplementedError

class Snake(Sprite):
    def __init__(self, head=0, speed=1, brightness=0.5):
        self.head = head
        self.brightness = float(brightness)
        self.length = 10
        self.speed = 60.0 * speed
        self.hue_offset = head

    def render(self, strip, t):
        head = self.head + self.speed * t
        for i in xrange(self.length):
            h, s, v = 0.5 * (self.hue_offset+head+i) / PixelStrip.count, 1, self.brightness * i / self.length
            strip.addPixelHSV(bound(int(head) + i), h, s, v)

class EveryNth(Sprite):
    def __init__(self, offset=0, speed=0.25, factor=0.02, v=0.5):
        self.num = int(PixelStrip.count * factor)
        self.skip = int(PixelStrip.count / self.num)
        self.speed = 60.0 * speed
        self.offset = float(offset)
        self.v = v

    def render(self, strip, t):
        offset = (self.offset + self.speed * t)
        for i in xrange(self.num):
            x = int(bound(offset + self.skip * i))
            strip.addPixelHSV(x, 0, 0, self.v)

class Sparkle(Sprite):
    def render(self, strip, t):
        for i in xrange(PixelStrip.count):
            if random.random() > 0.999:
                strip.addPixelHSV(i, random.random(), 0.3, random.random())

class SparkleFade(Sprite):
    def __init__(self, interval=0.01, max_age=.8, max_v=0.5):
        """Sparkles that fade over time.

        Args:
            interval: How often a new spark appears.
            max_age: Maximum age of a sparkle in seconds.
            max_v: Maximum brightness.
        """
        self.interval = float(interval)
        self.max_age = float(max_age)
        self.max_v = float(max_v)

        # Map from index -> activation time
        self.active = {}
        self.last_appear = time.time()

    def step(self):
        intervals_passed = (time.time() - self.last_appear) / self.interval
        for _ in xrange(int(min(intervals_passed, 10))):
            # Create a new pixel.
            self.last_appear = time.time()
            i = random.randint(0, PixelStrip.count-1)
            self.active[i] = time.time()

        for i, activation_time in self.active.items():
            age = time.time() - activation_time
            if age > self.max_age:
                del self.active[i]

    def render(self, strip, t):
        for i, activation_time in self.active.iteritems():
            age = time.time() - activation_time
            v_factor = 1 - (age / self.max_age)
            v = v_factor * self.max_v
            strip.addPixelHSV(i, 0, 0.0, v)

class Tunnel(Sprite):
    def __init__(self):
        self.front_angle = 350.0
        self.back = (self.front_angle + 180.0) % 360
        self.band_angle = 0.0
        self.band_width = 15.0

    def render(self, strip, t):
        band_angle = (self.band_angle + 4 * 60 * t) % 180
        front_angle = (self.front_angle + 1 * 60 * t) % 360
        half_width = self.band_width / 2.0
        for pixel in PixelStrip.pixels():
            angle = pixel.angle_from(front_angle)
            if abs(angle - band_angle) < half_width:
                strip.addPixelHSV(pixel.index, band_angle / 90., 1.0, 0.2)

class Drips(Sprite):
    def __init__(self):
        self.angle = 360 * random.random()
        self.hue = random.random()
        self.radius = random.random()

    def step(self):
        self.radius += 0.005
        if self.radius > 1.1:
            self.radius -= 1.2
            self.angle = 360 * random.random()
            self.hue = random.random()

    def render(self, strip, t):
        for pixel in PixelStrip.pixels_near_angle(self.angle):
            dr = abs(pixel.radius - self.radius)
            b = (1 - dr) ** 6
            strip.addPixelHSV(pixel.index, self.hue, 0, b)

class Predicate(Sprite):
    def __init__(self, predicate):
        self.f = predicate

    def render(self, strip, t):
        for i in xrange(PixelStrip.count):
            if self.f(i):
                strip.addPixelHSV(i, 0, 0, 0.04)

class InteractiveWalk(Sprite):
    def __init__(self):
        self.pos = 124
        self.radius = 3

    def handle_game_keys(self, keys):
        if keys["left"]:
            self.pos -= 1
        if keys["right"]:
            self.pos += 1
        self.pos = bound(self.pos)

    def render(self, strip, t):
        for i in xrange(self.pos - self.radius, self.pos + self.radius):
            i = bound(i)
            strip.addPixelHSV(i, 0.3, 0.4, 0.2)
