import redis
from flask import Flask
from requests import get


conn = redis.Redis()
# Initialize App
app = Flask(__name__)



#Run parser
@app.route('/run1')
def run1():
    r = get("localhost:5050/run1")
    return r


if __name__ == '__main__':
    app.run(debug=True, use_reloader=True, host='0.0.0.0')