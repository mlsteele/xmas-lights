import pika
import re, os, sys
import logging

logging.basicConfig(format='%(levelname)s:%(message)s', level=logging.CRITICAL)

RABBIT_URL = os.environ.get('RABBIT_URL') or os.environ.get('CLOUDAMQP_URL')
XMAS_LIGHTS_QUEUE = 'lights'

if RABBIT_URL:
    url = re.sub(r'(\/\/([^@]+@)[^:\/]+)\/', '\\1:5672/', RABBIT_URL)
    parameters = pika.URLParameters(url)
else:
    parameters = pika.ConnectionParameters(host='localhost')

connection = None
try:
    connection = pika.BlockingConnection(parameters)
except pika.exceptions.AMQPConnectionError as err:
    print type(err).__name__ + ':', repr(err)
    if RABBIT_URL:
        exit(1)

if connection:
    channel = connection.channel()
    channel.queue_declare(queue=XMAS_LIGHTS_QUEUE, durable=True)

def get_message():
    if not connection:
        return None
    (frame, props, body) = channel.basic_get(queue=XMAS_LIGHTS_QUEUE, no_ack=True)
    if body:
        return body
    else:
        return None

def publish(body):
    channel.basic_publish(
        exchange='',
        routing_key='lights',
        body=body,
        properties=pika.BasicProperties(delivery_mode=2) # persistent
      )

if __name__ == '__main__':
    if len(sys.argv) > 1:
        print sys.argv[1]
        publish(sys.argv[1])
        connection.close()
    else:
        while True:
            body = get_message()
            if body: print body
