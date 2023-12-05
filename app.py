from flask import Flask, request, jsonify
import requests
import os
from twitter.twitter_parser import TwitterWorker

from rq import Queue
from rq.job import Job
from red import conn


# Initialize App
app = Flask(__name__)
#basedir = os.path.abspath(os.path.dirname(__file__))
q = Queue(connection=conn)

# Run Downloader


NUMBER_OF_ACCOUNTS = 2

drivers = {}

@app.route('/new_worker')
def run():
    worker_code = 1
    while worker_code <= NUMBER_OF_ACCOUNTS:
        if not conn.exists(f"instance:{worker_code}"):
            driver = TwitterWorker()
            conn.hset(f"instance:{driver.WORKER_CODE}", mapping={"is_free": "True"})
            drivers[driver.WORKER_CODE] = driver
            return 'OK'
        else:
            worker_code += 1
    return "All workers already created!"



@app.route('/run1')
def run1():

    t_worker = get_free_worker().attachToSession()
    q.enqueue(t_worker.start_twitter_session)
    conn.hset(f"instance:{t_worker.result.WORKER_CODE}", mapping={"is_free": "True"})
    return 'OK'


@app.route('/run2')
def run2():

    t_worker = get_free_worker().attachToSession()
    q.enqueue(t_worker.do_smth)
    conn.hset(f"instance:{t_worker.result.WORKER_CODE}", mapping={"is_free": "True"})
    return 'OK'

@app.route('/run3')
def run3():

    q.enqueue(print, 33)
    return 'OK'

@app.route('/run4')
def run4():

    t_worker = get_free_worker().attachToSession()

    q.enqueue(t_worker.do_smth2)
    return 'OK'


def get_free_worker():
    worker_code = 1
    while worker_code <= NUMBER_OF_ACCOUNTS :
        if conn.exists(f"instance:{worker_code}"):
            print(str(conn.hget(f"instance:{worker_code}", "is_free")))
            if str(conn.hget(f"instance:{worker_code}", "is_free")) == "b'True'":
                conn.hset(f"instance:{worker_code}", mapping={"is_free": "False"})
                return drivers[worker_code]
            else:
                worker_code += 1
        else:
            worker_code += 1



if __name__ == '__main__':
    app.run(debug=True, use_reloader=True)
