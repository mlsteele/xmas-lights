import sys
import json
from flask import Flask, request, send_from_directory
from flask.ext.socketio import SocketIO, emit
import messages

app = Flask(__name__)
socketio = SocketIO(app)

import logging
app.logger.addHandler(logging.StreamHandler(sys.stdout))
app.logger.setLevel(logging.DEBUG)

@app.route("/")
def index():
    return send_from_directory("static", "index.html")

@socketio.on("ctl", namespace="/ctl")
def ctl_message(message):
    payload = {
        "label": "gamekey",
        "key": message.get("key"),
        "state": bool(message.get("state")),
    }
    print payload
    messages.publish(json.dumps(payload))

if __name__ == "__main__":
    socketio.run(app, use_reloader=True)
