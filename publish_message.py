import json, sys
import paho.mqtt.publish as mqtt_publish
import mqtt_config
import logging

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger('messages')

def publish(messageType, **payload):
    payload['type'] = messageType
    logger.info("publish topic=%s payload=%s", mqtt_config.TOPIC, payload)
    mqtt_publish.single(mqtt_config.TOPIC,
        payload=json.dumps(payload),
        qos=1,
        retain=True,
        hostname=mqtt_config.hostname,
        auth=mqtt_config.auth,
        port=mqtt_config.port,
        client_id="")

def repl():
    import readline
    while True:
        command = str(raw_input('> '))
        publish("action", action=command)

def main():
    logger.setLevel(logging.INFO)
    if not mqtt_config.hostname:
        print >> sys.stderr, 'At least one of these must be set:', ', '.join(mqtt_config.MQTT_ENV_VARS)
        sys.exit(1)
    action = "test"
    if len(sys.argv) > 1:
        action = sys.argv[1]
        publish("action", action=action)
    else:
        repl()

if __name__ == '__main__':
    main()
