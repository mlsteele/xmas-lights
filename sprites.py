import random
from colorsys import hsv_to_rgb
import numpy as np


class Scene(object):
    @classmethod
    def get_subclasses(cls):
        for subclass in cls.__subclasses__():
            yield subclass
            for descendant in subclass.get_subclasses():
                yield descendant

    def __init__(self, strip):
        pass

    def handle_game_keys(self, keys):
        pass

    # step is guaranteed to be called before render
    def step(self, strip, t):
        pass

    def render(self, strip, t):
        raise NotImplementedError


class Sprite(Scene):
    def __init__(self, strip, offset=0, speed=60):
        self.offset = offset or random.choice(range(len(strip)))
        self.speed = float(speed)
        self.last_time = None

    def step(self, strip, t):
        if self.last_time:
            self.offset += self.speed * (t - self.last_time)
            self.offset %= len(strip)
        self.last_time = t

    def render(self, strip, t):
        if hasattr(self, 'pixels'):
            strip.add_rgb_array(int(self.offset), np.array(self.pixels))


class Snake(Sprite):
    def __init__(self, strip, length=10, saturation=1.0, brightness=0.5, **kwargs):
        super(self.__class__, self).__init__(strip, **kwargs)
        self.length = int(length)
        self.hue_offset = float(self.offset)
        self.saturation = float(saturation)
        self.brightness = float(brightness)
        self.pixels = np.zeros((length, 3))

    def step(self, strip, t):
        super(self.__class__, self).step(strip, t)
        brightness = self.brightness
        length = self.length

        pixels = self.pixels
        h = 0.5 * (self.hue_offset + self.offset) % len(strip) / len(strip)
        pixels[:, :] = hsv_to_rgb(h, self.saturation, 1)
        brightness = np.arange(0, length) / float(length)
        pixels[:, 0] *= brightness
        pixels[:, 1] *= brightness
        pixels[:, 2] *= brightness

        # f, x = math.modf(offset + length)
        # if f > 0:
        #     strip.add_hsv(bound(int(x)), h, self.saturation, 1)


class Slices(Scene):
    def render(self, strip, t):
        speeds = np.array([.4, .5, .6])
        strip.driver.leds[:, :] = (strip.pos + t * speeds) % 1


class EveryNth(Scene):
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


class Hoop(Scene):
    def __init__(self, strip, hue=None, saturation=0.5, offset=None, speed=None):
        self.r0 = None
        self.offset = offset or -random.random() / 10
        self.hue = hue or random.random()
        self.saturation = saturation
        self.speed = speed or random.randrange(1, 3) * 0.1
        self.reverse = random.random() < 0.25

        # ring_ends : [(start_index, 1 + end_index)]
        ring_count = np.max(strip.pixel_ring) + 1
        ring_pixel_indices = np.ma.masked_array(np.tile(np.arange(len(strip)), (ring_count, 1)), mask=np.equal(strip.ring_mask, False))
        self.ring_ends = zip(np.min(ring_pixel_indices, axis=1), 1 + np.max(ring_pixel_indices, axis=1))

    def render(self, strip, t):
        r0 = (self.offset + self.speed * t) % 1.0
        if self.reverse:
            r0 = 1.0 - r0

        distance = (strip.ring_radius - r0) % 1
        distance = np.minimum(np.abs(distance), np.abs(1 - distance)) ** 2
        closest_ring = np.argsort(distance)[:3]
        d_sum = np.sum(distance[closest_ring])
        value = (1.0 - distance / d_sum) ** 5
        h = self.hue
        s = self.saturation
        for v, x0, x1 in ((value[i],) + self.ring_ends[i] for i in closest_ring):
            strip.add_range_hsv(x0, x1, h, s, v)


class Sparkle(Scene):
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


class SparkleFade(Scene):
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


class Sweep(Scene):
    def __init__(self, strip):
        self.a_speed = 100
        self.r_speed = 0.1
        self.exponent = 1

    def render(self, strip, t):
        angle = self.a_speed * t
        value = (strip.angle - angle) % 360 / 360
        value = value ** self.exponent
        strip.driver.leds[:, :] = value[:, np.newaxis]

        i = int((self.r_speed * t) % 3)
        value = (strip.radius - self.r_speed * t) % 1
        strip.driver.leds[:, i] = value


class Tunnel(Scene):
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
        angles = np.abs(strip.angle - front_angle)
        angles = np.minimum(angles % 360, -angles % 360)
        for i in np.where(abs(angles - band_angle) < half_width)[0]:
            strip.add_rgb(i, r, g, b)


class Droplet(Scene):
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
        distance = np.abs(strip.radius[self.indices] - offset)
        closest_pixel = np.argsort(distance)[:2]
        value = (1 - distance) ** 2
        value /= np.sum(value[closest_pixel])
        for i in closest_pixel:
            strip.add_hsv(self.indices[i], self.hue, 0., value[i])


class Predicate(Scene):
    def __init__(self, strip, predicate):
        self.f = predicate

    def render(self, strip, t):
        for i in xrange(len(strip)):
            if self.f(i):
                strip.add_hsv(i, 0, 0, 0.04)


class InteractiveWalk(Scene):
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


class RedOrGreenSnake(Sprite):
    def __init__(self, strip, brightness=0.3, **kwargs):
        super(self.__class__, self).__init__(strip, **kwargs)
        self.brightness = float(brightness)
        self.length = 20
        self.hue = random.choice([0, .33])

        r, g, b = hsv_to_rgb(self.hue, 1, self.brightness)
        self.pixels = [[r, g, b]] * self.length
