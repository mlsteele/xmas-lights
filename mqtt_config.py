from urlparse import urlparse
import os

MQTT_ENV_VARS = ['MQTT_URL', 'CLOUDMQTT_URL', 'CLOUDAMQP_URL']
MQTT_URL = next((value for value in (os.environ.get(name) for name in MQTT_ENV_VARS) if value), "mqtt://localhost")

TOPIC = 'xmas-lights'

hostname = None
username = None
password = None

if MQTT_URL:
    url = urlparse(MQTT_URL)

    hostname = url.hostname
    username = url.username
    password = url.password

    if url.path:
        username = url.path[1:] + ':' + username

    auth = dict(username=username, password=password) if username else None
    port = 1883
