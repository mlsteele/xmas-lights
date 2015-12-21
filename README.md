# Xmas Tree Lights

Christmas tree lights for the Minsky/Steele house.

Based of the lovely DotStar module for Python on a Raspberry Pi.
[Adafruit_DotStar_Pi](https://github.com/adafruit/Adafruit_DotStar_Pi)

## Usage

Clone the repository on your computer and on the raspberry pi:

```shell
    git clone https://github.com/mlsteele/xmas-lights
    cd xmas-lights
```

Run the lights in a screen on the pi, restarting when a change is detected.
Remember to run `make` to build the dotstar lib.
```shell
    ssh pi@xmas-pi
    screen -dR lights
    cd xmas-lights
    make
    LIGHTFILE=miles.py
    echo $LIGHTFILE | entr -r sh -c "sudo pkill -U root -f 'python $LIGHTFILE' ; sudo python $LIGHTFILE"
```

Upload the file you're working on when changes occur.

```shell
    LIGHTFILE=miles.py
    echo $LIGHTFILE | entr -r sh -c "scp $LIGHTFILE xmas-pi:xmas-lights/$LIGHTFILE"
```
