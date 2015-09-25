__author__ = 'mcowger'


import mileage
import requests
import datetime
from pprint import pprint

data = requests.get("http://data.sparkfun.com/output/xRRd17G9V1f2VDlLNLOg.json").json()[::-1]

first = None
counter = 0
for entry in data:
    odometer = entry['ODOMETER']
    dte = entry['ELECTRICDTE']
    latlong = "37.832,-122.2026"
    soc = entry['stateOfCharge']
    time = datetime.datetime.fromtimestamp(float(entry['orig_timestamp']))
    document = {
        'odometer': float(odometer),
        'dte': float(dte),
        'latlong': latlong,
        'soc': float(soc),
        'time':time
    }
    mileage.push_to_mongo(document)
    pprint(document)
    counter += 1
    pprint("{}/{}".format(counter,len(data)))

