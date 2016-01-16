# from functools import lru_cache
from math import pi
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


class PixelStrip(object):
    strips = {}

    def __init__(self, bus=0, device=1):
        # Must set before creating the driver, since the driver can create a child process that needs access
        # to the dictionary that this sets.
        PixelStrip.set(bus, device, self)

        self.count = count = CONFIG['pixels']['count']

        angle_samples = np.array(sorted((x, a) for a, xs in CONFIG['pixels']['angles'].items() for x in xs))
        # Assume samples are monotonically increasing. Whenever two consecutive samples violate this, add another wind.
        for i in np.nditer(np.where(np.diff(angle_samples[:, 1]) <= 0)):
            angle_samples[i + 1:, 1] += 360
        self.angles = np.interp(np.arange(count), angle_samples[:, 0], angle_samples[:, 1]) % 360

        self.radii = np.linspace(1, 0, num=count, endpoint=False)

        angles_r = self.angles * pi / 180
        self.xy = 0.5 + 0.5 * np.column_stack((self.radii * np.cos(angles_r), self.radii * np.sin(angles_r)))
        # self.xyz = np.column_stack((self.radii * np.cos(self.angles), self.radii * np.cos(self.angles), np.))

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

    # Iterates over pixel indices
    def __iter__(self):
        for i in xrange(self.count):
            yield i

    def indices_near_angle(self, angle):
        # FIXME misses the endpoints
        angles = np.abs((self.angles - angle) % 360)
        return 1 + (np.diff(np.sign(np.diff(angles))) > 0).nonzero()[0]
