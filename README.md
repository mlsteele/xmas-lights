# Xmas Tree Lights
[![Deploy](https://www.herokucdn.com/deploy/button.png)](https://heroku.com/deploy)

Christmas tree lights for the Minsky/Steele house.

## Installation (Mac; for Mac-based development)

    brew install python entr

## Installation (Raspberry Pi)

Enable the raspberry pi's SPI in raspi-config. This will require a reboot.

```shell
sudo raspi-config
```

Install the python libraries:

```shell
sudo apt-get install -y python-pip
pip install -r requirements-pi.py
```

```shell
git clone https://github.com/mlsteele/xmas-lights
```

## Usage (Raspberry Pi)

```shell
cd xmas-lights
python lights.py
```

## Development

You can use your edit sources on another computer, and set it to reload the changes sources on the Pi
when they change.

Clone the repository on your computer, and install dependencies:

```shell
git clone https://github.com/mlsteele/xmas-lights
cd xmas-lights
pip install -r requirements.txt
```

Find your Pi's IP address, and add an entry in your ``.ssh/config` on your development workstation:

    Host xmas-pi
      HostName 192.168.0.36
      User pi

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

`apa102.py` is adapted from Martin Erzberger's [APA-102c LED control lib](https://github.com/tinue/APA102_Pi) library.
