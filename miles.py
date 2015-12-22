#!/usr/bin/python

import time
import colorsys
import random
from dotstar import Adafruit_DotStar

NUMPIXELS = 900 # Number of LEDs in strip

# Here's how to control the strip from any two GPIO pins:
datapin   = 23
clockpin  = 24
strip     = Adafruit_DotStar(NUMPIXELS, datapin, clockpin, order="bgr")

strip.begin()           # Initialize pins for output
strip.setBrightness(255) # Limit brightness (out of 255)

RED = 0xff0000
GREEN = 0x00ff00
BLUE = 0x0000ff
BLACK = 0x000
WHITE = 0xffffff

def bound(x):
    return x % NUMPIXELS

class Color(object):
    @staticmethod
    def hex_to_rgb(hex_color):
        return ((hex_color & 0xff0000) >> 16,
            (hex_color & 0x00ff00) >> 8,
            (hex_color & 0x0000ff))

    @staticmethod
    def rgb_to_hex(r, g, b):
        return (r << 16) | (g << 8) | b

    @staticmethod
    def hex_to_hsv(hex_color):
        return colorsys.rgb_to_hsv(*Color.hex_to_rgb(hex_color))

    @staticmethod
    def hsv_to_hex(h, s, v):
        return Color.rgb_to_hex(*map(int, colorsys.hsv_to_rgb(h, s, v)))

class Snake(object):
    def __init__(self, head=0, speed=1):
        self.head = int(head)
        self.head_f = float(int(head))
        self.length = 10
        self.speed = speed
        self.hue_offset = head

    def step(self):
        self.head_f = bound(self.head_f + self.speed)
        self.head = bound(int(self.head_f))

    def show(self):
        for i in xrange(self.length):
            h, s, v = ((self.hue_offset+self.head+i)/float(NUMPIXELS)*2.), 1, 30 * i / float(self.length)
            strip.setPixelColor(self.head + i, Color.hsv_to_hex(h, s, v))

class EveryNth(object):
    def __init__(self, factor=0.02):
        self.num = int(NUMPIXELS * factor)
        self.skip = int(NUMPIXELS / self.num)
        self.offset = 0

    def step(self):
        self.offset += 1
        self.offset %= self.skip

    def show(self):
        for i in xrange(self.num):
            strip.setPixelColor(self.offset + self.skip * i, Color.hsv_to_hex(0, 0, 10))

class Sparkle(object):
    def step(self):
        pass

    def show(self):
        for i in xrange(NUMPIXELS):
            if random.random() > 0.999:
                strip.setPixelColor(i, Color.hsv_to_hex(random.random(), 0.3, random.random()*30))

def strip_clear():
    for i in xrange(NUMPIXELS):
        strip.setPixelColor(i, BLACK)

N_SNAKES = 15

sprites = []
sprites.extend(Snake(head=i*(NUMPIXELS / float(N_SNAKES)), speed=(1+(0.3*i))*random.choice([1, -1])) for i in xrange(N_SNAKES))
sprites.append(EveryNth(factor=0.1))
sprites.append(Sparkle())

last_frame_t = time.time()
ideal_frame_delta_t = 1.0 / 60
while True:
    frame_t = time.time()
    delta_t = frame_t - last_frame_t
    if delta_t < ideal_frame_delta_t:
        time.sleep(ideal_frame_delta_t - delta_t)
    last_frame_t = time.time()

    strip_clear()

    for sprite in sprites:
        sprite.show()
        sprite.step()

    strip.show()
