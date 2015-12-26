import os
import flask
from flask import Flask, abort, request
from messages import publish

app = Flask(__name__)

@app.route('/ifttt', methods=['POST'])
def ifttt():
    publish(request.form['event'])
    return 'ok'

@app.route('/slack', methods=['POST'])
def slack():
    message = request.form['text']
    message = re.sub(r'[!@]\S+\s*', '', message)
    publish(message)
    return flask.jsonify(text='ok')

if __name__ == '__main__':
    app.run()
