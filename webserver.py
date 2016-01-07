import logging, os, re, sys
import flask
from flask import Flask, abort, request, send_from_directory, abort
from flask.ext.socketio import SocketIO, emit

from publish_message import publish
logging.getLogger('messages').setLevel(logging.INFO)

SMS_TEXT_RE = r'^(on|off|\d+)$'

if os.environ.get('TWILIO_ACCOUNT_SID'):
    from twilio.rest import TwilioRestClient
    twilio = TwilioRestClient(os.environ['TWILIO_ACCOUNT_SID'], os.environ['TWILIO_AUTH_TOKEN'])

app = Flask(__name__)
socketio = SocketIO(app)

import logging
app.logger.addHandler(logging.StreamHandler(sys.stdout))
app.logger.setLevel(logging.DEBUG)

def validate_token(token):
    def validate_token_decorator(func):
        def func_wrapper(*args, **kwargs):
            if token != request.form['token']:
                return abort(403)
            return func(*args, **kwargs)
        return (func_wrapper if token else func)
    return validate_token_decorator

# Web hooks

@app.route('/ifttt', methods=['POST'])
@validate_token(os.environ.get('IFTTT_TOKEN'))
def ifttt():
    publish('action', action=request.form['action'])
    return 'ok'

@app.route('/slack', methods=['POST'])
@validate_token(os.environ.get('SLACK_WEBHOOK_TOKEN'))
def slack():
    message = request.form['text']
    message = re.sub(r'[!@]\S+\s*', '', message)
    if re.match(SMS_TEXT_RE, message):
        body = 'treelights' + message
        twilio.messages.create(
            from_ = os.environ['TWILIO_SMS_NUMBER'],
            to    = os.environ['TWILIO_SMS_TARGET_NUMBER'],
            body  = body,
        )
    else:
        publish('action', action=message)
    return flask.jsonify(text='ok')

# Game server

@app.route("/")
def index():
    return send_from_directory("static", "index.html")

@socketio.on("ctl", namespace="/ctl")
def ctl_message(message):
    payload = {
        "key": message.get("key"),
        "state": bool(message.get("state")),
    }
    print payload
    publish("gamekey", **payload)

if __name__ == '__main__':
    socketio.run(app, use_reloader=True)
