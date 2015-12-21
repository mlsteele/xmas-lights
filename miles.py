#!/usr/bin/python

# Simple strand test for Adafruit Dot Star RGB LED strip.
# This is a basic diagnostic tool, NOT a graphics demo...helps confirm
# correct wiring and tests each pixel's ability to display red, green
# and blue and to forward data down the line.  By limiting the number
# and color of LEDs, it's reasonably safe to power a couple meters off
# USB.  DON'T try that with other code!

import time
import colorsys
from dotstar import Adafruit_DotStar

NUMPIXELS = 600 # Number of LEDs in strip

# Here's how to control the strip from any two GPIO pins:
datapin   = 23
clockpin  = 24
strip     = Adafruit_DotStar(NUMPIXELS, datapin, clockpin, order="bgr")

strip.begin()           # Initialize pins for output
strip.setBrightness(30) # Limit brightness (out of 255)

head = 0
length = 10
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

while True:
        strip.show()
        time.sleep(1.0 / 60)
        print Color.hex_to_hsv(GREEN)

        for i in xrange(NUMPIXELS):
                strip.setPixelColor(i, BLACK)

        for i in xrange(length):
                h, s, v = ((head+i)/float(NUMPIXELS)*2.), 1, 255 * (i/float(length))
                strip.setPixelColor(head + i, Color.hsv_to_hex(h, s, v))

        head = bound(head + 1)
