#!/bin/bash

set -v

apt-get update
apt-get install -yq \
	git python3 python3-dev python3-pip libffi-dev python3-cairosvg

python3 -m pip install -U pip

cd /home/spamsuckersunited/FinBot

pip install -r requirements.txt

chown +x stockfish_10_x64_modern
chown +x main.py

nohup /home/spamsuckersunited/FinBot/main.py &


