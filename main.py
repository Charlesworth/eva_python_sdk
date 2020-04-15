#!/usr/bin/env python3

import time
import json
import logging
import signal
import sys

from evasdk import Eva, EvaState

host_ip = input(" IP please: ")
token = input(" Token please: ")

eva = Eva(host_ip, token)
# logging.basicConfig(level=logging.DEBUG)

evaState = EvaState(host_ip, eva.auth_create_session(), eva.data_snapshot())

def signal_handler(sig, frame):
    print('Closing connection')
    evaState.close()
    sys.exit(0)
signal.signal(signal.SIGINT, signal_handler)
print('Press Ctrl+C to exit')

def onLoop(changes):
    if 'control' in changes:
        if 'loop_count' in changes['control']:
            print("******************* Loop Update:", changes['control']['loop_count'])

evaState.add_state_change_handler(onLoop)

while True:
    print(evaState.state())
    time.sleep(1)
