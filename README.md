# Xmas Tree Lights

Christmas tree lights for the Minsky/Steele house.

## Installation

### Mac

    brew install python entr

### Raspberry Pi

Enable the raspberry pi's SPI in raspi-config. This will require a reboot.
```shell
sudo raspi-config
```

Install the python spidev library on the pi.

```shell
curl https://github.com/Gadgetoid/py-spidev/archive/master.zip >> py-spidev.zip
unzip py-spidev.zip
cd py-spidev-master
sudo python setup.py install
```

Create a directory to hold the program. `./download` (below) will populate this.

```shell
mkdir xmas-lights
```

## Usage

Clone the repository on your computer and on the raspberry pi:

```shell
git clone https://github.com/mlsteele/xmas-lights
cd xmas-lights
```

Run the lights in a screen on the pi, restarting when a change is detected:

```shell
ssh pi@xmas-pi
screen -dR lights
./xmas-lights/watch-upload.sh
```

Upload the file you're working on when changes occur:

```shell
./download
```

## Credits

This includes Martin Erzberger's [APA-102c LED control lib](https://github.com/tinue/APA102_Pi) library.
