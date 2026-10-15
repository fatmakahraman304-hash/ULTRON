"""Real listening handlers, desktop dispatcher and completion wire with synthetic
Ollama/DB/lease objects. No Qt startup, secrets, hardware or provider calls.
"""
import ast
import asyncio
import __future__
import json
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from aiohttp import web
from integration import local_cloud_brain as local
from ultron.backend.cloud_client import CloudClient, CloudDeliveryRejected
from local_listening_bridge import post_local_listening_analysis, get_local_listening_analysis
from test_local_listening_bridge import FakePool, FakeRequest
from test_local_listening_qwen import Settings

ROOT=Path(__file__).resolve().parents[2]


def real_handler(file, name, namespace):
    # Compile the actual handler body without booting the desktop app or
    # importing the production DB/provider setup. No implementation is copied.
    tree=ast.parse((ROOT/file).read_text(encoding='utf8'))
    function=next(node for node in ast.walk(tree)
                  if isinstance(node,ast.AsyncFunctionDef) and node.name==name)
    module=ast.Module(body=[function],type_ignores=[])
    exec(compile(module,str(ROOT/file),'exec',
                 flags=__future__.annotations.compiler_flag),namespace)
    return namespace[name]


class Lease:
    def __init__(self,*args,**kwargs):self.lost=asyncio.Event()
    async def run(self):await asyncio.Event().wait()


class RoundtripPool(FakePool):
    def __init__(self):
        super().__init__()
        self.row=None

    async def execute(self,sql,*args):
        result=await super().execute(sql,*args)
        if self.row and self.row['status']=='completed' and "payload=payload - 'text' - 'system'" in sql:
            self.row['payload'].pop('text',None)
            self.row['payload'].pop('system',None)
        return result

    async def fetchrow(self,sql,*args):
        if 'SELECT status,command' in sql:return dict(self.row)
        if 'UPDATE device_commands' in sql:
            self.row.update(status=args[0],result=json.loads(args[1]))
            return dict(self.row)
        if 'SELECT id,status,result,payload' in sql:return dict(self.row)
        result=await super().fetchrow(sql,*args)
        if 'INSERT INTO device_commands' in sql:
            self.row={'id':42,'payload':self.saved['payload'],'status':'queued',
                      'command':'agent_task','delivery_attempt':1,'retry_count':0,
                      'max_retries':0,'result':None}
        return result


class ListeningRoundtripTests(unittest.IsolatedAsyncioTestCase):
    async def test_map_reduce_final_completion_is_readable_after_desktop_report_and_scrub(self):
        complete=real_handler('ultron/cloud_service/app.py','complete_device_command',
                              {'web':web,'json':json,'_json_dumps':json.dumps})
        dispatch=real_handler('mark_app.py','_handle_cloud_remote_command',
                              {'asyncio':asyncio,'RemoteLeaseGuard':Lease,
                               'CloudDeliveryRejected':CloudDeliveryRejected})
        for stage in ('map','reduce','final'):
            with self.subTest(stage=stage):
                db=RoundtripPool()
                body={'stage':stage,'text':'Kaynak: bugün sade bir tasarım seçtim.',
                      'request_id':'123e4567-e89b-12d3-a456-426614174000'}
                if stage=='map':body.update(part=1,total=1)
                accepted=await post_local_listening_analysis(FakeRequest(body,db=db))
                self.assertEqual(accepted.status,202)
                db.row['status']='delivered'
                expected='😀'*5000 if stage=='final' else 'Karar: sade tasarım.'
                wire=[]

                class Client:
                    async def report_task_progress(self,*args,**kwargs):return {'ok':True}
                    async def local_listening_analysis(self,prompt,system,requested):
                        return local.local_listening_analysis(prompt,system,requested)
                    async def complete_task(self,*args,**kwargs):
                        return await CloudClient.complete_task(self,*args,**kwargs)
                    async def _request(self,method,path,json_body=None,**kwargs):
                        wire.append(json_body)
                        request=FakeRequest(json_body,kind='device',db=db)
                        response=await complete(request)
                        return json.loads(response.body)

                with patch.object(local,'_SETTINGS',Settings()), \
                     patch.object(local,'installed_models',return_value=['qwen3:4b']), \
                     patch.object(local,'_get_json',return_value={
                         'model':'qwen3:4b','done':True,'done_reason':'stop',
                         'message':{'content':expected}}) as inference:
                    await dispatch(SimpleNamespace(),Client(),dict(db.row))
                self.assertEqual(inference.call_count,1)
                self.assertEqual(len(wire),1)
                self.assertEqual(wire[0]['result']['stage'],stage)
                self.assertEqual(db.row['status'],'completed')
                self.assertNotIn('text',db.row['payload'])
                self.assertNotIn('system',db.row['payload'])
                for _ in range(2):
                    result=await get_local_listening_analysis(FakeRequest(db=db))
                    self.assertEqual(result.status,200)
                    value=json.loads(result.body)
                    self.assertEqual(value['status'],'completed')
                    self.assertEqual(value['stage'],stage)
                    self.assertEqual(value['analysis'],expected)
                    self.assertEqual(value['provider'],'local-ollama')


if __name__=='__main__':unittest.main()
