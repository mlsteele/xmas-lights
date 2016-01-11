#!/usr/bin/python

import collections
import time
import types
import random
import json
import apa102
from messages import get_message
from publish_message import publish
from led_geometry import PixelStrip
from sprites import *

strip = apa102.APA102(PixelStrip.count)

## Scenes
##

FrameCount = 0
CurrentScene = None

def make_sprite_scene(*sprites):
    def fn():
        return sprites
    fn.__name__ = sprites[0].__name__
    return fn

def select_another_scene():
    global Sprites
    global CurrentScene
    # choose a different scene than the current one
    otherScenes = CurrentMode - {CurrentScene}
    # if the mode has only one scene, don't change it
    if not otherScenes:
        return

    scene = random.choice(list(otherScenes))
    print 'selecting', scene.__name__
    CurrentScene = scene

    def makeSprite(sprite):
        if isinstance(sprite, type):
            sprite = sprite()
        return sprite
    sprites = scene()
    if not isinstance(sprites, (types.GeneratorType, collections.Sequence)):
        sprites = [sprites]
    Sprites = map(makeSprite, list(sprites))

    global FrameCount
    FrameCount = 400 + random.randrange(400)

def empty_scene():
    return []

def multi_scene():
    snakeCount = 15
    sprites = []
    sprites.extend(Snake(head=i*(PixelStrip.count / float(snakeCount)), speed=(1+(0.3*i))/4*random.choice([1, -1])) for i in range(snakeCount))
    sprites.append(EveryNth(factor=0.1, v=0.3))
    sprites.append(SparkleFade(interval=0.08))
    return sprites

def snakes_scene():
    snakeCount = 15
    return (Snake(head=i*(PixelStrip.count / float(snakeCount)), speed=(1+(0.3*i))/4*random.choice([1, -1])) for i in range(snakeCount))

def nth_scene():
    return [
        EveryNth(factor=0.1),
        EveryNth(factor=0.101)
    ]

def sparkle_scene():
    return [Sparkle, SparkleFade]

tunnel_scene = make_sprite_scene(Tunnel)

def drips_scene():
    return (Drips for _ in range(10))

game_scene = make_sprite_scene(InteractiveWalk)

## Modes
##

EmptyMode   = {empty_scene}
AttractMode = {multi_scene, snakes_scene, nth_scene, sparkle_scene, tunnel_scene}
GameMode    = {game_scene}

Modes = {
    'empty'  : EmptyMode,
    'attract': AttractMode,
    'game'   : GameMode,
}

CurrentMode = Modes['attract']

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

LEDState = None

def handle_action(message):
    global CurrentMode, Modes, FrameMode, SpinCount
    action = message["action"]
    if action == "next":
        print "Advancing to next scene."
        select_another_scene()
    elif action == "toggle":
        if not select_mode(EmptyMode, "toggle: off"):
            select_mode(AttractMode, "toggle: on")
        select_another_scene()
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
            CurrentScene.handle_game_keys(gamekeys)
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

args = parser.parse_args()

import sys
if args.scene:
    scene = None
    try:
        scene = eval(args.scene + '_scene')
    except NameError:
        print >> sys.stderr, "Unknown scene:", args.scene
        exit(1)
    select_mode({scene})

if args.sprite:
    sprite = None
    try:
        sprite = eval(args.sprite[0].capitalize() + args.sprite[1:])
    except NameError:
        print >> sys.stderr, "Unknown sprite:", args.sprite
        exit(1)
    scene = make_sprite_scene(sprite)
    select_mode({scene})

def do_slave_frame():
    global LEDState
    if not LEDState: return
    strip.clear()
    strip.leds = LEDState
    LEDState = None

def do_scenes_frame():
    global FrameCount

    FrameCount -= 1
    if FrameCount <= 0:
        select_another_scene()

    strip.clear()

    for sprite in Sprites:
        sprite.render(strip)
        sprite.step()

def do_stopped_frame():
    pass

FrameModeFunctions = {
    'slave'  : do_slave_frame,
    'scenes' : do_scenes_frame,
    'stopped': do_stopped_frame,
}

def do_frame():
    FrameModeFunctions[FrameMode]()

print "Starting."
frame_deltas = []
Modifiers = dict(spin=False, reverse=False)
SpinCount = 0
last_frame_printed_t = time.time()

try:
    last_frame_t = time.time()
    ideal_frame_delta_t = 1.0 / 60

    while True:
        if not args.master:
            handle_message()

        do_frame()

        frame_t = time.time()
        delta_t = frame_t - last_frame_t
        frame_deltas.append(delta_t)
        if len(frame_deltas) > 60:
            frame_deltas.pop(0)
        if args.print_frame_rate:
            if frame_t - (last_frame_printed_t or frame_t) > 1:
                print "fps: %2.1f" % (1 / (sum(frame_deltas) / len(frame_deltas)))
                last_frame_printed_t = frame_t
        if delta_t < ideal_frame_delta_t:
            if FrameMode != 'slave':
                time.sleep(ideal_frame_delta_t - delta_t)
        elif args.warn:
            print "Frame lagging. Time to optimize."
        last_frame_t = time.time()

        if Modifiers['spin']:
            strip.leds = strip.leds[SpinCount:] + strip.leds[:SpinCount]
            SpinCount += 3 * 4
            if SpinCount >= 450:
                Modifiers['spin'] = False
        if Modifiers['reverse']:
            strip.reverse()
        strip.show()

        if args.master:
            publish("pixels", leds=json.dumps(strip.leds))

finally:
    strip.cleanup()
