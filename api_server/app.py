from flask import Flask
import redis


# Initialize App
app = Flask(__name__)

#redis_client = redis.StrictRedis(host='localhost', port=6379, db=0)
redis_client = redis.StrictRedis(host='redis', port=6379, db=0) # docker


def send_message_to_channel(channel, message):
    redis_client.publish(channel, message)

@app.route('/')
def init():
    return "OK"


@app.route('/run1')
def run1():
    send_message_to_channel("parser_tasks", "login_to_twitter")
    return "OK"


@app.route('/run2')
def run2():
    send_message_to_channel("parser_tasks", "make_search")
    return "OK"


@app.route('/run3')
def run3():
    send_message_to_channel("parser_tasks", "make_parse")
    return "OK"


if __name__ == '__main__':
    app.run(host='0.0.0.0',debug=True, use_reloader=True)