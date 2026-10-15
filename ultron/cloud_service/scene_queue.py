"""Read-only scene synthesis over existing fenced local Qwen worker.

No conversation, automatic learning, memory or tool invocation. Same owner cap
and lock as local chat. Retried POSTs reuse the same request ID and payload.
"""
import hashlib
import json
import uuid
from aiohttp import web
from scene_design import description, validate, SYSTEM
from local_reply_validation import _validated_local_reply as validated_local_reply

async def post_scene(request):
    if request.get('auth_kind')!='web':raise web.HTTPForbidden()
    try:
        body=await request.json();text=description(body);ident=str(uuid.UUID(body['request_id']))
    except (ValueError,TypeError,KeyError):return web.json_response({'error':'invalid_description'},status=400)
    digest=hashlib.sha256(text.encode()).hexdigest()
    async with request.app['db'].acquire() as conn:
        async with conn.transaction():
            await conn.execute('SELECT pg_advisory_xact_lock(hashtextextended($1::text,0))','ultron-local-chat:'+request['user_id'])
            previous=await conn.fetchrow("SELECT id,payload FROM device_commands WHERE user_id=$1 AND target='desktop' AND command='agent_task' AND payload->>'mode'='local_brain' AND payload->>'purpose'='scene_design' AND payload->>'request_id'=$2 ORDER BY id DESC LIMIT 1",request['user_id'],ident)
            if previous:
                p=previous['payload'];p=json.loads(p) if isinstance(p,str) else p
                if p.get('digest')!=digest:return web.json_response({'error':'request_id_conflict'},status=409)
                return web.json_response({'command_id':previous['id']},status=202)
            ready=await conn.fetchval("SELECT COALESCE(last_seen > NOW()-INTERVAL '15 seconds' AND state->'local_chat_ready'='true'::jsonb,FALSE) FROM device_presence WHERE user_id=$1 AND device='desktop'",request['user_id'])
            if not ready:return web.json_response({'error':'desktop_offline'},status=409)
            count=await conn.fetchval("SELECT COUNT(*) FROM device_commands WHERE user_id=$1 AND target='desktop' AND command='agent_task' AND payload->>'mode'='local_brain' AND status IN ('queued','delivered')",request['user_id'])
            if int(count or 0)>=3:return web.json_response({'error':'local_brain_busy'},status=429)
            row=await conn.fetchrow("INSERT INTO device_commands(user_id,target,command,payload,source_device,max_retries) VALUES($1,'desktop','agent_task',$2::jsonb,$3,0) RETURNING id",request['user_id'],json.dumps({'mode':'local_brain','purpose':'scene_design','text':'Create a 3D JSON assembly: '+text,'system':SYSTEM,'turns':[],'request_id':ident,'digest':digest}),request['device_id'])
    return web.json_response({'command_id':row['id']},status=202)

async def get_scene(request):
    if request.get('auth_kind')!='web':raise web.HTTPForbidden()
    try:
        ident=int(request.match_info['id'])
        if ident<1:raise ValueError()
    except (ValueError,TypeError):return web.json_response({'error':'invalid_id'},status=400)
    row=await request.app['db'].fetchrow("SELECT status,result FROM device_commands WHERE id=$1 AND user_id=$2 AND target='desktop' AND command='agent_task' AND payload->>'mode'='local_brain' AND payload->>'purpose'='scene_design'",ident,request['user_id'])
    if not row:return web.json_response({'error':'not_found'},status=404)
    if row['status']!='completed':return web.json_response({'status':row['status']})
    try:
        result=row['result'];result=json.loads(result) if isinstance(result,str) else result
        details=validated_local_reply(result)
        if details is None or result.get('provider')!='local-ollama':raise ValueError()
        design=validate(details[0])
    except (ValueError,TypeError):return web.json_response({'status':'failed','error':'invalid_local_reply'},status=502)
    return web.json_response({'status':'completed','reply':json.dumps(design)})
