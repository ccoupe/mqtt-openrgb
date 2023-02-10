# Taken from 
#    https://gist.github.com/ghomasHudson/7cc24aa187e8141003073e36e068a5a2
# and heavily modified by Cecil Coupe, 1/15/2023
# 2/3/2023 - v1.0 - can set colors for top level devices.
# 2/6/2023 - v1.1 - add minimal support for profiles.
#                 - add minimal support for modes
#                 - list zones  - no supporting methods
#

from openrgb import OpenRGBClient
from openrgb.utils import RGBColor, DeviceType
import paho.mqtt.client as mqtt
import json
import time
import json
import argparse
import warnings
import sys
from lib.Settings import Settings
from socket import gaierror
from RGBServer import RGBServer
import threading
from threading import Lock, Thread

state_template = {"state":"ON","brightness":255,"color":{"r":255,"g":255,"b":255}}
active_servers = []


def on_connect(client, userdata, flags, rc):
    print("Connection returned result: "+mqtt.connack_string(rc))

'''
def get_real_color(state):
    """Apply brightness scaling to RGB"""
    brightness_multiplier = state["brightness"]/255
    return [int(state["color"]["r"]*brightness_multiplier),int(state["color"]["g"]*brightness_multiplier),int(state["color"]["b"]*brightness_multiplier)]
'''

def on_message(client, userdata, message):
    global active_servers
    print("message received " ,str(message.payload.decode("utf-8")))
    print("message topic=",message.topic)
    
    msg = json.loads(message.payload)
    topic = message.topic
    flds = topic.split('/')
    us = None
    for srv in active_servers:
      if flds[1] == srv.name:
        us = srv
        break
    if not us:
      print("topic is not ours")
      return

    if flds[2] == 'cmd':
      if flds[3] == 'set':
        
        if msg.get('color', None):
          dt = msg['color']
          print(f"setting all devices to r:{dt['r']},g:{dt['g']},b:{ dt['b']}")
          us.rgb_server.set_color(RGBColor(dt['r'], dt['g'], dt['b']))
        elif msg.get('state', None) == 'off':
          print("turning off all devices")
          us.rgb_server.clear()
        else:
          print("unknown cmd/set:", payload)
      return
    elif flds[2]== 'profile':
      if flds[3] == 'set':
        if msg.get('name'): 
          us.rgb_server.load_profile(msg['name'])
          print(f'Setting profile to {msg["name"]}')
      else:
        print(f'unknown profile/set', payload)
      return
    else:
      # These topics are for the individual devices that respond to /set
      # find the matching mqtt subscription to get to the proxy device
      # Now we can use the devinternals hash tree. First get the tree 
      # for the machine
      dev = us.devices[flds[2]]
      # print("dev=", dev)
      if dev == flds[2]: 
        proxy = dev['internal']
        if msg.get('state') == 'Off' or msg.get('state') == 'off':
          msg['r'] = msg['g'] = msg['b'] = 0
        elif msg.get('mode'):
         proxy.set_mode(msg.get('mode'))
        elif msg.get('color'):
          dt = msg.get(['color'])
          if dt['r'] <= 255 and dt['g'] <= 255 and dt['b'] <= 255:
            print(f"Setting {flds[2]} to r:{dt['r']},g:{dt['g']},b:{ dt['b']}")
            proxy.set_color(RGBColor(dt['r'], dt['g'], dt['b']))

      
def initialise_mqtt_clients(cname):
    client= mqtt.Client(cname,False) #don't use clean session
    client.on_connect= on_connect        #attach function to callback
    client.on_message=on_message        #attach function to callback
    client.topic_ack=[]
    client.run_flag=False
    client.running_loop=False
    client.subscribe_flag=False
    client.bad_connection_flag=False
    client.connected_flag=False
    client.disconnect_flag=False
    return client

def try_server(srv):
  global active_servers
  if srv.bring_online():
    # it's up and running
    if not srv.subscribed:
      srv.subscribe()
      srv.sendConfig()
      # we are good to go, any time hubitat wants us.
      if not srv in active_servers:
        active_servers.append(srv)
  else:
    th = threading.Timer(2 * 60, try_server, args=(srv,))
    th.start()
  
def main(argList=None):
  global subscribe_list, openrgb_machines, settings, client, rgb_client
  global devinternals, mqtt_server
  ap = argparse.ArgumentParser()
  loglevels = ('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL')
  ap.add_argument("-c", "--conf", required=True, type=str,
    help="path and name of the json configuration file")
  ap.add_argument("-s", "--syslog", action = 'store_true',
    default=False, help="use syslog")
  
  args = vars(ap.parse_args())  
  settings = Settings(args['conf'])

  openrgb_machines = settings.machines
  client = initialise_mqtt_clients("mqttopenrgb")    
  client.connect(settings.mqtt_server, settings.mqtt_port)
  
  subscribe_list = []
  top_level = []
  devinternals = {}
  for pc in openrgb_machines:
    node =  pc['name']
    srv = RGBServer(client, node, pc['ip'], pc['port'])
    print("Starting up with",node)
    try_server(srv)
  
  # there isn't much to do except get the cmds from mqtt and send them
  # to the (proxy) devices. Oh, and handle failures because it is normal
  # for the openrgb device to go offline for long periods of time - days?
  client.loop_forever()
  
if __name__ == '__main__':
  sys.exit(main())

   
