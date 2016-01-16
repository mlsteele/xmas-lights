import random
from colorsys import hsv_to_rgb
import numpy as np


class Sprite(object):
    def __init__(self, strip):
        pass

    def handle_game_keys(self, keys):
        pass

    # step is guaranteed to be called before render
    def step(self, strip, t):
        pass

    def render(self, strip, t):
        raise NotImplementedError


class Snake(Sprite):
    def __init__(self, strip, offset=0, speed=1, length=10, saturation=1.0, brightness=0.5):
        self.offset = float(offset)
        self.length = int(length)
        self.speed = 60.0 * speed
        self.hue_offset = float(offset)
        self.saturation = float(saturation)
        self.brightness = float(brightness)

    def render(self, strip, t):
        offset = self.offset + self.speed * t
        brightness = self.brightness
        length = self.length
        x = int(offset)

        rgbs = np.zeros((length, 3))
        h = 0.5 * (self.hue_offset + offset) % len(strip) / len(strip)
        rgbs[:, :] = hsv_to_rgb(h, self.saturation, 1)
        brightness = np.arange(0, length) / float(length)
        rgbs[:, 0] *= brightness
        rgbs[:, 1] *= brightness
        rgbs[:, 2] *= brightness
        strip.add_rgb_array(x % len(strip), rgbs)

        # for i in xrange(length):
        #     h, v = 0.5 * bound(self.hue_offset + offset + i) / len(strip), brightness * i / length
        #     strip.add_hsv(bound(x), h, self.saturation, v)
        #     x += 1

        # # adds ~4% overhead
        # f, x = math.modf(offset + length)
        # if f > 0:
        #     strip.add_hsv(bound(int(x)), h, self.saturation, 1)


class EveryNth(Sprite):
    def __init__(self, strip, offset=0, speed=0.25, factor=0.02, v=0.5):
        self.num = int(len(strip) * factor)
        self.spacing = len(strip) / self.num
        self.speed = 60.0 * speed
        self.offset = float(offset)
        self.v = v

    def render(self, strip, t):
        offset = self.offset + self.speed * t
        r, g, b = hsv_to_rgb(0, 0, self.v)
        for i in xrange(self.num):
            x = (offset + self.spacing * i) % len(strip)
            strip.add_rgb(x, r, g, b)


class Hoop(Sprite):
    def __init__(self, strip, hue=None, saturation=0.5, offset=None, speed=None):
        self.r0 = None
        self.offset = offset or -random.random() / 10
        self.hue = hue or random.random()
        self.saturation = saturation
        self.speed = speed or random.randrange(1, 3) * 0.1
        self.reverse = random.random() < 0.25

        # for each pixel index, its ring number
        pixel_rings = np.zeros(len(strip), int)
        for index in strip.indices_near_angle(180):
            if index > 0:
                pixel_rings[index:] += 1

        # compute average radius of each ring
        ring_count = np.max(pixel_rings)  # this skips the last ring, but it looks better this way
        distances = np.tile(strip.radii, (ring_count, 1))  # D[ring_index, pixel_index] = distance
        ring_indices = np.tile(np.arange(ring_count), (len(strip), 1)).transpose()  # R[ring_index, :] = ring_index
        mask = np.equal(np.tile(pixel_rings, (ring_count, 1)), ring_indices)  # S[ri, pi] = True iff pixel pi is in ring ri
        distances *= mask  # D[ring_index] = distances of pixels on the ring; other pixels are 0
        self.ring_radii = np.sum(distances, axis=1) / np.sum(mask, axis=1)

        # ring_ends : [(start_index, 1 + end_index)]
        ring_pixel_indices = np.ma.masked_array(np.tile(np.arange(len(strip)), (ring_count, 1)), mask=np.equal(mask, False))
        self.ring_ends = zip(np.min(ring_pixel_indices, axis=1), 1 + np.max(ring_pixel_indices, axis=1))

    def render(self, strip, t):
        r0 = (self.offset + self.speed * t) % 1.0
        if self.reverse:
            r0 = 1.0 - r0

        distances = np.abs(self.ring_radii - r0)  # distance of each ring from target
        closest_indices = np.argsort(distances)[:5]
        d_sum = np.sum(distances[closest_indices])
        values = (1.0 - distances / d_sum) ** 10
        h = self.hue
        s = self.saturation
        for v, x0, x1 in ((values[i],) + self.ring_ends[i] for i in closest_indices):
            strip.add_range_hsv(x0, x1, h, s, v)


class Sparkle(Sprite):
    def __init__(self, strip):
        self.indices = []
        self.last_time = 0

    def step(self, strip, t):
        if t - self.last_time < 1 / 60.:
            return
        self.last_time = t
        self.indices = np.where(np.random.random(len(strip)) < 0.001)[0]
        n = len(self.indices)
        self.hsv = np.column_stack((np.random.random(n), np.tile(0.3, n), np.random.random(n)))

    def render(self, strip, t):
        for ii, i in enumerate(self.indices):
            strip.add_hsv(i, *self.hsv[ii])


class SparkleFade(Sprite):
    """Sparkles that fade over time.

    Attributes:
        count (int): Number of sparkles
        lifetime (float): Maximum age of a sparkle in seconds.
        max_v (float): Maximum brightness.
    """

    def __init__(self, strip, count=50, lifetime=.8, max_v=0.5):
        self.strip = strip
        self.count = count
        self.lifetime = float(lifetime)
        self.max_v = float(max_v)

        self.active = {}  # Map from index -> activation time

    def step(self, strip, t):
        expired = [ii for ii, activation_time in self.active.items() if t - activation_time > self.lifetime]
        for i in expired:
            del self.active[i]

        for i in xrange(self.count - len(self.active)):
            ix = random.randint(0, len(self.strip) - 1)
            self.active[ix] = t
            if ix > 10:
                self.active[ix] -= random.random() * self.lifetime * 0.5

    def render(self, strip, t):
        lifetime = self.lifetime
        for i, activation_time in self.active.iteritems():
            v = self.max_v * (1 - ((t - activation_time) / lifetime))
            if v > 0:
                strip.add_hsv(i, 0., 0., v)


class Sweep(Sprite):
    def __init__(self, strip):
        self.speed = 100
        self.exponent = 1

    def render(self, strip, t):
        angle = self.speed * t
        value = (strip.angles - angle) % 360 / 360
        value = value ** self.exponent
        strip.driver.leds[:, :] = value[:, np.newaxis]

        value = (strip.radii - 0.1 * t) % 1
        strip.driver.leds[:, 0] = value


class Tunnel(Sprite):
    def __init__(self, strip):
        self.front_angle = 350.0
        self.back = (self.front_angle + 180.0) % 360
        self.band_angle = 0.0
        self.band_width = 15.0

    def render(self, strip, t):
        band_angle = (self.band_angle + 4 * 60 * t) % 180
        front_angle = (self.front_angle + 1 * 60 * t) % 360
        half_width = self.band_width / 2.0
        r, g, b = hsv_to_rgb(band_angle / 90., 1.0, 0.2)
        angles = np.abs(strip.angles - front_angle)
        angles = np.minimum(angles % 360, -angles % 360)
        for i in np.where(abs(angles - band_angle) < half_width)[0]:
            strip.add_rgb(i, r, g, b)


class Droplet(Sprite):
    def __init__(self, strip):
        self.speed = 0.3
        self.start_time = None

    def step(self, strip, t):
        if self.start_time is not None and self.offset + (t - self.start_time) * self.speed < 1.2:
            return
        self.start_time = t
        self.angle = random.uniform(0, 360)
        self.offset = random.uniform(-.3, -.1)
        self.hue = random.random()
        self.indices = np.array(list(strip.indices_near_angle(self.angle)))

    def render(self, strip, t):
        offset = self.offset + (t - self.start_time) * self.speed
        distances = np.abs(strip.radii[self.indices] - offset)
        closest_indices = np.argsort(distances)[:2]
        values = (1 - distances) ** 2
        values /= np.sum(values[closest_indices])
        for i in closest_indices:
            strip.add_hsv(self.indices[i], self.hue, 0., values[i])


class Predicate(Sprite):
    def __init__(self, strip, predicate):
        self.f = predicate

    def render(self, strip, t):
        for i in xrange(len(strip)):
            if self.f(i):
                strip.add_hsv(i, 0, 0, 0.04)


class InteractiveWalk(Sprite):
    def __init__(self, strip):
        self.strip = strip
        self.pos = 124
        self.radius = 3

    def handle_game_keys(self, keys):
        if keys['left']:
            self.pos -= 1
        if keys['right']:
            self.pos += 1
        self.pos = self.pos % len(self.strip)

    def render(self, strip, t):
        for i in xrange(self.pos - self.radius, self.pos + self.radius):
            i = i % len(strip)
            strip.add_hsv(i, 0.3, 0.4, 0.2)
