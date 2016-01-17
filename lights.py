#!/usr/bin/python

import argparse
import collections
import json
import logging
import os
import random
import sys
import time
import types
from messages import get_message
from publish_message import publish
from led_geometry import PixelStrip
import sprites
from sprites import Sprite, EveryNth, Snake, Sparkle, SparkleFade

strip = None  # initialized in `main`

# Scenes
#


# A Scene is just a Sprite that composes a set of underlying sprites
class Scene(Sprite):
    def __init__(self, children=(), name=None):
        def make_sprite(sprite):
            if isinstance(sprite, type):
                sprite = sprite(strip)
            return sprite
        if not isinstance(children, (types.GeneratorType, collections.Sequence)):
            children = [children]
        self.children = [make_sprite(child) for child in children]
        self.name = name or self.children[0].__class__.__name__ if self.children else 'empty'

    def step(self, strip, t):
        for child in self.children:
            child.step(strip, t)

    def render(self, strip, t):
        for child in self.children:
            child.render(strip, t)


scenes = {}


def define_scene(name, children):
    scenes[name] = Scene(children, name)


def make_scenes():
    define_scene('empty', [])

    define_scene('nth', [EveryNth(strip, factor=0.1), EveryNth(strip, factor=0.101)])

    define_scene('sparkle', [Sparkle, SparkleFade])

    # define_scene('gradient', Snake(speed=1, length=len(strip), saturation=0, brightness=1)

    define_scene('gradient', [
        sprites.Hoop(strip, offset=0, speed=0.1, hue=0),
        sprites.Hoop(strip, offset=1 / 4.0, speed=0.1, hue=1 / 3.0),
        sprites.Hoop(strip, offset=2 / 4.0, speed=0.1, hue=2 / 3.0),
        sprites.Hoop(strip, offset=3 / 4.0, speed=0.1, saturation=0),
    ])

    define_scene('tunnel', sprites.Tunnel)

    define_scene('hoops', (sprites.Hoop for _ in range(3)))

    define_scene('drops', (sprites.Droplet for _ in range(10)))

    define_scene('game', sprites.InteractiveWalk)

    define_scene('sweep', sprites.Sweep)

    n = 15
    children = [Snake(strip, offset=i * len(strip) / float(n), speed=(1 + (0.3 * i)) / 4 * random.choice([1, -1])) for i in range(n)]
    define_scene('snakes', children)

    n = 15
    children = [Snake(strip, offset=i * len(strip) / float(n), speed=(1 + (0.3 * i)) / 4 * random.choice([1, -1])) for i in range(n)]
    children.append(EveryNth(strip, factor=0.1, v=0.3))
    children.append(SparkleFade(strip))
    define_scene('multi', children)


# Modes
#


# A mode is a sprite that iterates through child sprites.
class Mode(Sprite):
    def __init__(self, children=frozenset()):
        self.children = frozenset(scenes[child] if isinstance(child, str) else child for child in children)
        if len(self.children) == 1:
            self.child = list(self.children)[0]
        self.current_child = None
        self.remaining_frames = 0

    def next_scene(self):
        # choose a different child than the current one
        others = self.children - {self.current_child}
        # if the mode has only one scene, don't change it
        if not others:
            return

        child = random.choice(list(others))
        print 'selecting mode', child.name
        self.current_child = child

        self.remaining_frames = 400 + random.randrange(400)

    def step(self, strip, t):
        self.remaining_frames -= 1
        if self.remaining_frames <= 0:
            self.next_scene()
        if self.current_child:
            self.current_child.step(strip, t)

    def render(self, strip, t):
        if self.current_child:
            self.current_child.render(strip, t)


class SlaveMode(Sprite):
    def __init__(self):
        self.pixels = None

    def next_scene(self):
        pass

    def render(self, strip, t):
        if not self.pixels:
            return
        strip.clear()
        strip.leds = self.pixels
        self.pixels = None

modes = {}
current_mode = None


def make_modes():
    modes['attract'] = Mode(['multi', 'snakes', 'nth', 'sparkle', 'tunnel', 'hoops', 'drops', 'sweep'])
    modes['game'] = Mode(['game'])
    modes['slave'] = SlaveMode()


# Select mode, and print message if the mode has changed.
def select_mode(mode, switch_message=None):
    global current_mode
    if current_mode == mode:
        return False
    if switch_message:
        print switch_message
    current_mode = mode
    current_mode.next_scene()
    return True


def change_speed_by(factor):
    global speed
    speed *= factor
    if abs(speed - 1.0) < 0.01:
        speed = 1.0
    print 'set speed to', speed

# Playing with angles.
# angle_offset = lambda: time.time() * 45 % 360
# angle_offset = lambda: sin(time.time()) * 55
# angle_width = lambda: 10
# sprites.append(Predicate(lambda x: angdist(PixelAngle.angle(x), angle_offset()) <= angle_width()))


def handle_action(message):
    global frame_modifiers, spin_count
    action = message['action']
    print 'action', action
    if action == 'next':
        frame_modifiers -= set(['stop', 'off'])
        current_mode.next_scene()
    elif action == 'toggle':
        frame_modifiers ^= set(['off'])
    elif action in ['off', 'stop']:
        frame_modifiers.add(action)
    elif action in ['start', 'resume', 'on']:
        frame_modifiers -= set(['stop', 'off'])
    elif action == 'reverse':
        frame_modifiers ^= set(['reverse'])
    elif action == 'spin':
        frame_modifiers.add('spin')
        spin_count = 0
    elif action == 'faster':
        change_speed_by(1.5)
    elif action == 'slower':
        change_speed_by(1 / 1.5)
    else:
        print 'unknown message:', action


def handle_message():
    global frame_modifiers

    message = get_message()
    if not message:
        return False

    mtype = message['type']
    if mtype == 'action':
        handle_action(message)
    elif mtype == 'ping':
        print 'pong'
    elif mtype == 'pixels':
        select_mode(modes['slave'], 'slave mode')
        current_mode.pixels = json.loads(str(message['leds']))
    elif mtype == 'gamekey':
        frame_modifiers -= set(['stop', 'off'])
        select_mode(game_mode, 'game mode on')
        key, state = message.get('key'), message.get('state')
        gamekeys = {
            'left': False,
            'right': False,
            'fire': False,
        }
        if key in gamekeys:
            gamekeys[key] = bool(state)
            print 'keys', gamekeys
            game_mode.child.handle_game_keys(gamekeys)
    else:
        print 'unknown message type:', mtype
    return True

parser = argparse.ArgumentParser(description='Christmas-Tree Lights.')
parser.add_argument('--debug-messages', dest='debug_messages', action='store_true')
parser.add_argument('--pygame', dest='pygame', action='store_true')
parser.add_argument('--master', dest='master', action='store_true')
parser.add_argument('--no-sync', dest='no_sync', action='store_true')
parser.add_argument('--scene', dest='scene', type=str)
parser.add_argument('--scenes', dest='show', action='store_const', const='scenes')
parser.add_argument('--sprites', dest='show', action='store_const', const='sprites')
parser.add_argument('--speed', dest='speed', type=float)
parser.add_argument('--sprite', dest='sprite', type=str)
parser.add_argument('--warn', dest='warn', action='store_true', help='warn on slow frame rate')
parser.add_argument('--print-frame-rate', dest='print_frame_rate', action='store_true', help='warn on slow frame rate')


def main(args):
    global current_mode, speed, strip

    # must precede PixelStrip constructor
    if args.pygame:
        os.environ['SPIDEV_PYGAME'] = '1'

    # strip must be initialized before scenes.
    # scenes must be intiialized before modes, and before '--scene' and '--scenes' handling
    strip = PixelStrip()
    make_scenes()
    make_modes()
    current_mode = modes['attract']

    if args.show == 'scenes':
        print 'scenes:', ', '.join(sorted(scenes.keys()))
        return

    if args.show == 'sprites':
        names = (cls.__name__ for cls in Sprite.get_subclasses() if cls not in (Scene, Mode, SlaveMode))
        print 'sprites:', ', '.join(sorted(names))
        return

    if args.scene:
        scene = scenes.get(args.scene)
        if not isinstance(scene, Scene):
            print >> sys.stderr, 'Unknown scene:', args.scene
            exit(1)
        select_mode(Mode({scene}))

    if args.sprite:
        sprite = getattr(sprites, args.sprite[0].capitalize() + args.sprite[1:], None)
        if not isinstance(sprite, (type, types.ClassType)) or not issubclass(sprite, Sprite):
            print >> sys.stderr, 'Unknown sprite:', args.sprite
            exit(1)
        scene = Scene(sprite)
        select_mode(Mode({scene}))

    if args.speed:
        speed = args.speed

    if args.no_sync:
        frame_modifiers.discard('sync')

    if args.debug_messages:
        logging.getLogger('messages').setLevel(logging.INFO)

    print 'Starting.'
    while True:
        if not args.master:
            handle_message()

        do_frame(args)

        if args.master:
            publish('pixels', leds=json.dumps(strip.leds))

last_frame_printed_t = time.time()
frame_deltas = []  # FIFO of the last 60 frame latencies

frame_modifiers = set(['sync'])
spin_count = 0

IDEAL_FRAME_DELTA_T = 1.0 / 60
speed = 1.0
last_frame_t = time.time()
synthetic_time = 0


def do_frame(options):
    global last_frame_t, last_frame_printed_t, spin_count, synthetic_time

    # Render the current frame
    if 'stop' not in frame_modifiers:
        strip.clear()
    if 'stop' not in frame_modifiers and 'off' not in frame_modifiers:
        current_mode.step(strip, synthetic_time)
        current_mode.render(strip, synthetic_time)
        dtime = IDEAL_FRAME_DELTA_T * speed
        if 'reverse' in frame_modifiers:
            dtime *= -1
        synthetic_time += dtime

    # Apply modifiers
    if 'spin' in frame_modifiers:
        strip.leds = strip.leds[spin_count:] + strip.leds[:spin_count]
        spin_count += 3 * 4
        if spin_count >= 450:
            frame_modifiers.discard('spin')
    if 'invert' in frame_modifiers:
        for i in range(len(strip.leds)):
            if i % 4:
                # strip.leds[i] = 16 - strip.leds[i] * 16 / 256
                strip.leds[i] = 255 - strip.leds[i]
            else:
                strip.leds[i] = 0xe0 | 1
    # for i in range(len(strip.leds)):
    #     if i % 4 is 0:
    #         strip.leds[i] = 0xe7

    frame_t = time.time()
    delta_t = frame_t - last_frame_t

    # Reprt the running average frame rate
    frame_deltas.append(delta_t)
    if len(frame_deltas) > 60:
        frame_deltas.pop(0)
    if options.print_frame_rate:
        if frame_t - (last_frame_printed_t or frame_t) > 1:
            print 'fps: %2.1f' % (1 / (sum(frame_deltas) / len(frame_deltas)))
            last_frame_printed_t = frame_t

    # Slow down to target frame rate
    if delta_t < IDEAL_FRAME_DELTA_T:
        if current_mode != modes['slave'] and 'sync' in frame_modifiers:
            time.sleep(IDEAL_FRAME_DELTA_T - delta_t)
    elif options.warn:
        print 'Frame lagging. Time to optimize.'

    last_frame_t = time.time()
    strip.show()

try:
    args = parser.parse_args()
    main(args)
except KeyboardInterrupt:
    if strip:
        # Fade to black.
        # Improvement: trap this signal, and set a global animation that fades the brightness and then quits.
        for _ in xrange(15):
            strip.driver.leds[:, 1:] *= .8
            strip.show()
            time.sleep(1. / 60)
        strip.clear()
        strip.show()
finally:
    if strip:
        strip.close()
