from flask import Flask, request
from messages import publish

app = Flask(__name__)

@app.route('/ifttt', methods=['POST'])
def ifttt():
    publish(request.form['event'])
    return 'ok'

@app.route('/slack', methods=['POST'])
def slack():
    publish(request.form['text'])
    return 'ok'

if __name__ == '__main__':
    app.run()
