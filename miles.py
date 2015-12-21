#!/usr/bin/python

# Simple strand test for Adafruit Dot Star RGB LED strip.
# This is a basic diagnostic tool, NOT a graphics demo...helps confirm
# correct wiring and tests each pixel's ability to display red, green
# and blue and to forward data down the line.  By limiting the number
# and color of LEDs, it's reasonably safe to power a couple meters off
# USB.  DON'T try that with other code!

import time
import colorsys
import random
from dotstar import Adafruit_DotStar

NUMPIXELS = 900 # Number of LEDs in strip
# We have 300 LEDs per strip.

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
        self.length = 10
        self.speed = int(speed)
        self.hue_offset = head

    def step(self):
        self.head = bound(self.head + self.speed)

    def show(self):
        for i in xrange(self.length):
            h, s, v = ((self.hue_offset+self.head+i)/float(NUMPIXELS)*2.), 1, 30 * (i/float(self.length))
            strip.setPixelColor(self.head + i, Color.hsv_to_hex(h, s, v))
            # strip.setPixelColor(self.head + i, Color.hsv_to_hex(0, 1, 30))

def strip_clear():
    for i in xrange(NUMPIXELS):
        strip.setPixelColor(i, BLACK)

N_SNAKES = 15
snakes = [Snake(head=i*(NUMPIXELS / float(N_SNAKES)), speed=(1+(0.3*i))*random.choice([1, -1])) for i in xrange(N_SNAKES)]

while True:
    strip.show()
    time.sleep(1.0 / 60)

    strip_clear()

    for snake in snakes:
        snake.show()
        snake.step()

    for i in xrange(NUMPIXELS):
        if random.random() > 0.99:
            strip.setPixelColor(i, Color.hsv_to_hex(random.random(), 0.4, random.random()*10))
