import json, sys
import paho.mqtt.publish as mqtt_publish
import mqtt_config
import logging

logger = logging.getLogger('messages')

def publish(messageType, **payload):
    payload['type'] = messageType
    logger.info("publish topic=%s payload=%s", mqtt_config.TOPIC, payload)
    auth = dict(username=mqtt_config.username, password=mqtt_config.password)
    mqtt_publish.single(mqtt_config.TOPIC, payload=json.dumps(payload), qos=1, retain=True,
        hostname=mqtt_config.hostname, auth=auth, port=1883, client_id="")

if __name__ == '__main__':
    action = "test"
    if len(sys.argv) > 1:
        action = sys.argv[1]

    publish("action", action=action)
