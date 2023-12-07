import redis
from flask import Flask
from parser.twitter_parser import TwitterWorker


conn = redis.Redis()
# Initialize App
app = Flask(__name__)

# Run parser
driver = TwitterWorker()
conn.set(f"instance:{driver.WORKER_CODE}", True)


@app.route('/run1')
def run1():
    driver.start_twitter_session()
    return 'OK'


if __name__ == '__main__':
    app.run(debug=True, use_reloader=True, host='0.0.0.0')
