from urlparse import urlparse
import os

MQTT_URL = os.environ.get('MQTT_URL') or os.environ.get('CLOUDMQTT_URL') or os.environ.get('CLOUDAMQP_URL')

TOPIC = 'xmas-lights'

if MQTT_URL:
    url = urlparse(MQTT_URL or "mqtt://localhost")

    hostname = url.hostname
    username = url.username
    password = url.password

    if url.path:
        username = url.path[1:] + ':' + username
else:
    hostname = None
    username = None
    password = None
