# Taken from 
#    https://gist.github.com/ghomasHudson/7cc24aa187e8141003073e36e068a5a2
# and heavily modified by Cecil Coupe, 1/15/2023
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
                    
state_template = {"state":"ON","brightness":255,"color":{"r":255,"g":255,"b":255}}

def on_connect(client, userdata, flags, rc):
    print("Connection returned result: "+mqtt.connack_string(rc))
'''
def get_real_color(state):
    """Apply brightness scaling to RGB"""
    brightness_multiplier = state["brightness"]/255
    return [int(state["color"]["r"]*brightness_multiplier),int(state["color"]["g"]*brightness_multiplier),int(state["color"]["b"]*brightness_multiplier)]
'''

def on_message(client, userdata, message):
    global subscribe_list, openrgb_machines
    print("message received " ,str(message.payload.decode("utf-8")))
    print("message topic=",message.topic)
    msg = json.loads(message.payload)
    topic = message.topic
    flds = topic.split('/')
    # find the matching subscription to get to the proxy device
    for ent in subscribe_list:
      if ent == topic:
        for machine in openrgb_machines:
          if machine['name'] == flds[1]: 
            # Now find the device
            dev = machine['devices'][flds[2]]
            if dev is not None:
              proxy = dev['internal']
              if msg.get('state') == 'OFF' or msg.get('state') == 'off':
                msg['r'] = msg['g'] = msg['b'] = 0
              if msg['r'] <= 255 and msg['g'] <= 255 and msg['b'] <= 255:
                print(f"Setting {flds[2]} to r:{msg['r']},g:{msg['g']},b:{ msg['b']}")
                proxy.set_color(RGBColor(msg['r'], msg['g'], msg['b']))

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


def get_machine_state(ip, port):
  #
  devices = {}
  try: 
    print("Getting rgb info from",ip,port)
    rgb_client = OpenRGBClient(ip, port, 'mqttopenrgb')
    # TODO - multiple addressable devices may be found
    mb = rgb_client.get_devices_by_type(DeviceType.MOTHERBOARD)
    for dev in mb:
      key = dev.name.replace(" ", "_")
      # get the 'state': on/off, intensity, color
      # not supported in the network api. 
      devices[key] = {'id': dev.id, 'type': DeviceType.MOTHERBOARD,
            'internal': dev}
      print(f"Motherboard id:{dev.id} {key}")
      
    for dev in rgb_client.get_devices_by_type(DeviceType.GPU):
      key = dev.name.replace(" ", "_")
      devices[key] = {'id': dev.id, 'type': DeviceType.GPU,
            'internal': dev}
      print(f"GPU id:{dev.id} {key}")
    
    for dev in rgb_client.get_devices_by_type(DeviceType.DRAM):
      key = dev.name.replace(" ", "_")
      devices[key] = {'id': dev.id, 'type': DeviceType.DRAM,
            'internal': dev}
      print(f"DRAM id:{dev.id} {key}")
  except ConnectionRefusedError:
    print('connection refused',ip)
    return None
  except TimeoutError:
    print('timeout in get_machine_state',ip)
    return None
    
  return devices
  
def main(argList=None):
  global subscribe_list, openrgb_machines, settings, client
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
  for pc in openrgb_machines:
    machine = pc['name']
    base_topic = "openrgb/" + machine
    devices = get_machine_state(pc['ip'], pc['port'])
    if devices == None:
      continue
    devnames = []
    for key in devices.keys():
      devnames.append(key)
      topic = f'{base_topic}/{key}/set'
      #print("subscribing to",topic)
      client.subscribe(topic)
      subscribe_list.append(topic)
    
    # save the devices for that machine. 
    pc['devices'] = devices
    # build a tree for a json dump of current configuation
    # including on/off,brightness and r,g,b
    toplvl = {'name': machine, 'devices': devnames}
    top_level.append(toplvl)
    client.publish(f'{base_topic}/config', json.dumps(toplvl), qos=0, retain=True)
    client.subscribe(f"openrgb/{machine}/cnd/set")
    subscribe_list.append(f"openrgb/{machine}/cnd/set")
  # Version 1 of this code doesn't handle zones or anything complicated
  #   
  print(json.dumps(top_level))
  print("Subscriptions", subscribe_list)
  
  # there isn't much to do except get the colors from mqtt and set them
  # on the (proxy) device.
  client.loop_forever()
  
if __name__ == '__main__':
  sys.exit(main())

   
