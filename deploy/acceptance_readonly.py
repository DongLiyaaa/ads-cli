"""Import the owner's existing authorization and verify read-only job persistence."""
import argparse
import ast
import getpass
from datetime import datetime
import json
import os
from pathlib import Path
import re
import time
import httpx
from dotenv import dotenv_values

p=argparse.ArgumentParser()
p.add_argument('--credentials',required=True)
p.add_argument('--profile-id',required=True)
p.add_argument('--label',required=True)
p.add_argument('--report-date',required=True)
p.add_argument('--receipt',required=True)
args=p.parse_args()
datetime.strptime(args.report_date,'%Y-%m-%d')
config=dotenv_values('.env')
values={}
for key,value in re.findall(r'^\s*(client_id|client_secret|refresh_token|profile_id)\s*:\s*(.*?)\s*$',Path(args.credentials).read_text(),re.M):
    if value.startswith(('"',"'")):value=ast.literal_eval(value)
    values[key]=str(value)
assert all(values.get(k) for k in ('client_id','client_secret','refresh_token'))
base=config['ADS_PUBLIC_ORIGIN']
client=httpx.Client(base_url=base,timeout=90)
# Accounts created on the setup page are not in .env, so prompt for them.
username=config.get('ADS_ADMIN_USERNAME') or input('Admin username: ')
password=config.get('ADS_ADMIN_PASSWORD') or getpass.getpass('Admin password: ')
response=client.post('/api/login',headers={'Origin':base},json={'username':username,'password':password})
response.raise_for_status()
headers={'Origin':base,'X-CSRF-Token':response.json()['csrf_token']}
accounts=client.get('/api/accounts').json()
account=next((a for a in accounts if a['marketplace']=='US' and a['profile_id']==args.profile_id),None)
if account is None:
    body={k:values[k] for k in ('client_id','client_secret','refresh_token')}
    body.update(label=args.label,profile_id=args.profile_id,marketplace='US',region='NA')
    response=client.post('/api/accounts',headers=headers,json=body);response.raise_for_status();account=response.json()
for attempt in range(3):
    response=client.post('/api/accounts/'+account['id']+'/verify',headers=headers,json={})
    if response.is_success:break
    if attempt==2:raise RuntimeError('Account verification failed; inspect redacted service logs')
    time.sleep(3)
print(json.dumps({'account_id':account['id'],'marketplace':'US','authorization_verified':True}),flush=True)
jobs=[]
for endpoint,operation,arguments,key in [
    ('queries','campaigns.list',{},'deployment-20261014-read-campaigns'),
    ('reports','reports.create-sp-campaign-placement',{'start_date':args.report_date,'end_date':args.report_date,'time_unit':'DAILY'},'deployment-20261014-read-report')]:
    response=client.post('/api/'+endpoint,headers=headers,json={'account_id':account['id'],'operation':operation,'arguments':arguments,'idempotency_key':key})
    response.raise_for_status();jobs.append(response.json()['id'])
receipt={'account_id':account['id'],'marketplace':'US','report_date':args.report_date,'tasks':[],'real_ad_mutations':0}
os.umask(0o077)
target=Path(args.receipt);target.parent.mkdir(parents=True,exist_ok=True)
deadline=time.monotonic()+600
last={}
while time.monotonic()<deadline:
    records=[]
    for task_id in jobs:
        response=client.get('/api/tasks/'+task_id);response.raise_for_status();t=response.json()
        record={k:t.get(k) for k in ('id','operation','kind','status','row_count','remote_status','error')}
        if t['status']=='SUCCEEDED':
            result=client.get('/api/tasks/'+task_id+'/rows?limit=1').json();record['saved_records']=result['total']
        if last.get(task_id)!=t['status']:print(json.dumps(record,ensure_ascii=False),flush=True)
        last[task_id]=t['status'];records.append(record)
    receipt['tasks']=records;target.write_text(json.dumps(receipt,ensure_ascii=False,indent=2))
    if all(r['status'] in ('SUCCEEDED','FAILED','PARTIAL','UNKNOWN','CANCELLED') for r in records):break
    time.sleep(10)
client.post('/api/logout',headers=headers,json={})
if not all(r['status']=='SUCCEEDED' for r in receipt['tasks']):
    raise SystemExit('Read-only validation not complete; jobs remain persisted for inspection')
print(json.dumps({'read_only_validation':'passed','receipt':str(target)}),flush=True)
