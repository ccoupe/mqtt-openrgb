#!/bin/bash
cd /home/ccoupe/Projects/iot/openrgb
source ~/anaconda3/etc/profile.d/conda.sh
conda activate py3
python3 mqttrgb.py -c games.json 
