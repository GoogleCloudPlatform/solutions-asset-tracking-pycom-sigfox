# Copyright 2019 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import argparse
import binascii
from construct import Struct, Flag, Int8ub, Int16ub, Float32l


pytrack_config = Struct(
    "DOWNLINK_HR" / Int8ub,
    "SLEEP_MIN" / Int16ub,
    "DEEP_SLEEP" / Int8ub,
    "GPS_WAIT_SEC" / Int8ub,
    "COMMAND" / Int8ub,
    "RESERVED" / Int16ub
)


def parse_command_line_args():
  """Parse command line arguments."""
  parser = argparse.ArgumentParser(description=(
      'Data and config payload parser for Pytrack.'))
  parser.add_argument(
      '--parser-mode',
      choices=('encode-config', 'decode-data'),
      default='decode-data',
      required=True,
      help='Parser mode: encode-config|decode-data.')
  parser.add_argument(
      '--hex-string',
      type=str,
      default='',
      help='Pytrack payload HEX string.')
  parser.add_argument(
      '--in-file',
      help='Pytrack config input file.')
  parser.add_argument(
      '--out-file',
      required=False,
      help='Pytrack config output file, generated from '
           'parsed payload config data.')
  return parser.parse_args()


def decode_data(data):
  print("Pytrack sensor data:")
  pytrack = Struct(
      "lat" / Float32l,
      "lng" / Float32l,
      "roll" / Int8ub,
      "pitch" / Int8ub,
      "volt" / Int8ub,
      "wake" / Int8ub,
  )
  s = pytrack.parse(bytearray.fromhex(data))
  print(s)
  d = {}
  if 'lat' in s.keys():
    d['lat'] = s['lat']
  if 'lng' in s.keys():
    d['lng'] = s['lng']
  if 'roll' in s.keys():
    d['roll'] = (s['roll'] - 128.0) / (256.0 / 360.0)
  if 'pitch' in s.keys():
    d['pitch'] = (s['pitch'] - 128.0) / (256.0 / 180.0)
  if 'volt' in s.keys():
    d['volt'] = s['volt'] / 256.0 * 5.0
  if 'wake' in s.keys():
    d['wake'] = s['wake']
  return d


def decode_config(data):
  print('Pytrack device configuration:')
  c = pytrack_config.parse(bytearray.fromhex(data))
  for key in c.keys():
    if key is not '_io':
      print('{} = {}'.format(key, c[key]))
  return c


def encode_config(in_file):
  print('Reading config from input file: {}'.format(in_file))
  try:
    f = open(in_file, 'r')
  except IOError:
    print('Error reading file')
    exit(1)
  c = {}
  for row in f:
    key, foo, value = row.split()
    if value == 'True':
      c[key] = True
    elif value == 'False':
      c[key] = False
    else:
      c[key] = int(value)
  data = pytrack_config.build(c)
  print('Config HEX: {}'.format(binascii.hexlify(data).decode()))
  return


def write_config_file(out_file, c):
  f = open(out_file, 'w')
  for key in c.keys():
    if key is not '_io':
      f.write('{} = {}\n'.format(key, c[key]))
  f.close()
  print('\nConfig file written to: {}'.format(out_file))
  return


args = parse_command_line_args()
if args.parser_mode == 'decode-data':
  if not args.hex_string:
    print('Error. Argument --hex-string missing.')
    exit(1)
  data_len = len(args.hex_string)
  if not (data_len == 16 or data_len == 24):
    print('Invalid Pytrack payload HEX string length. Must be 16 or '
          '24 characters.')
    exit(1)
  elif data_len == 24:
    d = decode_data(args.hex_string)
    print('\n{}'.format(d))
  elif data_len == 16:
    c = decode_config(args.hex_string)
    if args.out_file:
      write_config_file(args.out_file, c)
  else:
    exit(1)
elif args.parser_mode == 'encode-config':
  if not args.in_file:
    print('Error. Argument --in-file missing.')
    exit(1)
  encode_config(args.in_file)
exit(0)
