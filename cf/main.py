# Copyright 2018 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the 'License');
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an 'AS IS' BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import sys


def decode_data(payload):
    from construct import Struct, Int8ub, Int16ub, Float32l


    pytrack = Struct(
        "lat" / Float32l,
        "lng" / Float32l,
        "roll" / Int8ub,
        "pitch" / Int8ub,
        "volt" / Int8ub,
        "wake" / Int8ub,
    )
    s = pytrack.parse(bytearray.fromhex(payload))
    p = {}
    if 'lat' in s.keys():
        p['lat'] = s['lat']
    if 'lng' in s.keys():
        p['lng'] = s['lng']
    if 'roll' in s.keys():
        p['roll'] = (s['roll'] - 128.0) / (256.0 / 360.0)
    if 'pitch' in s.keys():
        p['pitch'] = (s['pitch'] - 128.0) / (256.0 / 180.0)
    if 'volt' in s.keys():
        p['volt'] = s['volt'] / 256.0 * 5.0
    if 'wake' in s.keys():
        p['wake'] = s['wake']
    return p


def pubsub_bigquery_pytrack(event, context):
    # [START functions_pubsub_bigquery_pytrack]
    """Triggered from a message on a Cloud Pub/Sub topic.
    Args:
         event (dict): Event payload.
         context (google.cloud.functions.Context): Metadata for the event.
    """
    import os
    import base64
    import json
    from rfc3339 import rfc3339
    from google.cloud import bigquery


    project_id = os.environ.get('GCP_PROJECT')
    bigquery_dataset = os.environ.get('BIGQUERY_DATASET')
    bigquery_table = os.environ.get('BIGQUERY_TABLE')
    device_type = os.environ.get('DEVICE_TYPE')
    if (not project_id or not bigquery_dataset or not
        bigquery_table or not device_type):
        print('Error reading Function environment variables')
        return

    client = bigquery.Client(project=project_id)
    table_ref = client.dataset(bigquery_dataset).table(bigquery_table)
    table = client.get_table(table_ref)

    pubsub_data = base64.b64decode(event['data']).decode('utf-8')
    print('Data JSON: {}'.format(pubsub_data))

    d = json.loads(pubsub_data)

    # Only process the payload if the device type matches
    if 'deviceType' in d:
        if device_type in d['deviceType']:
            try:
                time_int = int(d['time'])
            except ValueError:
                time_int = float(d['time'])
                time_int = int(time_int)
            d['time'] = rfc3339(time_int)

            payload = d['data']
            p = decode_data(payload)

            if 'lat' in p.keys():
                if p['lat'] != 0.0:
                    d['lat'] = p['lat']
            if 'lng' in p.keys():
                if p['lng'] != 0.0:
                    d['lng'] = p['lng']
            if 'roll' in p.keys():
                d['roll'] = p['roll']
            if 'pitch' in p.keys():
                d['pitch'] = p['pitch']
            if 'volt' in p.keys():
                d['volt'] = p['volt']
            if 'wake' in p.keys():
                d['wake'] = p['wake']

            rows_to_insert = [(\
                d.get('device'),\
                d.get('time'),\
                d.get('data'),\
                d.get('seqNumber'),\
                d.get('lat'),\
                d.get('lng'),\
                d.get('roll'),\
                d.get('pitch'),\
                d.get('volt'),\
                d.get('lqi'),\
                d.get('fixedLat'),\
                d.get('fixedLng'),\
                d.get('operatorName'),\
                d.get('countryCode'),\
                d.get('computedLocation')
                )]
            print('BQ Row: {}'.format(rows_to_insert))
            errors = client.insert_rows(table, rows_to_insert)
            try:
                assert errors == []
            except AssertionError:
                print("BigQuery insert_rows error: {}".format(errors))
    return
    # [END functions_pubsub_bigquery_pytrack]
