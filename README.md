# Xmas Tree Lights

Christmas tree lights for the Minsky/Steele house.

## Installation (Mac; for Mac-based development)

    brew install python entr

## Installation (Raspberry Pi)

Enable the raspberry pi's SPI in raspi-config. This will require a reboot.

```shell
sudo raspi-config
```

Install the python spidev library:

```shell
curl https://github.com/Gadgetoid/py-spidev/archive/master.zip > py-spidev.zip
unzip py-spidev.zip
(cd py-spidev-master && sudo python setup.py install)
```

```shell
git clone https://github.com/mlsteele/xmas-lights
```

## Usage (Raspberry Pi)

```shell
cd xmas-lights
python lights.py
```

## Usage (Unix or Mac)

Clone the repository on your computer:

```shell
git clone https://github.com/mlsteele/xmas-lights
cd xmas-lights
```

Ssh into Pi and create a persistent connection with `screen` or `tmux`.
Run the lights, reloading the file when it changes.

```shell
ssh pi@xmas-pi
screen -dR lights
./xmas-lights/live-reload.sh
```

Leave this running in a terminal to download the files to the Pi when they change.
The `./live-reload.sh` script on the Pi will restart the program.

```shell
./live-download.sh
```

## Credits

This project includes the `apa102.py` file from Martin Erzberger's [APA-102c LED control lib](https://github.com/tinue/APA102_Pi) library.

That library and this code are available under Version 2 of the Gnu General Public License.
