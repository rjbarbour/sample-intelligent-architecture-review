"""ACR selective power control. Default is PLAN_OFF; preparation never applies."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import boto3

REGION='us-east-1'
ACCOUNT='551828031976'
EXECUTION_ENABLED=False  # Staged only: IAM approval and recovery validation still required.
BUCKET='arch-review-deploy-551828031976-us-east-1'
STATE='dev/terraform.tfstate'
JOURNAL='power/restore.json'
CLUSTER='arch-review-dev-cluster'
SERVICES=['arch-review-dev-service','arch-review-dev-pptx-converter']
BASE=Path(__file__).resolve().parent
INFRA=BASE/'infrastructure'
TARGETS=[
 'module.ecs.aws_ecs_service.app','module.ecs.aws_ecs_service.pptx_converter',
 'module.ecs.aws_appautoscaling_target.ecs',
 'module.ecs.aws_lb.main','module.ecs.aws_lb_listener.http','module.ecs.aws_lb_listener.https',
 'module.ecs.aws_lb_listener_rule.verified_origin_http','module.ecs.aws_lb_listener_rule.verified_origin_https',
 'module.vpc.aws_nat_gateway.main','module.vpc.aws_eip.nat','module.vpc.aws_route_table.private',
 'module.knowledge_base.aws_opensearchserverless_collection.kb',
 'module.knowledge_base.null_resource.kb_index_bootstrap',
 'module.knowledge_base.aws_bedrockagent_knowledge_base.main',
 'module.knowledge_base.aws_bedrockagent_data_source.s3',
]
MUTABLE=set(TARGETS+['module.cloudfront.aws_cloudfront_distribution.frontend'])

def canonical(addr):
 return addr.replace('[0]','')

def check_plan(plan):
 changes=[]
 for r in plan.get('resource_changes',[]):
  actions=r['change']['actions']
  if r.get('mode')=='data' or actions==['no-op']:continue
  a=canonical(r['address'])
  if a not in MUTABLE:raise RuntimeError('Plan touches retained resource: '+r['address'])
  if a in {'module.ecs.aws_ecs_service.app','module.ecs.aws_ecs_service.pptx_converter','module.ecs.aws_appautoscaling_target.ecs','module.vpc.aws_route_table.private','module.cloudfront.aws_cloudfront_distribution.frontend'} and actions!=['update']:
   raise RuntimeError('Retained resource would be replaced/deleted: '+a)
  changes.append({'address':r['address'],'actions':actions})
 return changes

class Power:
 def __init__(self):
  self.session=boto3.Session(region_name=REGION)
  self.clients={}
  if self.client('sts').get_caller_identity()['Account']!=ACCOUNT:raise RuntimeError('Wrong AWS account')
 def client(self,name):
  if name not in self.clients:self.clients[name]=self.session.client(name)
  return self.clients[name]
 def tf(self,*args):
  p=subprocess.run(['terraform',*args],cwd=INFRA,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
  # Terraform output is private: plans/state can include origin-authentication material.
  if p.returncode:raise RuntimeError('Terraform failed: '+p.stdout[-3000:])
  return p.stdout
 def init(self):
  self.tf('init','-input=false',f'-backend-config=bucket={BUCKET}',f'-backend-config=key={STATE}',f'-backend-config=region={REGION}','-backend-config=use_lockfile=true')
  self.tf('validate')
 def services(self):
  out=self.client('ecs').describe_services(cluster=CLUSTER,services=SERVICES)
  if out['failures'] or len(out['services'])!=2:raise RuntimeError('Expected two ACR services')
  return out['services']
 def status(self):
  return [{'name':s['serviceName'],'desired':s['desiredCount'],'running':s['runningCount'],'pending':s['pendingCount']} for s in self.services()]
 def journal(self):
  try:
   with self.client('s3').get_object(Bucket=BUCKET,Key=JOURNAL)['Body'] as b:return json.loads(b.read())
  except self.client('s3').exceptions.NoSuchKey:return None
 def save(self,j):
  self.client('s3').put_object(Bucket=BUCKET,Key=JOURNAL,Body=json.dumps(j).encode(),ServerSideEncryption='AES256')
 def snapshot(self):
  ss=self.services()
  tasks={s['serviceName']:self.client('ecs').describe_task_definition(taskDefinition=s['taskDefinition'])['taskDefinition'] for s in ss}
  scales=self.client('application-autoscaling').describe_scalable_targets(ServiceNamespace='ecs',ResourceIds=[f'service/{CLUSTER}/{SERVICES[0]}'])['ScalableTargets']
  return {'phase':'captured','services':[{k:s[k] for k in ['serviceName','desiredCount','taskDefinition']} for s in ss], 'tasks':tasks,'scaling':scales}
 def idle(self):
  db=self.session.resource('dynamodb').meta.client
  active={'pending','in_progress','running','processing','parsing','extracting','syncing','analyzing'}
  # Conservative: pending document sync also blocks shutdown.
  for table in ['arch-review-dev-documents','arch-review-dev-validations','arch-review-dev-chat-jobs']:
   for page in db.get_paginator('scan').paginate(TableName=table,ConsistentRead=True):
    for row in page.get('Items',[]):
     if any(str(row.get(k,'')).lower() in active for k in ['status','sync_status']):raise RuntimeError('Active/pending work in '+table+'; shutdown deferred')
 def ensure_no_deploy(self):
  cb=self.client('codebuild')
  ids=cb.list_builds_for_project(projectName='arch-review-deploy',sortOrder='DESCENDING')['ids'][:20]
  if ids:
   if any(b['buildStatus']=='IN_PROGRESS' for b in cb.batch_get_builds(ids=ids)['builds']):raise RuntimeError('Deployment in progress; retry after it finishes')
 def plan(self,on):
  args=['plan','-input=false','-lock=false','-var-file=tfvars/dev.tfvars',f'-var=power_on={str(on).lower()}','-out=/tmp/power.tfplan']
  targets=TARGETS+(['module.cloudfront.aws_cloudfront_distribution.frontend'] if on else [])
  self.tf(*args,*['-target='+t for t in targets])
  p=json.loads(self.tf('show','-json','/tmp/power.tfplan'))
  changes=check_plan(p)
  print(json.dumps({'mode':'ON' if on else 'OFF','changes':changes},indent=2))
  return p
 def off(self,confirmed):
  if not confirmed:raise RuntimeError('OFF requires --execute; no changes made')
  self.ensure_no_deploy()
  j=self.journal()
  if j and j['phase']!='on':raise RuntimeError('Existing unfinished power cycle; use ON to recover before another OFF')
  self.idle()
  j=self.snapshot()
  # Backup Terraform state privately before any infrastructure mutation.
  self.client('s3').copy_object(Bucket=BUCKET,Key=f'power/backups/{int(time.time())}.tfstate',CopySource={'Bucket':BUCKET,'Key':STATE},ServerSideEncryption='AES256')
  self.save(j)
  scale=self.client('application-autoscaling')
  for s in j['scaling']:
   scale.register_scalable_target(ServiceNamespace='ecs',ResourceId=s['ResourceId'],ScalableDimension=s['ScalableDimension'],MinCapacity=0,MaxCapacity=0,SuspendedState={'DynamicScalingInSuspended':True,'DynamicScalingOutSuspended':True,'ScheduledScalingSuspended':True})
  # User must stop submitting new work before OFF; scan is a conservative additional guard.
  self.idle()
  for s in SERVICES:self.client('ecs').update_service(cluster=CLUSTER,service=s,desiredCount=0)
  self.client('ecs').get_waiter('services_stable').wait(cluster=CLUSTER,services=SERVICES,WaiterConfig={'Delay':10,'MaxAttempts':90})
  if any(s['running'] or s['pending'] for s in self.status()):raise RuntimeError('Tasks not stopped')
  j['phase']='tasks-stopped';self.save(j)
  # ALB deletion protection is disabled only during an explicit OFF execution.
  lbs=self.client('elbv2').describe_load_balancers(Names=['arch-review-dev-alb'])['LoadBalancers']
  self.client('elbv2').modify_load_balancer_attributes(LoadBalancerArn=lbs[0]['LoadBalancerArn'],Attributes=[{'Key':'deletion_protection.enabled','Value':'false'}])
  self.plan(False)
  self.tf('apply','-input=false','/tmp/power.tfplan')
  j['phase']='off';self.save(j)
  print('OFF complete; retained data and identities are unchanged.')
 def on(self,confirmed):
  if not confirmed:raise RuntimeError('ON requires --execute; no changes made')
  self.ensure_no_deploy()
  j=self.journal()
  if not j:raise RuntimeError('No restore journal; refusing to guess previous settings')
  if j['phase']=='on':print(json.dumps(self.status()));return
  self.plan(True)
  self.tf('apply','-input=false','/tmp/power.tfplan')
  outputs=json.loads(self.tf('output','-json'))
  # Module outputs are obtained from state so no assumption about root output names is needed.
  state=json.loads(self.tf('state','pull'))
  def attrs(typ,name,module):
   return next(r for r in state['resources'] if r['type']==typ and r['name']==name and r.get('module')==module)['instances'][0]['attributes']
  kb=attrs('aws_bedrockagent_knowledge_base','main','module.knowledge_base')['id']
  ds=attrs('aws_bedrockagent_data_source','s3','module.knowledge_base')['data_source_id']
  bedrock=self.client('bedrock-agent')
  job=bedrock.start_ingestion_job(knowledgeBaseId=kb,dataSourceId=ds)['ingestionJob']['ingestionJobId']
  deadline=time.monotonic()+3600
  while time.monotonic()<deadline:
   status=bedrock.get_ingestion_job(knowledgeBaseId=kb,dataSourceId=ds,ingestionJobId=job)['ingestionJob']['status']
   if status=='COMPLETE':break
   if status in ['FAILED','STOPPED']:raise RuntimeError('Knowledge Base ingestion '+status)
   time.sleep(15)
  else:raise RuntimeError('Knowledge Base ingestion timed out')
  ecs=self.client('ecs')
  allowed=ecs.meta.service_model.operation_model('RegisterTaskDefinition').input_shape.members
  for s in j['services']:
   td={k:v for k,v in j['tasks'][s['serviceName']].items() if k in allowed}
   for c in td['containerDefinitions']:
    for e in c.get('environment',[]):
     if e['name']=='KNOWLEDGE_BASE_ID':e['value']=kb
     if e['name']=='DATA_SOURCE_ID':e['value']=ds
   arn=ecs.register_task_definition(**td,tags=[{'key':'Project','value':'arch-review'},{'key':'Environment','value':'dev'}])['taskDefinition']['taskDefinitionArn']
   ecs.update_service(cluster=CLUSTER,service=s['serviceName'],taskDefinition=arn,desiredCount=s['desiredCount'])
  ecs.get_waiter('services_stable').wait(cluster=CLUSTER,services=SERVICES,WaiterConfig={'Delay':15,'MaxAttempts':80})
  for s in j['scaling']:
   self.client('application-autoscaling').register_scalable_target(**{k:s[k] for k in ['ServiceNamespace','ResourceId','ScalableDimension','MinCapacity','MaxCapacity','SuspendedState']})
  tg=attrs('aws_lb_target_group','app','module.ecs')['arn']
  self.client('elbv2').get_waiter('target_in_service').wait(TargetGroupArn=tg,WaiterConfig={'Delay':15,'MaxAttempts':40})
  j['phase']='on';self.save(j)
  print('ON complete; original image/model settings restored, index rebuilt and ALB targets healthy.')

def main():
 p=argparse.ArgumentParser();p.add_argument('action',choices=['STATUS','PLAN_OFF','PLAN_ON','OFF','ON']);p.add_argument('--execute',action='store_true');a=p.parse_args()
 if a.action in ['OFF','ON'] and not EXECUTION_ENABLED:
  raise RuntimeError('Execution is staged and disabled pending IAM approval; use PLAN_OFF/PLAN_ON/STATUS')
 power=Power()
 if a.action=='STATUS':print(json.dumps(power.status()));return
 power.init()
 if a.action.startswith('PLAN_'):power.plan(a.action=='PLAN_ON')
 elif a.action=='OFF':power.off(a.execute)
 else:power.on(a.execute)

if __name__=='__main__':
 main()
