README.md 

For a mqtt driver of openrgb servers. Hubitat will call us with json 
payload and we reformat and call the openrgb server. 

Support multiple openrgb servers - I call them 'machines'
Only support one Motherboard color, one GPU color, one DRAM color
  per machine.
Doesn't support zones.
Doesn't support profiles.
Doesn't support modes
Setting r,g,b to zero turns off 'The RGB Puke'. 


          
Use this: Mqtt topic, payload
openrgb/<node>/set <node_payload>

<node> is the dns node name (for this case). ex: games - from games.local
it is set in the python mqtt drivers setting.json file.

<color_payload> := <color_dict>
<color_dict> :=  {"r": <val> , "g": <val> "b": <val>}
<val> is 0..255

Hubitat subscribes to `openrgb/<node>/config` The python mqtt driver publishes
(retain = true) this json (example) to that topic
  {"name": "games",
   "devices": ["ASUS_TUF_GAMING_Z790-PLUS_WIFI_D4", 
              "Gigabyte_RTX3060_Gaming_OC_12G", 
              "Patriot_Viper_Steel_RGB"
             ]}
The hubitat driver creates child devices for each of them and later they will
send <color_payload> to these topics
  ['openrgb/games/ASUS_TUF_GAMING_Z790-PLUS_WIFI_D4/set', 
                'openrgb/games/Gigabyte_RTX3060_Gaming_OC_12G/set', 
                'openrgb/games/Patriot_Viper_Steel_RGB/set']
The mqtt driver will subscribe to those.

There is a command channel `openrgb/games/cnd/set` which the the hubitat driver
can publish too. for example {"cmd": "refresh"} could cause the python mqtt driver
to republish the devices dict to /config

Sigh, Actually from Hubitat pov, we have 3 independent, separate rgb devices - three
That is a lot more hubitat work than treating them all as one.  Could help with
the discovery issue if the parse() after init() creates the child devices. 
--------

To Do
1. Error check around proxy.setcolor() - the machine could have gone 
    offline since we were started. Very Likely to happen.
2. Setting modes would be nice. Flash Red for alarm tripped for example.

