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


def make_scene(scene_or_string):
    """Given a Scene instance, class, or class name, return an instance."""
    obj = scene_or_string
    if isinstance(scene_or_string, str):
        obj = scenes.get(scene_or_string, None)
        obj = obj or getattr(sprites, capitalize_first_letter(scene_or_string), None)
    if isinstance(obj, type):
        obj = obj(strip)
    if not isinstance(obj, Scene):
        raise Exception('Not a scene name: %s' % scene_or_string)
    return obj


def get_scene_name(scene):
    return getattr(scene, 'name', None) or scene.__class__.__name__


class MultiScene(Scene):
    def __init__(self, children=(), name=None):
        if not isinstance(children, (types.GeneratorType, collections.Sequence)):
            children = [children]
        self.children = [make_scene(child) for child in children]
        self.name = name or self.children[0].__class__.__name__ if self.children else 'empty'

    def __repr__(self):
        return "<%s %s>" % (self.__class__.__name__, self.name)

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
    children = [Snake(strip, offset=i * len(strip) / float(n), speed=60 * (1 + (0.3 * i)) / 4 * random.choice([1, -1])) for i in range(n)]
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
        self.cross_fade_start = None
        self.next_scene_start = None

    def next_scene(self):
        # choose a different child than the current one
        others = self.children - {self.current_child}

        # if the mode has only one scene, don't change it
        if not others:
            return

        child = random.choice(list(others))
        print 'selecting scene', get_scene_name(child)
        self.next_child = child
        self.cross_fade_start = None
        self.next_scene_start = None

    def step(self, strip, t):
        if self.next_scene_start is None:
            self.next_scene_start = t + random.randrange(30, 90)

        if t > self.next_scene_start:
            self.next_scene()

        if self.next_child:
            self.cross_fade_start = self.cross_fade_start or t
            self.cross_fade = (t - self.cross_fade_start) * 3
            if self.cross_fade >= 1:
                self.current_child = self.next_child
                self.next_child = None

        if self.current_child:
            self.current_child.step(strip, t)

        if self.next_child:
            self.next_child.step(strip, t)

    def render(self, strip, t):

        if self.current_child:
            self.current_child.render(strip, t)

        if self.next_child:
            pixels_0 = np.copy(strip.driver.leds)
            strip.clear()
            self.next_child.render(strip, t)
            pixels_1 = strip.driver.leds
            strip.driver.leds[:] = (1 - self.cross_fade) * pixels_0 + self.cross_fade * pixels_1


class SlaveMode(Mode):
    def __init__(self):
        self.pixels = None

    def render(self, strip, t):
        if not self.pixels:
            return
        strip.clear()
        strip.leds = self.pixels
        self.pixels = None


def make_modes():
    global attract_mode, slave_mode

    attract_mode = AttractMode([
        'multi', 'snakes', 'nth', 'sparkle', 'tunnel', 'hoops', 'drops', 'sweep', 'slices', 'redGreen'])
    slave_mode = SlaveMode()


# Modifiers
#


class SceneModifier(object):
    def __init__(self, strip):
        pass

    def step(self, strip, t):
        pass

    def post_render(self, strip, t):
        pass

    def transform_time(self, t):
        return t


class InvertModifier(SceneModifier):
    def post_render(self, strip, t):
        pixels = strip.driver.leds
        pixels[:, :] = (1 - np.clip(pixels[i], 0, 1)) / 2


class ReverseModifier(SceneModifier):
    def transform_time(self, t):
        return -t


class StopModifier(SceneModifier):
    def step(self, strip, t):
        if not hasattr(self, 'time'):
            self.time = t

    def transform_time(self, t):
        if hasattr(self, 'time'):
            return self.time
        return t


class SpinModifier(SceneModifier):
    def __init__(self, child):
        self.spin_count = 0

    def step(self, strip, t):
        self.spin_count += 4 * 3
        if self.spin_count >= 450:
            scene_manager.remove_scene_modifier(self)

    def post_render(self, strip, t):
        n = self.spin_count
        pixels = strip.driver.leds
        pixels[:] = np.r_[pixels[n:], pixels[:n]]


class OffTransitionModifier(SceneModifier):
    def __init__(self, child):
        self.mode = 'dimming'
        self.child = child
        self.transition_duration = 1.
        print 'create off'

    def step(self, strip, t):
        if not hasattr(self, 'transition_start'):
            self.transition_start = t
        dt = t - self.transition_start
        s = dt / self.transition_duration
        if self.mode == 'dimming':
            if s >= 1:
                self.mode = 'off'
        elif self.mode == 'brightening':
            s = 1 - s
            if s >= 1:
                scene_manager.remove_scene_modifier(self)
        self.s = min(1, s)

    def post_render(self, strip, t):
        pixels = strip.driver.leds
        pixels *= self.s
        if self.mode in ('dimming', 'brightening'):
            # radius = strip.radius
            radius = strip.ring_radius[strip.pixel_ring]
            values = np.interp(1 - radius + 3 * self.s, [0, 1, 2, 3], [0, 0, 1, 0])
            alpha = np.interp(3 * self.s, [0, 1, 2, 3], [1, 0, 0, 0])
            pixels *= alpha
            pixels[:, :] += values[:, np.newaxis]
        else:
            pixels *= 0


class SceneManager(Scene):
    def __init__(self):
        self.scene_modifiers = []
        self.scene = None

    def add_scene_modifier(self, modifier_or_class):
        modifier_class = modifier_or_class
        if isinstance(modifier_or_class, SceneModifier):
            modifier_class = modifier_or_class.__class__
        if not self.find_scene_modifier(modifier_class):
            self.scene_modifiers.append(modifier_class(strip))

    def remove_scene_modifier(self, modifier_class):
        mod = self.find_scene_modifier(modifier_class)
        if mod:
            self.scene_modifiers.remove(mod)

    def toggle_scene_modifier(self, modifier_class):
        if self.find_scene_modifier(modifier_class):
            self.remove_scene_modifier(modifier_class)
        else:
            self.add_scene_modifier(modifier_class)

    def find_scene_modifier(self, modifier_or_class):
        modifier_class = modifier_or_class
        if isinstance(modifier_or_class, SceneModifier):
            modifier_class = modifier_or_class.__class__
        return next((mod for mod in self.scene_modifiers if isinstance(mod, modifier_class)), None)

    def call_method(self, method_name):
        if hasattr(self.scene, method_name):
            getattr(self.scene, method_name)()

    # Select mode, and print message if the mode has changed.
    def select_mode(self, scene):
        if self.scene == scene:
            return False
        logger.info('scene=%s', get_scene_name(scene))
        self.scene = scene
        self.current_mode = scene
        self.call_method('next_scene')

    def compute_time(self, t):
        for mod in self.scene_modifiers:
            t = mod.transform_time(t)
        return t

    def step(self, strip, t):
        for mod in self.scene_modifiers:
            t = mod.transform_time(t)
            mod.step(strip, t)
        if self.scene:
            self.scene.step(strip, t)

    def render(self, strip, t):
        if self.scene:
            self.scene.render(strip, self.compute_time(t))
        for mod in self.scene_modifiers:
            t = mod.transform_time(t)
            mod.post_render(strip, t)

scene_manager = SceneManager()


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
    global spin_count

    action = message['action']
    print 'action', action
    if action == 'next':
        scene_manager.remove_scene_modifier(OffTransitionModifier)
        scene_manager.remove_scene_modifier(StopModifier)
        scene_manager.call_method('next_scene')
    elif action == 'toggle':
        scene_manager.toggle_scene_modifier(OffTransitionModifier)
    elif action in ['off']:
        scene_manager.add_scene_modifier(OffTransitionModifier)
    elif action in ['stop']:
        scene_manager.toggle_scene_modifier(StopModifier)
    elif action in ['start', 'resume', 'on']:
        scene_manager.remove_scene_modifier(OffTransitionModifier)
        scene_manager.remove_scene_modifier(StopModifier)
    elif action == 'reverse':
        scene_manager.toggle_scene_modifier(ReverseModifier)
    elif action == 'spin':
        scene_manager.toggle_scene_modifier(SpinModifier)
    elif action == 'faster':
        change_speed_by(1.5)
    elif action == 'slower':
        change_speed_by(1 / 1.5)
    else:
        print 'unknown message:', action


def handle_message():
    message = get_message()
    if not message:
        return False

    mtype = message['type']
    if mtype == 'action':
        handle_action(message)
    elif mtype == 'ping':
        print 'pong'
    elif mtype == 'pixels':
        scene_manager.select_mode(slave_mode)
        scene_manager.current_mode.pixels = json.loads(str(message['leds']))
    elif mtype == 'gamekey':
        scene_manager.remove_scene_modifier(OffTransitionModifier)
        scene_manager.remove_scene_modifier(StopModifier)
        scene_manager.select_mode(game_mode)
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
    global speed, strip

    # must precede PixelStrip constructor
    if args.pygame:
        os.environ['SPIDEV_PYGAME'] = '1'

    # strip must be initialized before scenes.
    # scenes must be intiialized before modes, and before '--scene' and '--scenes' handling
    strip = PixelStrip()
    make_scenes()
    make_modes()
    scene_manager.select_mode(attract_mode)

    if args.show == 'scenes':
        names = scenes.keys() + list(cls.__name__ for cls in Scene.get_subclasses() if cls not in (Mode,))
        names = set(lower_first_letter(name) for name in names)
        print 'scenes:', ', '.join(sorted(list(names)))
        return

    if args.scene:
        scene = make_scene(args.scene)
        scene_manager.select_mode(scene)

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
    strip.clear()
    scene_manager.step(strip, synthetic_time)
    scene_manager.render(strip, synthetic_time)
    dtime = IDEAL_FRAME_DELTA_T * speed
    synthetic_time += dtime

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
        if scene_manager.current_mode != slave_mode and 'sync' in frame_modifiers:
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
