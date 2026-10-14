"""Read-only deployment inventory. Does not build, create, stop or remove anything."""
import argparse
import json
import socket
import subprocess
from pathlib import Path

parser=argparse.ArgumentParser()
parser.add_argument('--baseline',default='artifacts/docker-before.json')
args=parser.parse_args()

def docker(*args):
    return subprocess.check_output(['docker',*args],text=True).strip()

rows=[json.loads(line) for line in docker('ps','-a','--format','json').splitlines() if line.strip()]
names={row['Names'] for row in rows}
expected={'ads-mcp-6666-api','ads-mcp-6666-worker','ads-mcp-6666-postgres'}
conflicts=[]
for port in (6666,16666):
    with socket.socket() as connection:
        try:connection.bind(('127.0.0.1',port))
        except OSError:conflicts.append(f'Host port {port} is occupied')
for name in expected&names:conflicts.append('Container name already exists: '+name)
if 'ads-mcp-6666-pgdata' in docker('volume','ls','--format','{{.Name}}').splitlines():conflicts.append('Data volume already exists; inspect before reuse')
if 'ads-mcp-6666-net' in docker('network','ls','--format','{{.Name}}').splitlines():conflicts.append('Network already exists; inspect before reuse')
baseline=Path(args.baseline);baseline.parent.mkdir(parents=True,exist_ok=True)
baseline.write_text(json.dumps({'containers':rows,'conflicts':conflicts},ensure_ascii=False,indent=2))
print(json.dumps({'existingContainerCount':len(rows),'conflicts':conflicts,'baseline':str(baseline),'mutationsPerformed':False},ensure_ascii=False))
raise SystemExit(1 if conflicts else 0)
