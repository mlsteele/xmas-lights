import logging, os, re, sys
import flask
from flask import Flask, abort, request, send_from_directory, abort
from flask.ext.socketio import SocketIO, emit

import messages
logging.getLogger('messages').setLevel(logging.INFO)

IFTTT_TOKEN = os.environ.get('IFTTT_TOKEN')
SLACK_WEBHOOK_TOKEN = os.environ.get('SLACK_WEBHOOK_TOKEN')

app = Flask(__name__)
socketio = SocketIO(app)

import logging
app.logger.addHandler(logging.StreamHandler(sys.stdout))
app.logger.setLevel(logging.DEBUG)

@app.route('/ifttt', methods=['POST'])
def ifttt():
    if IFTTT_TOKEN and IFTTT_TOKEN != request.form['token']:
        return abort(403)
    messages.publish('action', action=request.form['action'])
    return 'ok'

@app.route('/slack', methods=['POST'])
def slack():
    if SLACK_WEBHOOK_TOKEN and SLACK_WEBHOOK_TOKEN != request.form['token']:
        return abort(403)
    message = request.form['text']
    message = re.sub(r'[!@]\S+\s*', '', message)
    messages.publish('action', action=message)
    return flask.jsonify(text='ok')

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
    messages.publish("gamekey", **payload)

if __name__ == '__main__':
    socketio.run(app, use_reloader=True)
