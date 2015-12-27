# Xmas Tree Lights

Christmas tree lights for the Minsky/Steele house.

![](http://assets.osteele.com.s3.amazonaws.com/images/2015/xmas-lights/lights.gif)
![](http://assets.osteele.com.s3.amazonaws.com/images/2015/xmas-lights/sparkle.gif)
![](http://assets.osteele.com.s3.amazonaws.com/images/2015/xmas-lights/nth.gif)
![](http://assets.osteele.com.s3.amazonaws.com/images/2015/xmas-lights/other.gif)

A Python program that runs on a Raspberry Pi and animates the lights on an APA102 (Dotstar) LED strip.

This README is divided into three sections:

* Installing and running the program on the Raspberry Pi.
* Optional: Configuring the Pi and another workstation for streamlined development with automatic reloading.
* Optional: Configuring a WebServer for remote control of the lights via IFTTT, Slack, or Twilio.

## Raspberry Pi

### Installation

Enable the raspberry pi's SPI in raspi-config. This will require a reboot.

    sudo raspi-config

Clone the repo:

    git clone https://github.com/mlsteele/xmas-lights
    cd xmas-lights

Install the required dependencies:

    sudo apt-get install -y python-pip
    pip install -r pi-requirements.txt

### Running

To run the lights:

    python lights.py

To run the lights whenever the Pi boots, use `sudo nano /etc/rc.local` or another editor to add this line to
``/etc/rc.local`.

Note that this will swallow error messages. If things aren't working, debug it running it
from the terminal as above.

    sudo python lights.py > /dev/null 2>&1 &

(If you change the `/etc/rc.local` line to log to a file: beware of filling up your file system,
and be aware that continuously writing to an SD card increases the likelihood that it will be corrupted if
power to the Pi is cut while the Pi is running.)

## Live-Reload Development Flow

For development, you can set up the Pi to restart the application whenever its sources change.

Do this once:

    apt-get install entr

and run the lights thus:

    ./live-reload.sh

Now when you edit a `*.py` file, the program will reload.

## Live-Download Development Flow

If you prefer to edit on a separate development workstation, you can configure it to download files
to the Pi when they change on the development workstation. In conjunction with the Live-Reload flow, above,
this has the effect that when you save a file from the editor on your workstation, the application on the Pi
will shortly re-run with the changes.

### Installation (Development Station)

On the development station, download the repo:

    git clone https://github.com/mlsteele/xmas-lights
    cd xmas-lights

Run one of the following:

    apt-get install -y entr       # Linux
    brew install ssh-copy-id entr # Mac OS

[Find your Pi's IP address](https://www.raspberrypi.org/documentation/troubleshooting/hardware/networking/ip-address.md),
and add an entry in your ``.ssh/config` on your development workstation.
For example, if your Pi's IP address is `192.168.0.36`, add the following.

    Host xmas-pi
      HostName 192.168.0.36
      User pi

[Configure your Pi for passwordless login](https://www.raspberrypi.org/documentation/remote-access/ssh/passwordless.md):

    [ -f ~/.ssh/id_rsa.pub] || ssh-keygen -t rsa
    ssh-copy-id -i ~/.ssh/id_rsa.pub pi@xmas-pi

### Running

Run `./live-reload.sh` on the Pi. Use the first line below to simply run it:

    ssh pi@xmas-pi xmas-lights/live-reload.sh

Or, use this block to create a [screen](https://www.gnu.org/software/screen/) session that will remain running if you
lose the connection to the Pi, and that you can attach to again using the same command:

    ssh pi@xmas-pi -t screen -dR lights
    xmas-lights/live-reload.sh

Run this on the development station:

    ./live-download.sh

## Server

### Configuration

The server and the Pi communicate using RabbitMQ.
Provision a RabbitMQ host, and retrieve its URI.
The URI should look something like this: `amqp://user:pass@host:10000/vhost`.

Edit the RabbitMQ URI into the Raspberry Pi's `/etc/environment` file, via `sudo nano /etc/environment` or
another editor. Remember to replace the example URI below by your Rabbit's URI.

    RABBIT_URL=amqp://user:pass@host:10000/vhost

### Local Development

Run one of the following:
    apt-get install -y entr python-pip # Linux
    brew install entr python           # Mac OS

Inside the `xmas-lights` directory:

    pip install -r requirements.txt # once
    python webserver.py

### Deployment [![Deploy](https://www.herokucdn.com/deploy/button.png)](https://heroku.com/deploy)

The simplest way to deploy the app is to create a Heroku application, add a RabbitMQ add-on, and push
this repository to the application.

## Credits

`apa102.py` is adapted from Martin Erzberger's [APA-102c LED control lib](https://github.com/tinue/APA102_Pi) library.

An earlier version used the Adafruit_DotStar_Pi library. Erzberger's library is both pure Python and faster.
