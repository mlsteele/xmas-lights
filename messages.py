import pika
import re, os, sys
import json
import logging

# logging.basicConfig(format='%(levelname)s:%(message)s', level=logging.CRITICAL)

RABBIT_URL = os.environ.get('RABBIT_URL') or os.environ.get('CLOUDAMQP_URL')
MESSAGE_QUEUE = 'lights'

if RABBIT_URL:
    parameters = pika.URLParameters(RABBIT_URL)
else:
    parameters = pika.ConnectionParameters(host='localhost')

connection = None
try:
    connection = pika.BlockingConnection(parameters)
except pika.exceptions.AMQPConnectionError as err:
    print 'Error starting rabbit:', type(err).__name__ + ':', repr(err)
except Exception as err:
    print 'Error starting rabbit:', type(err).__name__ + ':', repr(err)

if connection:
    channel = connection.channel()
    channel.queue_declare(queue=MESSAGE_QUEUE, durable=True)

def get_message():
    if not connection: return None
    (frame, props, body) = channel.basic_get(queue=MESSAGE_QUEUE, no_ack=True)
    if not frame: return None
    return json.loads(body)

def publish(messageType, **payload):
    payload['type'] = messageType
    channel.basic_publish(
        exchange    = '',
        routing_key = 'lights',
        body        = json.dumps(payload),
        properties  = pika.BasicProperties(delivery_mode=2) # persistent
      )

if __name__ == '__main__':
    # publish a message
    if len(sys.argv) > 1:
        print sys.argv[1]
        publish("action", action=sys.argv[1])
        connection.close()
    else:
        while True:
            body = get_message()
            if body: print body
