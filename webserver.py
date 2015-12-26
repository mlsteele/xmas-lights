import os, re
import flask
from flask import Flask, abort, request
from flask import abort
from messages import publish

app = Flask(__name__)

SLACK_WEBHOOK_TOKEN = os.environ.get('SLACK_WEBHOOK_TOKEN')

@app.route('/ifttt', methods=['POST'])
def ifttt():
    publish(request.form['event'])
    return 'ok'

@app.route('/slack', methods=['POST'])
def slack():
    if SLACK_WEBHOOK_TOKEN and SLACK_WEBHOOK_TOKEN != request.form['token']:
        return abort(403)
    message = request.form['text']
    message = re.sub(r'[!@]\S+\s*', '', message)
    publish(message)
    return flask.jsonify(text='ok')

if __name__ == '__main__':
    app.run()
