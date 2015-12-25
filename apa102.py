import colorsys
import spidev

"""
Driver for APA102 LEDS (aka "DotStar").
(c) Martin Erzberger 2015

My very first Python code, so I am sure there is a lot to be optimized ;)

Public methods are:
 - setPixel
 - setPixelRGB
 - show
 - clearStrip
 - cleanup

The rest of the methods are used internally and should not be used by the user of the library.

Very brief overview of APA102: An APA102 LED is addressed with SPI. The bits are shifted in one by one,
starting with the least significant bit.

An LED usually just forwards everything that is sent to its data-in to data-out. While doing this, it
remembers its own color and keeps glowing with that color as long as there is power.

An LED can be switched to not forward the data, but instead use the data to change it's own color.
This is done by sending (at least) 32 bits of zeroes to data-in. The LED then accepts the next
correct 32 bit LED frame (with color information) as its new color setting.

After having received the 32 bit color frame, the LED changes color, and then resumes to just copying
data-in to data-out.

The really clever bit is this: While receiving the 32 bit LED frame, the LED sends zeroes on its
data-out line. Because a color frame is 32 bits, the LED sends 32 bits of zeroes to the next LED.
As we have seen above, this means that the next LED is now ready to accept a color frame and
update its color.

So that's really the entire protocol:
- Start by sending 32 bits of zeroes. This prepares LED 1 to update its color.
- Send color information one by one, starting with the color for LED 1, then LED 2 etc.
- Finish off by cycling the clock line a few times to get all data to the very last LED on the strip

The last step is necessary, because each LED delays forwarding the data a bit. Imagine ten people in
a row. When you yell the last color information, i.e. the one for person ten, to the first person in
the line, then you are not finished yet. Person one has to turn around and yell it to person 2, and
so on. So it takes ten additional "dummy" cycles until person ten knows the color. When you look closer,
you will see that not even person 9 knows the color yet. This information is still with person 2.
Essentially the driver sends additional zeroes to LED 1 as long as it takes for the last color frame
to make it down the line to the last LED.
"""
class APA102:
    def __init__(self, numLEDs, globalBrightness = 31): # The number of LEDs in the Strip
        self.numLEDs = numLEDs
        # LED startframe is three "1" bits, followed by 5 brightness bits
        self.ledstart = (globalBrightness & 0b00011111) | 0b11100000 # Don't validate; just slash off extra bits
        self.clear()
        self.spi = spidev.SpiDev()  # Init the SPI device
        self.spi.open(0, 1)  # Open SPI port 0, slave device (CS)  1
        self.spi.max_speed_hz = 8000000 # Up the speed a bit, so that the LEDs are painted faster

    """
    void clockStartFrame()
    This method clocks out a start frame, telling the receiving LED that it must update its own color now.
    """
    def clockStartFrame(self):
        self.spi.xfer2([0x00, 0x00, 0x00, 0x00])  # Start frame, 32 zero bits

    """
    void clear()
    Sets the strip color to black, does not show.
    """
    def clear(self):
        # (Re-)initialize the pixel buffer.
        self.leds = []
        # Allocate the entire buffer. If later some LEDs are not set, they will just be black, instead of crashing the
        # driver.
        for _ in range(self.numLEDs):
            self.leds.extend([self.ledstart])
            self.leds.extend([0x00] * 3)

    """
    void setPixel(ledNum, red, green, blue)
    Sets the color of one pixel in the LED stripe. The changed pixel is not shown yet on the Stripe, it is only
    written to the pixel buffer. Colors are passed individually.
    """
    def setPixel(self, ledNum, red, green, blue):
        if ledNum < 0:
            return # Pixel is invisible, so ignore
        if ledNum >= self.numLEDs:
            return # again, invsible
        startIndex = 4 * ledNum
        self.leds[startIndex] = self.ledstart
        self.leds[startIndex + 3] = red
        self.leds[startIndex + 1] = green
        self.leds[startIndex + 2] = blue

    def addPixel(self, ledNum, red, green, blue):
        if not (0 <= ledNum < self.numLEDs): return
        startIndex = 4 * ledNum
        self.leds[startIndex] = self.ledstart
        self.leds[startIndex + 3] = max(0, min(255, self.leds[startIndex + 3] + red))
        self.leds[startIndex + 1] = max(0, min(255, self.leds[startIndex + 1] + green))
        self.leds[startIndex + 2] = max(0, min(255, self.leds[startIndex + 2] + blue))

    """
    void setPixelRGB(ledNum,rgbColor)
    Sets the color of one pixel in the LED stripe. The changed pixel is not shown yet on the Stripe, it is only
    written to the pixel buffer. Colors are passed combined (3 bytes concatenated)
    """
    def setPixelRGB(self, ledNum, rgbColor):
        self.setPixel(ledNum, (rgbColor & 0xFF0000) >> 16, (rgbColor & 0x00FF00) >> 8, rgbColor & 0x0000FF)

    def addPixelRGB(self, ledNum, rgbColor):
        self.setPixel(ledNum, (rgbColor & 0xFF0000) >> 16, (rgbColor & 0x00FF00) >> 8, rgbColor & 0x0000FF)

    def setPixelHSV(self, ledNum, h, s, v):
        r, g, b = (int(255 * c) for c in colorsys.hsv_to_rgb(h, s, v))
        self.setPixel(ledNum, r, g, b)

    def addPixelHSV(self, ledNum, h, s, v):
        r, g, b = (int(255 * c) for c in colorsys.hsv_to_rgb(h, s, v))
        self.addPixel(ledNum, r, g, b)

    """
    void show()
    Sends the content of the pixel buffer to the strip.
    Todo: More than 1024 LEDs requires more than one xfer operation.
    """
    def show(self):
        self.clockStartFrame()
        self.spi.xfer2(self.leds) # SPI takes up to 4096 Integers. So we are fine for up to 1024 LEDs.

    """
    void cleanup()
    This method should be called at the end of a program in order to release the SPI device
    """
    def cleanup(self):
        self.spi.close()  # ... SPI Port schliessen
