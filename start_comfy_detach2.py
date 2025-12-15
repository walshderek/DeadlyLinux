#!/usr/bin/env python3
import os
import subprocess
import sys
from pathlib import Path

HOME = Path('/home/seanf')
DEADLY = HOME / 'deadlygraphics'
POSSIBLE = [DEADLY / 'ai' / 'ComfyUI', DEADLY / 'ai' / 'apps' / 'ComfyUI', DEADLY / 'ComfyUI']
COMFY_DIR = None
for p in POSSIBLE:
    if p.exists():
        COMFY_DIR = p
        break

if COMFY_DIR is None:
    print('ComfyUI directory not found; looked in:')
    for p in POSSIBLE:
        print(' -', p)
    sys.exit(1)

LOG = DEADLY / 'comfy.log'
PY = '/home/seanf/mambaforge/envs/deadlygraphics/bin/python'

cmd = [PY, 'main.py', '--listen', '--port', '8188']
with open(LOG, 'a') as f:
    f.write('Starting ComfyUI from ' + str(COMFY_DIR) + '\n')
    f.flush()
    proc = subprocess.Popen(cmd, cwd=str(COMFY_DIR), stdout=f, stderr=subprocess.STDOUT, preexec_fn=os.setsid, close_fds=True)
    f.write(f'Launched pid: {proc.pid}\n')
    f.flush()
print('Launched ComfyUI pid', proc.pid, 'from', COMFY_DIR)
