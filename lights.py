#!/usr/bin/python

import collections, json, random, sys, time, types
import apa102
from messages import get_message
from publish_message import publish
from led_geometry import PixelStrip
from sprites import *

strip = apa102.APA102(PixelStrip.count)

## Scenes
##

# A Scene is just a Sprite that composes a set of underlying sprites
class Scene(Sprite):
    def __init__(self, children=[]):
        def makeSprite(sprite):
            if isinstance(sprite, type):
                sprite = sprite()
            return sprite
        if not isinstance(children, (types.GeneratorType, collections.Sequence)):
            children = [children]
        self.children = map(makeSprite, list(children))
        self.name = self.children[0].__class__.__name__ if self.children else 'empty'

    def step(self):
        for child in self.children:
            child.step()

    def render(self, strip):
        for child in self.children:
            child.render(strip)

def make_sprite_scene(*sprites):
    def fn():
        scene = Scene(sprites)
        scene.name = sprites[0].__name__
        return scene
    return fn

def empty_scene():
    return Scene()

def multi_scene():
    snakeCount = 15
    sprites = list(Snake(head=i*(PixelStrip.count / float(snakeCount)), speed=(1+(0.3*i))/4*random.choice([1, -1])) for i in range(snakeCount))
    sprites.append(EveryNth(factor=0.1, v=0.3))
    sprites.append(SparkleFade(interval=0.08))
    return Scene(sprites)

def snakes_scene():
    snakeCount = 15
    return Scene(Snake(head=i*(PixelStrip.count / float(snakeCount)), speed=(1+(0.3*i))/4*random.choice([1, -1])) for i in range(snakeCount))

def nth_scene():
    return Scene([
        EveryNth(factor=0.1),
        EveryNth(factor=0.101)
    ])

def sparkle_scene():
    return Scene([Sparkle, SparkleFade])

tunnel_scene = make_sprite_scene(Tunnel)

def drips_scene():
    return Scene(Drips for _ in range(10))

game_scene = make_sprite_scene(InteractiveWalk)

## Modes
##

CurrentScene = None

# A mode is a sprite that iterates through child sprites.
class Mode(Sprite):
    def __init__(self, children={}):
        self.children = set(children)
        self.current_child = None
        self.remaining_frames = 0

    def next_scene(self):
        # choose a different child than the current one
        others = self.children - {self.current_child}
        # if the mode has only one scene, don't change it
        if not others:
            return

        child = random.choice(list(others))
        print 'selecting', child.name
        self.current_child = child

        self.remaining_frames = 400 + random.randrange(400)

    def step(self):
        self.remaining_frames -= 1
        if self.remaining_frames <= 0:
            self.next_scene()
        if self.current_child:
            self.current_child.step()

    def render(self, strip):
        if self.current_child:
            self.current_child.render(strip)

EmptyMode   = Mode()
AttractMode = Mode({multi_scene(), snakes_scene(), nth_scene(), sparkle_scene(), tunnel_scene()})
GameMode    = Mode({game_scene()})

Modes = {
    'empty'  : EmptyMode,
    'attract': AttractMode,
    'game'   : GameMode,
}

CurrentMode = AttractMode

# Select mode, and print message if the mode has changed.
def select_mode(mode, switchMessage=None):
    global CurrentMode
    if CurrentMode == mode:
        return False
    print switchMessage
    CurrentMode = mode
    CurrentMode.next_scene()
    return True

# Playing with angles.
# angle_offset = lambda: time.time() * 45 % 360
# angle_offset = lambda: sin(time.time()) * 55
# angle_width = lambda: 10
# sprites.append(Predicate(lambda x: angdist(PixelAngle.angle(x), angle_offset()) <= angle_width()))

LEDState = None

def handle_action(message):
    global CurrentMode, Modes, FrameMode, SpinCount
    action = message["action"]
    if action == "next":
        print "Advancing to the next scene."
        CurrentMode.next_scene()
    elif action == "toggle":
        if not select_mode(EmptyMode, "toggle: off"):
            select_mode(AttractMode, "toggle: on")
        CurrentMode.next_scene()
    elif action == "off":
        print 'off'
        FrameMode = 'stopped'
        strip.clear()
    elif action == "stop":
        print 'stop'
        FrameMode = 'stopped'
    elif action in ["start", "resume", "on"]:
        print 'start'
        FrameMode = 'scenes'
    elif action == "reverse":
        Modifiers['reverse'] = True
    elif action == "spin":
        Modifiers['spin'] = True
        SpinCount = 0
    elif Modes.get(action):
        select_mode(Modes[action])
    else:
        print "unknown message:", action

FrameMode = 'scenes'

def handle_message():
    global FrameMode
    message = get_message()
    if not message: return False

    messageType = message["type"]
    if messageType == "action":
        FrameMode = 'scenes'
        handle_action(message)
    elif messageType == "ping":
        print "pong"
    elif messageType == "pixels":
        # print 'switch to mode', FrameMode
        FrameMode = 'slave'
        global LEDState
        LEDState = json.loads(str(message["leds"]))
    elif messageType == "gamekey":
        FrameMode = 'default'
        select_mode(GameMode, "game mode on")
        key, state = message.get("key"), message.get("state")
        if key in gamekeys:
            gamekeys = {
                "left": False,
                "right": False,
                "fire": False,
            }
            gamekeys[key] = bool(state)
            print gamekeys
            GameMode.children[0].handle_game_keys(gamekeys)
    else:
        print "unknown message type:", messageType
    return True

import argparse
parser = argparse.ArgumentParser(description='Christmas-Tree Lights.')
parser.add_argument('--master', dest='master', action='store_true')
parser.add_argument('--scene', dest='scene', type=str)
parser.add_argument('--sprite', dest='sprite', type=str)
parser.add_argument('--warn', dest='warn', action='store_true', help='warn on slow frame rate')
parser.add_argument('--print-frame-rate', dest='print_frame_rate', action='store_true', help='warn on slow frame rate')

def main(args):
    if args.scene:
        try:
            scenefn = eval(args.scene + '_scene')
        except NameError:
            print >> sys.stderr, "Unknown scene:", args.scene
            exit(1)
        scene = scenefn()
        select_mode(Mode({scene}))

    if args.sprite:
        try:
            sprite = eval(args.sprite[0].capitalize() + args.sprite[1:])
        except NameError:
            print >> sys.stderr, "Unknown sprite:", args.sprite
            exit(1)
        scene = Scene(sprite)
        select_mode(Mode({scene}))

    while True:
        if not args.master:
            handle_message()

        do_frame(args)

        if args.master:
            publish("pixels", leds=json.dumps(strip.leds))

def do_slave_frame():
    global LEDState
    if not LEDState: return
    strip.clear()
    strip.leds = LEDState
    LEDState = None

def do_scenes_frame():
    strip.clear()
    CurrentMode.render(strip)
    CurrentMode.step()

def do_stopped_frame():
    pass

FrameModeFunctions = {
    'slave'  : do_slave_frame,
    'scenes' : do_scenes_frame,
    'stopped': do_stopped_frame,
}

print "Starting."
frame_deltas = [] # FIFO of the last 60 frame latencies
Modifiers = dict(spin=False, reverse=False)
SpinCount = 0

IDEAL_FRAME_DELTA_T = 1.0 / 60
last_frame_t = time.time()
last_frame_printed_t = time.time()

def do_frame(options):
    global last_frame_t, last_frame_printed_t, SpinCount

    frame_t = time.time()
    delta_t = frame_t - last_frame_t

    # Reprt the running average frame rate
    frame_deltas.append(delta_t)
    if len(frame_deltas) > 60:
        frame_deltas.pop(0)
    if options.print_frame_rate:
        if frame_t - (last_frame_printed_t or frame_t) > 1:
            print "fps: %2.1f" % (1 / (sum(frame_deltas) / len(frame_deltas)))
            last_frame_printed_t = frame_t

    # Render the current frame
    FrameModeFunctions[FrameMode]()

    # Apply modifiers
    if Modifiers['spin']:
        strip.leds = strip.leds[SpinCount:] + strip.leds[:SpinCount]
        SpinCount += 3 * 4
        if SpinCount >= 450:
            Modifiers['spin'] = False
    if Modifiers['reverse']:
        strip.reverse()

    # Slow down to target frame rate
    if delta_t < IDEAL_FRAME_DELTA_T:
        if FrameMode != 'slave':
            time.sleep(IDEAL_FRAME_DELTA_T - delta_t)
    elif options.warn:
        print "Frame lagging. Time to optimize."

    last_frame_t = time.time()
    strip.show()

try:
    args = parser.parse_args()
    main(args)
finally:
    strip.cleanup()
