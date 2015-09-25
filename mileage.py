__author__ = 'mcowger'

import logging


logging.basicConfig(level=logging.DEBUG, format="%(asctime)s: %(levelname)s:%(funcName)s:%(module)s: %(message)s")
logger = logging.getLogger("")
logging.getLogger("requests.packages.urllib3.connectionpool").setLevel(logging.WARN)


import pymongo
import os, sys
import requests
import time
import json
import pygal
import datetime
from pprint import pprint
import boto
from boto.s3.key import Key


def km_to_miles(km):
    return int(float(km) * 0.621371)

def get_current_data_from_ford():

    ford_url = 'https://phev.myfordmobile.com/services/webLoginPS'
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.9; rv:30.0) Gecko/20100101 Firefox/30.0',
        'Accept': 'application/json, text/javascript, */*; q=0.01',
        'Content-Type': 'application/json; charset=UTF-8',
        'Cache-Control': 'no-cache',
        'X-Requested-With': 'XMLHttpRequest',
        'Referer': 'https://phev.myfordmobile.com/content/mfm/en_us/site/login.html'
    }
    login_data = {
        'PARAMS': {
            'emailaddress': os.getenv("FORD_USER"),
            'password': os.getenv("FORD_PASS"),
            'persistent': '0'
        }
    }

    try:
        response = requests.post(ford_url,data=json.dumps(login_data),headers=headers)
    except:
        raise

    data = response.json()['response']
    #logger.info(json.dumps(data))


    chopped = {
        'time': datetime.datetime.now(),
        'dte':km_to_miles(data['ELECTRICDTE']),
        'odometer':km_to_miles(data['ODOMETER']),
        'soc':int(data['stateOfCharge']),
        'latlong': str(",".join([data['LATITUDE'],data['LONGITUDE']]))
    }

    logger.info(chopped)
    return chopped

def get_all_data():
    try:
        client = pymongo.MongoClient(host=os.getenv("MONGODB"))
        database = client.get_database("iot-data")
        database.authenticate(os.getenv("MONGO_USER"),os.getenv("MONGO_PASS"))
        collection = database.get_collection("mileage")
    except:
        raise
    data = collection.find().sort("time",1)
    line_chart = pygal.DateY(
        x_label_rotation=20,
        fill=True,
        human_readable=True,
        pretty_print=True,
        width=800,
        print_values=False,
        disable_xml_declaration=False
    )


    line_chart.title = "odometer over time"
    dates = []
    for datapoint in data:
        dates.append(
            (
                datapoint['time'],
                float(datapoint['odometer'])
            )
        )

    line_chart.add("Odometer",dates)

    pprint(line_chart.render())

    client.close()

    return line_chart.render()

def save_to_s3(filename,data):
    s3conn = boto.connect_gs(os.getenv("S3_AKIA"), os.getenv("S3_SECRET")) #set up an S3 style connections
    bucket = s3conn.get_bucket(os.getenv("S3_BUCKET"))
    k = Key(bucket)
    k.key = filename
    k.content_type = 'image/svg+xml'
    k.set_metadata('Content-Type', 'image/svg+xml')

    k.set_contents_from_string(data)
    k.set_acl('public-read')
    return k

def push_to_mongo(data):
    try:
            client = pymongo.MongoClient(host=os.getenv("MONGODB"))
            database = client.get_database("iot-data")
            database.authenticate(os.getenv("MONGO_USER"),os.getenv("MONGO_PASS"))
            collection = database.get_collection("mileage")
    except:
        raise

    try:
        collection.insert_one(data)

    except:
        raise

    client.close()


if __name__ == "__main__":

    if not os.getenv("MONGODB") \
            or not os.getenv("S3_AKIA") \
            or not os.getenv("S3_SECRET") \
            or not os.getenv("S3_BUCKET")\
            or not os.getenv("FORD_USER")\
            or not os.getenv("FORD_PASS"):
        raise Exception("Failed to find required items in environment")


    while True:

        push_to_mongo(get_current_data_from_ford())

        try:
            save_to_s3("odometer.svg",get_all_data())
        except:
            raise
        time.sleep(3600)










