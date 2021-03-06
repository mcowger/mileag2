__author__ = 'mcowger'

import logging


logging.basicConfig(level=logging.WARNING, format="%(asctime)s: %(levelname)s:%(funcName)s:%(module)s: %(message)s")
logger = logging.getLogger()
logging.getLogger("requests.packages.urllib3.connectionpool").setLevel(logging.WARN)



import requests
import json
import pygal
import datetime
import time
from pprint import pprint

import boto3
from options import *

session = boto3.session.Session(aws_access_key_id=S3_AKIA, aws_secret_access_key=S3_SECRET, region_name='us-east-1')
dynamodb = session.resource('dynamodb')
mileage_table = dynamodb.Table('mileage')
s3 = session.resource('s3')

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
    print(chopped)
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


    for datapoint in data['Items']:

        #pprint(datapoint)
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

    try:

        s3_object = s3.Object(S3_BUCKET, filename).put(Body=data, ContentType='image/svg+xml', ACL='public-read')


    except Exception as e:
        logger.critical("BAD RESPONSE FROM Object: {}".format(e))

    return s3_object

def push_to_db(data):

    try:

        mileage_table.put_item(Item=data)

    except:
        raise


def lambda_handler(event=None, context=None):
        try:
            push_to_db(get_current_data_from_ford())
            save_to_s3("odometer.svg",get_all_data())
        except Exception as e:
            raise(e)

if __name__ == "__main__":
    lambda_handler()
