import time
import apa102

NUMPIXELS = 900 # Number of LEDs in strip

strip = apa102.APA102(NUMPIXELS)

def main():
    for i in xrange(110, NUMPIXELS):
        print i
        strip.setPixelRGB(i, 0x0fff0)
        strip.setPixelRGB(i-3, 0x000000)
        strip.show()
        time.sleep(0.08)

if __name__ == "__main__":
    try:
        main()
    finally:
        strip.cleanup()
