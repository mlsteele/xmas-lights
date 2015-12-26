import pika
import re, os, sys
import json
import logging

logging.basicConfig(level=logging.WARNING)
logging.getLogger('pika.connection').setLevel(logging.CRITICAL)

logger = logging.getLogger('messages')

RABBIT_URL = os.environ.get('RABBIT_URL') or os.environ.get('CLOUDAMQP_URL')
MESSAGE_QUEUE = 'lights'

if RABBIT_URL:
    url = re.sub(r'(\/\/([^@]+@)[^:\/]+)\/', '\\1:5672/', RABBIT_URL)
    parameters = pika.URLParameters(url)
else:
    parameters = pika.ConnectionParameters(host='localhost')
parameters.socket_timeout = 5

connection = None
try:
    connection = pika.BlockingConnection(parameters)
except pika.exceptions.AMQPConnectionError as err:
    print "Error starting rabbit:", type(err).__name__ + ':', repr(err)
except Exception as err:
    print "Error starting rabbit:", type(err).__name__ + ':', repr(err)

if connection:
    channel = connection.channel()
    channel.queue_declare(queue=MESSAGE_QUEUE, durable=True)

def get_message():
    if not connection: return None
    (frame, props, body) = channel.basic_get(queue=MESSAGE_QUEUE, no_ack=True)
    if not frame: return None
    logger.info("receive %s", body)
    return json.loads(body)

def publish(messageType, **payload):
    payload['type'] = messageType
    logger.info("publish %s", payload)
    channel.basic_publish(
        exchange    = '',
        routing_key = 'lights',
        body        = json.dumps(payload),
        properties  = pika.BasicProperties(delivery_mode=2) # persistent
      )

if __name__ == '__main__':
    logger.setLevel(logging.INFO)

    if len(sys.argv) > 1:
        # publish a test message
        publish("action", action=sys.argv[1])
        connection.close()
    else:
        print 'Waiting for messages'
        while True:
            get_message()
