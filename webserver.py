import re, os, sys
import flask
from flask import Flask, abort, request
from flask import abort
from messages import publish

IFTTT_TOKEN = os.environ.get('IFTTT_TOKEN')
SLACK_WEBHOOK_TOKEN = os.environ.get('SLACK_WEBHOOK_TOKEN')

app = Flask(__name__)

import logging
app.logger.addHandler(logging.StreamHandler(sys.stdout))
app.logger.setLevel(logging.DEBUG)

@app.route('/ifttt', methods=['POST'])
def ifttt():
    if IFTTT_TOKEN and IFTTT_TOKEN != request.form['token']:
        return abort(403)
    publish('action', action=request.form['action'])
    return 'ok'

@app.route('/slack', methods=['POST'])
def slack():
    if SLACK_WEBHOOK_TOKEN and SLACK_WEBHOOK_TOKEN != request.form['token']:
        return abort(403)
    message = request.form['text']
    message = re.sub(r'[!@]\S+\s*', '', message)
    publish('action', action=message)
    return flask.jsonify(text='ok')

if __name__ == '__main__':
    app.run()
