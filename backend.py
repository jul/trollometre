from flask import Flask
from flask import request


app = Flask(__name__)



@app.get("/hello/<name>")
def hello(name):
    print(name)
    return "name"

@app.get('/spam/<path:uri>/<is_spam>')
def spam(uri, is_spam):
    print("spam")
    print(uri)
    print(is_spam)
    return "spam"
