__author__ = 'mcowger'

import logging


logging.basicConfig(level=logging.INFO, format="%(asctime)s: %(levelname)s:%(funcName)s:%(module)s: %(message)s")
logger = logging.getLogger("")
logging.getLogger("requests.packages.urllib3.connectionpool").setLevel(logging.WARN)



import requests
import time
import json
import pygal
import datetime
import time
import boto
from pprint import pprint
from boto.s3.key import Key
from options import *
from boto.dynamodb2.table import Table
connection=boto.dynamodb2.connect_to_region('us-east-1')
mileage_table = Table('mileage')


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
            'emailaddress': FORD_USER,
            'password': FORD_PASS,
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
        'time': int(float(time.time())),
        'dte':km_to_miles(data['ELECTRICDTE']),
        'odometer':km_to_miles(data['ODOMETER']),
        'soc':int(float(data['stateOfCharge'])),
        'latlong': str(",".join([data['LATITUDE'],data['LONGITUDE']]))
    }

    logger.info(chopped)
    return chopped

def get_all_data():

    data = mileage_table.scan()
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

        #pprint(dict(datapoint))
        dates.append(
            (
                datetime.datetime.fromtimestamp(datapoint['time']),
                float(datapoint['odometer'])
            )
        )


    dates.sort(key=lambda tup: tup[0])
    #pprint(dates)

    line_chart.add("Odometer",dates)

    return line_chart.render()



def save_to_s3(filename,data):
    s3conn = boto.connect_s3(S3_AKIA, S3_SECRET) #set up an S3 style connections
    bucket = s3conn.get_bucket(S3_BUCKET)
    k = Key(bucket)
    k.key = filename
    k.content_type = 'image/svg+xml'
    k.set_metadata('Content-Type', 'image/svg+xml')

    try:
        k.set_contents_from_string(data)
        k.set_acl('public-read')
    except boto.exception.S3ResponseError as e:
        logger.critical("BAD RESPONSE FROM Object: {}".format(e))

    return k

def push_to_db(data):

    try:
        mileage_table.put_item(data)

    except:
        raise



def lambda_handler(event=None, context=None):
        try:
            push_to_db(get_current_data_from_ford())

            #get_all_data()

            save_to_s3("odometer.svg",get_all_data())
        except Exception as e:
            raise(e)

if __name__ == "__main__":
    lambda_handler()
