import yaml
from math import sin, cos, pi

with open('geometry.yaml') as f:
    CONFIG = yaml.safe_load(f)

NUMPIXELS = CONFIG['pixels']['count'] # Number of LEDs in strip

class Pixel(object):
    def __init__(self, index):
        self.index = index

    @property
    def angle(self):
        return PixelAngle.angle(self.index)

    @property
    def radius(self):
        return Pixels.radius(self.index)

    def angle_from(self, angle):
        d = abs(self.angle - angle)
        return min(d % 360, -d % 360)

class Pixels(object):
    count = NUMPIXELS

    # Iterates over pixels, returning the same Flyweight each time.
    @staticmethod
    def iter():
        pixel = Pixel(0)
        while pixel.index < NUMPIXELS:
            yield pixel
            pixel.index += 1

    @staticmethod
    def near_angle(angle, band_width=0):
        half_band = band_width / 2.0
        for pixel in Pixels.iter():
            if abs(pixel.angle_from(angle)) < half_band:
                yield pixel

    @staticmethod
    def angle(index):
        return PixelAngle.angle(index)

    @staticmethod
    def radius(index):
        return 1 - index / float(NUMPIXELS)

    @staticmethod
    def pos(index):
        angle = Pixels.angle(index) * pi / 180
        radius = Pixels.radius(index)
        x = 0.5 + radius * cos(angle) / 2.0
        y = 0.5 + radius * sin(angle) / 2.0
        return (x, y)

class PixelAngle(object):
    # Map from pixel indices to angles in degrees.
    # The front face of the tree is 0.
    # Angles increase CCW looking from the heavens.
    REF_ANGLES = {}
    for angle, indices in CONFIG['pixels']['angles'].items():
        for index in indices:
            REF_ANGLES[index] = angle

    cache = {}

    @staticmethod
    def angle(i):
        """Get the angle of a pixel.
        Estimate by linear approximation between two closest known neighbors.
        """
        if i in PixelAngle.cache:
            return PixelAngle.cache[i]

        if i in PixelAngle.REF_ANGLES.keys():
            return float(PixelAngle.REF_ANGLES[i])

        left_i, right_i = PixelAngle.closest(i)
        left_a, right_a = PixelAngle.REF_ANGLES[left_i], PixelAngle.REF_ANGLES[right_i]
        if right_a <= left_a:
            right_a += 360
        ratio = (i - left_i) / float(right_i - left_i)
        predicted = (left_a * (1 - ratio) + right_a * ratio)
        predicted %= 360

        PixelAngle.cache[i] = predicted
        return predicted

    @staticmethod
    def closest(i):
        """Get the closest known neighbor(s) of a pixel."""
        items = PixelAngle.REF_ANGLES.keys()
        assert i not in items
        lesser = [x for x in items if x < i]
        greater = [x for x in items if x > i]
        left_i = sorted(lesser, key=lambda x: abs(x - i))[0]
        right_i = sorted(greater, key=lambda x: abs(x - i))[0]
        return (left_i, right_i)
