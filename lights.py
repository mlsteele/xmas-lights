#!/usr/bin/python

import argparse
import collections
import json
import logging
import os
import random
import time
import types
import numpy as np
from messages import get_message
from publish_message import publish
from led_geometry import PixelStrip
import sprites
from sprites import Scene, EveryNth, Snake, Sparkle, SparkleFade

logger = logging.getLogger('lights')
strip = None  # initialized in `main`


def capitalize_first_letter(string):
    return string[0].capitalize() + string[1:]


def lower_first_letter(string):
    return string[0].lower() + string[1:]

# MultiScenes
#


def make_scene(sceneOrString):
    """Given a Scene instance, class, or class name, return an instance."""
    obj = sceneOrString
    if isinstance(sceneOrString, str):
        obj = scenes.get(sceneOrString, None)
        obj = obj or getattr(sprites, capitalize_first_letter(sceneOrString), None)
    if isinstance(obj, type):
        obj = obj(strip)
    if not isinstance(obj, Scene):
        raise Exception('Not a scene name: %s' % sceneOrString)
    return obj


def get_scene_name(scene):
    return getattr(scene, 'name') or scene.__class__.__name__


class MultiScene(Scene):
    def __init__(self, children=(), name=None):
        if not isinstance(children, (types.GeneratorType, collections.Sequence)):
            children = [children]
        self.children = [make_scene(child) for child in children]
        self.name = name or self.children[0].__class__.__name__ if self.children else 'empty'

    def step(self, strip, t):
        for child in self.children:
            child.step(strip, t)

    def render(self, strip, t):
        for child in self.children:
            child.render(strip, t)


scenes = {}


def define_scene(name, children):
    scenes[name] = MultiScene(children, name)


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

    define_scene('hoops', (sprites.Hoop for _ in range(3)))

    define_scene('drops', (sprites.Droplet for _ in range(10)))

    define_scene('game', sprites.InteractiveWalk)

    n = 15
    print 'speeds', [60 * (1 + (0.3 * i)) / 4 * random.choice([1, -1]) for i in range(n)]
    children = [Snake(strip, offset=i * len(strip) / float(n), speed=60 * (1 + (0.3 * i)) / 4 * random.choice([1, -1])) for i in range(n)]
    print [s.speed for s in children]
    define_scene('snakes', children)

    n = 30
    children = [sprites.RedOrGreenSnake(strip, offset=i * len(strip) / float(n)) for i in range(n)]
    define_scene('redGreen', children)

    n = 15
    children = [Snake(strip, offset=i * len(strip) / float(n), speed=60 * (1 + (0.3 * i)) / 4 * random.choice([1, -1])) for i in range(n)]
    children.append(EveryNth(strip, factor=0.1, v=0.3))
    children.append(SparkleFade(strip))
    define_scene('multi', children)


# Modes
#


# A mode wraps a scene or scenes
class Mode(Scene):
    pass


# Attract mode is a scene that iterates through child scenes.
class AttractMode(Mode):
    def __init__(self, children=frozenset()):
        self.children = frozenset(make_scene(child) for child in children)
        if len(self.children) == 1:
            self.child = list(self.children)[0]
        self.current_child = None
        self.next_child = None
        self.remaining_frames = 0

    def next_scene(self):
        # choose a different child than the current one
        others = self.children - {self.current_child}
        # if the mode has only one scene, don't change it
        if not others:
            return

        child = random.choice(list(others))
        print 'selecting mode', get_scene_name(child)
        self.next_child = child
        self.fade_start = None

        self.remaining_frames = 400 + random.randrange(400)

    def step(self, strip, t):
        self.fade = 0
        if self.next_child:
            self.fade_start = self.fade_start or t
            self.fade = (t - self.fade_start) * 3
            if self.fade >= 1:
                self.current_child = self.next_child
                self.next_child = None

        self.remaining_frames -= 1
        if self.remaining_frames <= 0:
            self.next_scene()
        if self.current_child:
            self.current_child.step(strip, t)
        if self.next_child:
            self.next_child.step(strip, t)

    def render(self, strip, t):
        if self.current_child:
            self.current_child.render(strip, t)
        if self.next_child:
            leds = np.copy(strip.driver.leds)
            strip.clear()
            self.next_child.render(strip, t)
            strip.driver.leds = (1 - self.fade) * leds + self.fade * strip.driver.leds


class SlaveMode(Mode):
    def __init__(self):
        self.pixels = None

    def render(self, strip, t):
        if not self.pixels:
            return
        strip.clear()
        strip.leds = self.pixels
        self.pixels = None


current_mode = None


def make_modes():
    global attract_mode, slave_mode

    attract_mode = AttractMode(['multi', 'snakes', 'nth', 'sparkle', 'tunnel', 'hoops', 'drops', 'sweep', 'slices', 'redGreen'])
    slave_mode = SlaveMode()


# Select mode, and print message if the mode has changed.
def select_mode(mode):
    global current_mode
    if current_mode == mode:
        return False
    log.info('mode=%s', mode.name)
    current_mode = mode
    # FIXME
    if hasattr(current_mode, 'next_scene'):
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
        # FIXME
        if hasattr(current_mode, 'next_scene'):
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
        select_mode(slave_mode)
        current_mode.pixels = json.loads(str(message['leds']))
    elif mtype == 'gamekey':
        frame_modifiers -= set(['stop', 'off'])
        select_mode(game_mode)
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
    current_mode = attract_mode

    if args.show == 'scenes':
        names = scenes.keys() + list(cls.__name__ for cls in Scene.get_subclasses() if cls not in (Mode,))
        names = set(lower_first_letter(name) for name in names)
        print 'scenes:', ', '.join(sorted(list(names)))
        return

    if args.scene:
        scene = make_scene(args.scene)
        select_mode(scene)

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
        if current_mode != slave_mode and 'sync' in frame_modifiers:
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
