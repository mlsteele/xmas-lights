#!/usr/bin/python

import time
import random
import signal
from math import sin, cos, pi
import apa102
from messages import get_message

NUMPIXELS = 900 # Number of LEDs in strip

strip = apa102.APA102(NUMPIXELS)

gamekeys = {
    "left": False,
    "right": False,
    "fire": False,
}

RED   = 0xff0000
GREEN = 0x00ff00
BLUE  = 0x0000ff
BLACK = 0x000000
WHITE = 0xffffff

class PixelAngle(object):
    # Map from pixel indices to angles in degrees.
    # The front face of the tree is 0.
    # Angles increase CCW looking from the heavens.
    REF_ANGLES = {
        0: 180,
        120: 0,
        336: 0,
        527: 0,
        648: 0,
        737: 0,
        814: 0,
        862: 0,
        876: 0,
        886: 0,
        NUMPIXELS: 180,
    }

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

def angdist(x, y):
    """Minimum distance between two angles (in degrees)."""
    x = (x + 360) % 360
    y = (y + 360) % 360
    return min([abs((x - y) % 360), abs((y - x) % 360)])

def bound(x):
    return x % NUMPIXELS

class Profiler:
    def __init__(self, name="_"):
        self.name = name

    # Thanks to:
    # http://preshing.com/20110924/timing-your-code-using-pythons-with-statement/
    def __enter__(self):
        self.start = time.time()
        return self

    def __exit__(self, *args):
        self.end = time.time()
        self.interval = self.end - self.start
        print "profiled {}: {:.0f} (ms)".format(self.name, self.interval * 1000)

class Snake(object):
    def __init__(self, head=0, speed=1, brightness=0.5):
        self.head = int(head)
        self.head_f = float(int(head))
        self.brightness = float(brightness)
        self.length = 10
        self.speed = speed
        self.hue_offset = head

    def step(self):
        self.head_f = bound(self.head_f + self.speed)
        self.head = bound(int(self.head_f))

    def show(self):
        for i in xrange(self.length):
            h, s, v = 0.5 * (self.hue_offset+self.head+i) / NUMPIXELS, 1, self.brightness * i / self.length
            strip.addPixelHSV(bound(self.head + i), h, s, v)

class EveryNth(object):
    def __init__(self, speed=1, factor=0.02, v=0.5):
        self.num = int(NUMPIXELS * factor)
        self.skip = int(NUMPIXELS / self.num)
        self.speed = speed
        self.offset = 0
        self.v = v

    def step(self):
        self.offset += self.speed
        self.offset %= self.skip

    def show(self):
        for i in xrange(self.num):
            x = bound(int(self.offset + self.skip * i))
            strip.addPixelHSV(x, 0, 0, self.v)

class Sparkle(object):
    def step(self):
        pass

    def show(self):
        for i in xrange(NUMPIXELS):
            if random.random() > 0.999:
                strip.addPixelHSV(i, random.random(), 0.3, random.random())

class SparkleFade(object):
    def __init__(self, interval=0.01, max_age=.8, max_v=0.5):
        """Sparkles that fade over time.

        Args:
            interval: How often a new spark appears.
            max_age: Maximuma age of a sparkle in seconds.
            max_v: Maximum brightness.
        """
        self.interval = float(interval)
        self.max_age = float(max_age)
        self.max_v = float(max_v)

        # Map from index -> activation time
        self.active = {}
        self.last_appear = time.time()

    def step(self):
        intervals_passed = (time.time() - self.last_appear) / self.interval
        for _ in xrange(int(min(intervals_passed, 10))):
            # Create a new pixel.
            self.last_appear = time.time()
            i = random.randint(0, NUMPIXELS-1)
            self.active[i] = time.time()

        for i, activation_time in self.active.items():
            age = time.time() - activation_time
            if age > self.max_age:
                del self.active[i]

    def show(self):
        for i, activation_time in self.active.iteritems():
            age = time.time() - activation_time
            v_factor = 1 - (age / self.max_age)
            v = v_factor * self.max_v
            strip.addPixelHSV(i, 0, 0.0, v)

class Tunnel(object):
    def __init__(self):
        self.front = 350
        self.back = (self.front + 180) % 360
        self.bandangle = 0
        self.bandwidth = 15

    def step(self):
        self.bandangle += 4
        self.bandangle %= 180

        self.front += 1
        self.front %= 360

    def show(self):
        for i in xrange(NUMPIXELS):
            d = angdist(PixelAngle.angle(i), self.front)
            if abs(d - self.bandangle) < self.bandwidth/2.:
                strip.addPixelHSV(i, self.bandangle/90., 1, 0.2)

class Falls(object):
    def __init__(self):
        self.angle = 360 * random.random()
        self.bandwidth = 15
        self.phase = 0
        self.hue = random.random()

    def step(self):
        self.phase += 0.1

    def show(self):
        for i in xrange(NUMPIXELS):
            d = angdist(PixelAngle.angle(i), self.angle)
            if abs(d) < self.bandwidth/2.:
                r = 1 - (i / float(NUMPIXELS))
                b = 0.5 + 0.5 * sin(r * 2 * pi + self.phase) * cos(d / self.bandwidth * 2 * pi)
                strip.addPixelHSV(i, self.hue, 0.5, b)

class Predicate(object):
    def __init__(self, predicate):
        self.f = predicate

    def step(self):
        pass

    def show(self):
        for i in xrange(NUMPIXELS):
            if self.f(i):
                strip.addPixelHSV(i, 0, 0, 0.04)

class InteractiveWalk(object):
    def __init__(self):
        self.pos = 124
        self.radius = 3

    def step(self):
        if gamekeys["left"]:
            self.pos -= 1
        if gamekeys["right"]:
            self.pos += 1
        self.pos = bound(self.pos)

    def show(self):
        for i in xrange(self.pos - self.radius, self.pos + self.radius):
            i = bound(i)
            strip.addPixelHSV(i, 0.3, 0.4, 0.2)

sprites = []

def empty_scene(sprites):
    pass

def multi_scene(sprites):
    N_SNAKES = 15
    sprites.extend(Snake(head=i*(NUMPIXELS / float(N_SNAKES)), speed=(1+(0.3*i))/4*random.choice([1, -1])) for i in xrange(N_SNAKES))
    sprites.append(EveryNth(factor=0.1, v=0.3))
    sprites.append(SparkleFade(interval=0.08))

def snakes_scene(sprites):
    N_SNAKES = 15
    sprites.extend(Snake(head=i*(NUMPIXELS / float(N_SNAKES)), speed=(1+(0.3*i))/4*random.choice([1, -1])) for i in xrange(N_SNAKES))

def nth_scene(sprites):
    sprites.append(EveryNth(factor=0.1))
    sprites.append(EveryNth(factor=0.101))

def sparkle_scene(sprites):
    sprites.append(Sparkle())
    sprites.append(SparkleFade())

def tunnel_scene(sprites):
    sprites.append(Tunnel())

def falls_scene(sprites):
    sprites.extend(Falls() for _ in xrange(10))

def game_scene(sprites):
    sprites.append(InteractiveWalk())

EmptyMode   = {empty_scene}
AttractMode = {multi_scene, snakes_scene, nth_scene, sparkle_scene, tunnel_scene}
GameMode    = {game_scene}

Modes = {
    'empty'  : EmptyMode,
    'attract': AttractMode,
    'game'   : GameMode,
}

CurrentMode = Modes['attract']
CurrentScene = None
FrameCount = 0

def select_another_scene():
    global sprites
    global CurrentScene
    # choose a different scene than the current one
    otherScenes = CurrentMode - {CurrentScene}
    # if the mode has only one scene, don't change it
    if not otherScenes:
        return
    scene = random.choice(list(otherScenes))
    print 'selecting', scene.__name__
    CurrentScene = scene
    sprites = []
    scene(sprites)

    global FrameCount
    FrameCount = 400 + random.randrange(400)

def select_mode(sceneSet, switchMessage=None):
    global CurrentMode, CurrentScene
    if CurrentMode == sceneSet: return False
    print switchMessage
    CurrentMode = sceneSet
    CurrentScene = None
    select_another_scene()
    return True

# Playing with angles.
# angle_offset = lambda: time.time() * 45 % 360
# angle_offset = lambda: sin(time.time()) * 55
# angle_width = lambda: 10
# sprites.append(Predicate(lambda x: angdist(PixelAngle.angle(x), angle_offset()) <= angle_width()))

def handle_action(message):
    global CurrentMode, Modes
    action = message["action"]
    if action == "next":
        print "Advancing to next scene."
        select_another_scene()
    elif action == "toggle":
        if not select_mode(EmptyMode, "toggle: off"):
            select_mode(AttractMode, "toggle: on")
        select_another_scene()
    elif Modes.get(action):
        select_mode(Modes[action])
    else:
        print "unknown message:", action

def handle_message():
    message = get_message()
    if not message: return
    print message
    messageType = message["type"]
    if messageType == "action":
        handle_action(message)
    elif messageType == "gamekey":
        select_mode(GameMode, "game mode on")
        key, state = message.get("key"), message.get("state")
        if key in gamekeys:
            gamekeys[key] = bool(state)
            print gamekeys
    else:
        print "unknown message type:", messageType

import sys
if len(sys.argv) > 2 and sys.argv[1] == '--scene':
    scene = eval(sys.argv[2] + '_scene')
    if scene:
        select_mode({scene})

print "Starting."
try:
    last_frame_t = time.time()
    ideal_frame_delta_t = 1.0 / 60
    while True:
        frame_t = time.time()
        delta_t = frame_t - last_frame_t
        if delta_t < ideal_frame_delta_t:
            time.sleep(ideal_frame_delta_t - delta_t)
        # else:
        #     print "Frame lagging. Time to optimize."
        last_frame_t = time.time()

        handle_message()

        FrameCount -= 1
        if FrameCount <= 0:
            select_another_scene()
        strip.clear()

        for sprite in sprites:
            sprite.show()
            sprite.step()

        strip.show()

finally:
    strip.cleanup()
