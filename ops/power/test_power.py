import importlib.util
import sys
import types
import unittest
sys.modules['boto3']=types.ModuleType('boto3')
spec=importlib.util.spec_from_file_location('power','power.py')
power=importlib.util.module_from_spec(spec);spec.loader.exec_module(power)
def change(address,actions):
 return {'address':address,'mode':'managed','change':{'actions':actions}}
class GuardTests(unittest.TestCase):
 def test_retained_data_cannot_be_deleted(self):
  for addr in ['module.s3.aws_s3_bucket.documents','module.dynamodb.aws_dynamodb_table.standards','module.cognito.aws_cognito_user_pool.this','module.ecs.aws_ecr_repository.backend','module.kms.aws_kms_key.main']:
   with self.assertRaises(RuntimeError):power.check_plan({'resource_changes':[change(addr,['delete'])]})
 def test_ecs_service_definition_cannot_be_destroyed(self):
  with self.assertRaises(RuntimeError):power.check_plan({'resource_changes':[change('module.ecs.aws_ecs_service.app',['delete','create'])]})
 def test_exact_expensive_resources_allowed(self):
  items=[change('module.ecs.aws_lb.main[0]',['delete']),change('module.vpc.aws_nat_gateway.main[0]',['delete']),change('module.knowledge_base.aws_opensearchserverless_collection.kb[0]',['delete']),change('module.ecs.aws_ecs_service.app',['update'])]
  self.assertEqual(len(power.check_plan({'resource_changes':items})),4)
 def test_off_without_execute_never_touches_aws(self):
  p=object.__new__(power.Power)
  with self.assertRaises(RuntimeError):p.off(False)
 def test_on_without_execute_never_touches_aws(self):
  p=object.__new__(power.Power)
  with self.assertRaises(RuntimeError):p.on(False)
if __name__=='__main__':unittest.main()
