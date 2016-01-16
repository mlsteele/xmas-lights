# from functools import lru_cache
from math import sin, cos, pi
from functools32 import lru_cache
import numpy as np
import apa102
import yaml


# source: http://code.activestate.com/recipes/578231-probably-the-fastest-memoization-decorator-in-the-/
# This is faster than explicitly memoizing into a list or array.
def memoize(f):
    class MemoDict(dict):
        __slots__ = ()

        def __missing__(self, key):
            self[key] = ret = f(key)
            return ret
    return MemoDict().__getitem__

with open('geometry.yaml') as f:
    CONFIG = yaml.safe_load(f)


class Pixel(object):
    def __init__(self, index):
        self.index = index

    def clone(self):
        clone = Pixel(self.index)
        clone.angle = self.angle
        return clone

    # faster than @property
    def __getattr__(self, name):
        if name == 'angle':
            self.angle = PixelAngle.angle(self.index)
            return self.angle
        raise AttributeError(name)

    def angle_from(self, angle):
        d = abs(self.angle - angle)
        return min(d % 360, -d % 360)


class PixelStrip(object):
    strips = {}

    def __init__(self, bus=0, device=1):
        # Must set before creating the driver, since the driver can create a child process that needs access
        # to the dictionary that this sets.
        PixelStrip.set(bus, device, self)

        self.count = count = CONFIG['pixels']['count']
        self.angles = np.array([PixelAngle.angle(i) for i in xrange(count)])
        self.radii = np.array([1 - i / float(count) for i in xrange(count)])

        self.driver = apa102.APA102(self.count, bus=bus, device=device)
        for w in ['clear', 'close', 'show', 'add_hsv', 'add_rgb', 'add_range_hsv', 'add_rgb_array', 'set_hsv']:
            setattr(self, w, getattr(self.driver, w))

    @staticmethod
    def set(bus, device, instance):
        PixelStrip.strips[(bus, device)] = instance

    @staticmethod
    def get(bus, device):
        return PixelStrip.strips[(bus, device)]

    def __len__(self):
        return self.count

    # Iterates over LEDs, returning the same Flyweight each time.
    def __iter__(self):
        pixel = Pixel(0)
        for index, angle in enumerate(self.angles):
            pixel.index = index
            pixel.angle = angle
            yield pixel
            index += 1

    @lru_cache()
    def indices_near_angle(self, angle):
        return list(i for i in self._indices_near_angle(angle))

    def _indices_near_angle(self, angle):
        a0 = None
        da0 = None
        y0 = None
        for pixel in self:
            a = pixel.angle_from(angle)
            if a0 is not None:
                da = a - a0
                if da0 <= 0 and 0 <= da:
                    ix = pixel.index
                    if a0 < a:
                        if y0 != ix - 1:
                            y0 = ix - 1
                            yield ix - 1
                    else:
                        y0 = ix
                        yield ix
                da0 = da
            a0 = a

    def angle(self, index):
        return PixelAngle.angle(index)

    def pos(self, index):
        angle = self.angle(index) * pi / 180
        radius = self.radii[index]
        x = 0.5 + radius * cos(angle) / 2.0
        y = 0.5 + radius * sin(angle) / 2.0
        return (x, y)


class PixelAngle(object):
    # Map from pixel indices to angles in degrees.
    # The front face of the tree is 0.
    # Angles increase CCW looking from the heavens.
    REF_ANGLES = {}
    for angle, indices in CONFIG['pixels']['angles'].items():
        angle = float(angle)
        for i in indices:
            REF_ANGLES[i] = angle

    @staticmethod
    @memoize
    def angle(i):
        """Get the angle of a pixel.

        Estimate by linear approximation between two closest known neighbors.
        """
        angle = PixelAngle.REF_ANGLES.get(i)
        if angle is not None:
            return angle

        keys = PixelAngle.REF_ANGLES.keys()
        i0 = max(j for j in keys if j <= i)
        i1 = min(j for j in keys if i <= j)
        a0, a1 = PixelAngle.REF_ANGLES[i0], PixelAngle.REF_ANGLES[i1]
        if a1 <= a0:
            a1 += 360
        ratio = (i - i0) / float(i1 - i0)
        return (a0 * (1 - ratio) + a1 * ratio) % 360
