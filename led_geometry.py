# from functools import lru_cache
from math import sin, cos, pi
from functools32 import lru_cache
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
    count = CONFIG['pixels']['count']

    # Iterates over pixels, returning the same Flyweight each time.
    @staticmethod
    def pixels():
        pixel = Pixel(0)
        for index, angle in enumerate(PixelAngles):
            pixel.index = index
            pixel.angle = angle
            yield pixel
            index += 1

    @staticmethod
    @lru_cache()
    def pixels_near_angle(angle):
        return list(pixel.clone() for pixel in PixelStrip.pixels_near_angle_(angle))

    @staticmethod
    def pixels_near_angle_(angle):
        a0 = None
        da0 = None
        y0 = None
        for pixel in PixelStrip.pixels():
            a = pixel.angle_from(angle)
            if a0 is not None:
                da = a - a0
                if da0 <= 0 and 0 <= da:
                    ix = pixel.index
                    if a0 < a:
                        if y0 != ix - 1:
                            y0 = ix - 1
                            yield Pixel(ix - 1)
                    else:
                        y0 = ix
                        yield Pixel(ix)
                da0 = da
            a0 = a

    @staticmethod
    def pixels_within_angles(angle, band_width=0):
        half_band = band_width / 2.0
        for pixel in PixelStrip.iter():
            if abs(pixel.angle_from(angle)) < half_band:
                yield pixel

    @staticmethod
    def angle(index):
        return PixelAngle.angle(index)

    @staticmethod
    def radius(index):
        return 1 - index / float(PixelStrip.count)

    @staticmethod
    def pos(index):
        angle = PixelStrip.angle(index) * pi / 180
        radius = PixelStrip.radius(index)
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

PixelAngles = list(PixelAngle.angle(i) for i in range(PixelStrip.count))
