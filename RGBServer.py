# 
# Describes one machine (i.e. a PC) with rgb devices and running 
# the openrgb server (as admin - or the port is opened..) 
# 
# unclear whether RGBDevice needs a class or we can 
# just wing it with some dicts and lists
#
from openrgb import OpenRGBClient
from openrgb.utils import RGBColor, DeviceType
import paho.mqtt.client as mqtt
from socket import gaierror

class RGBServer:
  def __init__(self, mqtt_server, name, ip, port=6742):
    self.ip = ip
    self.port = port
    self.name = name
    self.online = False
    self.subscribed = False
    self.subscriptions = None
    self.topic_list = []
    self.profiles = []
    self.devices = None
    self.jsondevs = None      # send to Hubitat - must be serializable
    self.rgb_server = None
    self.mqtt_server = mqtt_server
    
    self.base_topic = "openrgb/" + self.name
    topic_list = [ f'{self.base_topic}/cmd/set',
                    f'{self.base_topic}/profiles/set'
                  ]
    
  def bring_online(self):
    if self.online is False:
      try:
        self.rgb_server = OpenRGBClient(self.ip, self.port, 'mqttopenrgb')
      except ConnectionRefusedError:
        print('connection refused',self.ip)
        return False
      except TimeoutError:
        print('timeout in get_machine_state',self.ip)
        return False
      except gaierror:
        print('no local DNS - is machine off?')
        return False
      self.online = True
      
    if self.online and self.devices is None:
      self.devices = {}
      self.jsondevs = {}
      for ent in self.rgb_server.ee_devices:
        key = ent.name.replace(" ", "_")
        devlist = self.rgb_server.get_devices_by_name(ent.name)
        for dev in devlist:
          modenames = []
          zonenames = []
          for md in dev.modes:
            modenames.append(md.name)
          for zn in dev.zones:
            zonenames.append(zn.name)
            
          self.devices[key] = {"name": ent.name, 'id': dev.id, 'internal': dev,
             'modes': modenames, 'zones': zonenames, 
             'topic': f"{self.base_topic}/{ent.name}/set"}
          
          self.jsondevs[key] = {"name": ent.name, 
            "modes": modenames, "zones": zonenames}
      return True
          
    return False
      
  def sendConfig(self):
    print('sendConfig', self.jsondevs)
    
    
  def subscribe(self):
    if self.subscribed is False: 
      for ent in self.devices:
        print("Device:", ent)
