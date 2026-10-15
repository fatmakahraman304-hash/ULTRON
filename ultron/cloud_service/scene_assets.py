"""Public CC0 Poly Haven catalogue and bounded geometry-only GLB import.

Only fixed API/download origins; never fetch user URLs or follow redirects.
Textures are intentionally omitted: the scene uses its own hologram material.
"""
import asyncio
import json
import re
import struct
import time
import threading
import unicodedata
from urllib.parse import urlsplit
import urllib.request
from aiohttp import web

MAX_BYTES=30*1024*1024
_catalog=(0,{})
_download_gate=threading.BoundedSemaphore(2)
class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):raise ValueError('asset_redirect_rejected')

def read_url(url,limit,timeout=25):
    parsed=urlsplit(url)
    if parsed.scheme!='https' or parsed.netloc not in ('api.polyhaven.com','dl.polyhaven.org') or parsed.username or parsed.fragment:
        raise ValueError('asset_origin_rejected')
    if parsed.netloc=='dl.polyhaven.org' and not parsed.path.startswith('/file/ph-assets/Models/'):
        raise ValueError('asset_path_rejected')
    request=urllib.request.Request(url,headers={'User-Agent':'Golge-Scene/1.0','Accept':'application/json,application/octet-stream'})
    with urllib.request.build_opener(NoRedirect()).open(request,timeout=timeout) as response:
        data=response.read(limit+1)
    if len(data)>limit:raise ValueError('asset_too_large')
    return data

def catalog():
    global _catalog
    if time.monotonic()-_catalog[0]<3600 and _catalog[1]:return _catalog[1]
    data=json.loads(read_url('https://api.polyhaven.com/assets?t=models',4*1024*1024))
    if not isinstance(data,dict) or len(data)>10000:raise ValueError('invalid_catalog')
    _catalog=(time.monotonic(),data);return data

def norm(text):
    text=unicodedata.normalize('NFD',str(text).lower().replace('ı','i'))
    return re.sub(r'[^a-z0-9 ]',' ',''.join(c for c in text if not unicodedata.combining(c)))

# Translate common object words, never pin an object to a fixed asset ID.
WORDS={'sandalye':'chair','koltuk':'armchair','ucak':'airplane','gemi':'ship','insan':'person','masa':'table','sehpa':'table','ev':'house','agac':'tree','tas':'rock','kaya':'rock','araba':'car','arac':'car','motor':'engine','lamba':'lamp','isik':'light','kapi':'door','pencere':'window','dolap':'cabinet','kitap':'book','kitaplik':'bookshelf','bardak':'glass','sise':'bottle','tabak':'plate','kase':'bowl','cicek':'flower','saksi':'pot','bitki':'plant','yatak':'bed','bank':'bench','kutu':'box','varil':'barrel','tekerlek':'wheel','lastik':'tire','heykel':'statue','canta':'bag','ayakkabi':'shoe','telefon':'phone','bilgisayar':'computer','kamera':'camera','alet':'tool','cekic':'hammer','saat':'clock','merdiven':'stairs','catal':'fork','kasik':'spoon','bicak':'knife','yastik':'pillow','ahsap':'wood','metal':'metal','eski':'old','modern':'modern','yuvarlak':'round'}
STOP={'bir','bana','lutfen','model','modeli','modelini','3d','3b','internetten','webden','bul','getir','indir','ve'}
def search(query):
    tokens=[WORDS.get(w,w) for w in norm(query).split() if w not in STOP]
    if not tokens:return []
    results=[]
    for ident,asset in catalog().items():
        if not re.fullmatch(r'[A-Za-z0-9_-]{1,100}',ident) or not isinstance(asset,dict) or asset.get('type')!=2:continue
        title=str(asset.get('name',''))[:150]
        words=set(norm(title+' '+' '.join(asset.get('tags',[]))+' '+' '.join(asset.get('categories',[]))).split())
        if 'arm' in words and 'chair' in words:words.add('armchair')
        # Require every significant word: never substitute unrelated search results.
        if not all(any(w in (t,t+'s',t+'es') or t in (w+'s',w+'es') for w in words) for t in tokens):continue
        score=sum(3 if t in norm(title).split() else 1 for t in tokens)
        results.append((score,{'id':ident,'name':title,'source':'https://polyhaven.com/a/'+ident,'license':'CC0-1.0','authors':', '.join(asset.get('authors',{}))[:300]}))
    return [r for _,r in sorted(results,key=lambda r:(-r[0],r[1]['id']))[:5]]

def pack_gltf(document,buffers):
    """Embed bounded buffers, removing any texture or extension resource paths."""
    if not isinstance(document,dict) or document.get('asset',{}).get('version')!='2.0' or document.get('extensionsRequired') or document.get('skins'):
        raise ValueError('unsupported_gltf')
    if not 1<=len(buffers)<=16 or len(document.get('buffers',[]))!=len(buffers):raise ValueError('invalid_buffers')
    binary=bytearray();offsets=[]
    for spec,data in zip(document['buffers'],buffers):
        if type(spec.get('byteLength')) is not int or spec['byteLength']!=len(data):raise ValueError('invalid_buffer_length')
        offsets.append(len(binary));binary.extend(data);binary.extend(b'\0'*((-len(binary))%4))
        if len(binary)>MAX_BYTES:raise ValueError('asset_too_large')
    for view in document.get('bufferViews',[]):
        index=view.get('buffer');start=view.get('byteOffset',0);length=view.get('byteLength')
        if type(index) is not int or not 0<=index<len(buffers) or type(start) is not int or type(length) is not int or start<0 or length<0 or start+length>len(buffers[index]):raise ValueError('invalid_buffer_view')
        view['buffer']=0;view['byteOffset']=offsets[index]+start
    for key in ('images','textures','samplers','materials','animations'):document.pop(key,None)
    def strip(obj):
        if isinstance(obj,dict):
            for key in ('extensions','extras','extensionsUsed','extensionsRequired'):obj.pop(key,None)
            for value in obj.values():strip(value)
        elif isinstance(obj,list):
            for value in obj:strip(value)
    strip(document)
    for mesh in document.get('meshes',[]):
        for primitive in mesh.get('primitives',[]):primitive.pop('material',None)
    document['buffers']=[{'byteLength':len(binary)}]
    encoded=json.dumps(document,separators=(',',':')).encode();encoded+=b' '*((-len(encoded))%4)
    size=28+len(encoded)+len(binary)
    if size>MAX_BYTES:raise ValueError('asset_too_large')
    return struct.pack('<III',0x46546c67,2,size)+struct.pack('<II',len(encoded),0x4e4f534a)+encoded+struct.pack('<II',len(binary),0x004e4942)+binary

def _download(ident):
    deadline=time.monotonic()+60
    def fetch(url,limit):
        remaining=deadline-time.monotonic()
        if remaining<=0:raise ValueError("asset_deadline")
        return read_url(url,limit,min(25,remaining))
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,100}',ident) or ident not in catalog():raise ValueError('unknown_asset')
    files=json.loads(fetch('https://api.polyhaven.com/files/'+ident,2*1024*1024))
    choices=files.get('gltf',{});item=next((choices[k]['gltf'] for k in ('1k','2k','4k') if k in choices and 'gltf' in choices[k]),None)
    if not item:raise ValueError('gltf_unavailable')
    doc=json.loads(fetch(item['url'],2*1024*1024));buffers=[];remaining=MAX_BYTES
    if not isinstance(doc.get('buffers'),list) or not 1<=len(doc['buffers'])<=16:raise ValueError('invalid_buffers')
    for spec in doc['buffers']:
        uri=spec.get('uri');entry=item.get('include',{}).get(uri)
        if not isinstance(uri,str) or not entry or type(entry.get('size')) is not int or not 0<entry['size']<=remaining:raise ValueError('invalid_buffer_source')
        data=fetch(entry['url'],min(entry['size'],remaining));remaining-=len(data);buffers.append(data)
    return pack_gltf(doc,buffers)

def download(ident):
    if not _download_gate.acquire(blocking=False):raise ValueError('asset_busy')
    try:return _download(ident)
    finally:_download_gate.release()

async def search_assets(request):
    query=request.query.get('query','').strip()
    if not 1<=len(query)<=160:return web.json_response({'error':'invalid_query'},status=400)
    try:items=await asyncio.to_thread(search,query)
    except Exception:return web.json_response({'error':'asset_search_unavailable'},status=502)
    return web.json_response({'items':items})

async def asset_file(request):
    try:data=await asyncio.to_thread(download,request.match_info['id'])
    except Exception:return web.json_response({'error':'asset_download_unavailable'},status=502)
    return web.Response(body=data,content_type='model/gltf-binary',headers={'Cache-Control':'private, no-store'})

def register(app):
    app.router.add_get('/api/scene-assets',search_assets)
    app.router.add_get('/api/scene-assets/{id}',asset_file)
