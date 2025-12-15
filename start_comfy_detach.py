#!/usr/bin/env python3
import os
import subprocess
import sys
from pathlib import Path

HOME = Path('/home/seanf')
DEADLY = HOME / 'deadlygraphics'
COMFY_DIR = DEADLY / 'ai' / 'ComfyUI'
LOG = DEADLY / 'comfy.log'
PY = '/home/seanf/mambaforge/envs/deadlygraphics/bin/python'

if not COMFY_DIR.exists():
    print('ComfyUI directory not found:', COMFY_DIR)
    sys.exit(1)

cmd = [PY, 'main.py', '--listen', '--port', '8188']
with open(LOG, 'a') as f:
    f.write('Starting ComfyUI\n')
    f.flush()
    # Detach using setsid so the child outlives this process
    proc = subprocess.Popen(cmd, cwd=str(COMFY_DIR), stdout=f, stderr=subprocess.STDOUT, preexec_fn=os.setsid, close_fds=True)
    f.write(f'Launched pid: {proc.pid}\n')
    f.flush()
print('Launched ComfyUI pid', proc.pid)
