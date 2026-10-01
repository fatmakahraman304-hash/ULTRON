"""Read-only weather and local ICS connectors with bounded HTTP requests."""
import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, quote, urlsplit
from urllib.request import Request, urlopen

class ConnectorError(Exception):
    pass


def _http_get(url, timeout_s=10, max_bytes=2_000_000):
    if urlsplit(url).scheme not in ('http','https'):
        raise ConnectorError('Only HTTP(S) URLs are supported')
    try:
        try:
            response=urlopen(Request(url,headers={'User-Agent':'MARK-ULTRON/1'}),timeout=timeout_s)
        except HTTPError as exc:
            response=exc
        with response:
            data=response.read(max_bytes+1)
            if len(data)>max_bytes:
                raise ConnectorError('HTTP response exceeds size limit')
            return {'status':response.status,'body':data.decode('utf-8',errors='replace')}
    except (OSError,URLError,ValueError) as exc:
        # Do not include the URL: query parameters may contain credentials.
        raise ConnectorError('HTTP request failed: '+type(exc).__name__) from None

class WeatherConnector:
    def __init__(self,vault=None,owm_base='https://api.openweathermap.org/data/2.5',wttr_base='https://wttr.in'):
        self.vault=vault;self.owm_base=owm_base;self.wttr_base=wttr_base
    def health(self):
        return {'ok':True,'configured':bool(self.vault and self.vault.get('openweathermap')),'fallback':'wttr.in'}
    def current(self,city):
        if not isinstance(city,str) or not re.fullmatch(r"[\w .,'-]{1,100}",city):
            raise ConnectorError('Invalid city')
        key=self.vault.get('openweathermap') if self.vault else None
        if key:
            result=_http_get(self.owm_base.rstrip('/')+'/weather?'+urlencode({'q':city,'appid':key,'units':'metric','lang':'tr'}))
            if result['status']!=200: raise ConnectorError('Weather service HTTP '+str(result['status']))
            try:
                data=json.loads(result['body'])
                return {'source':'openweathermap','city':data.get('name',city),'temp_c':data['main']['temp'],'humidity':data['main'].get('humidity'),'description':data.get('weather',[{}])[0].get('description','')}
            except (ValueError,KeyError,IndexError,TypeError) as exc:
                raise ConnectorError('Invalid weather response') from exc
        result=_http_get(self.wttr_base.rstrip('/')+'/'+quote(city,safe='')+'?format=j1')
        if result['status']!=200: raise ConnectorError('Weather fallback unavailable')
        try:
            current=json.loads(result['body'])['current_condition'][0]
            return {'source':'wttr.in','city':city,'temp_c':float(current['temp_C']),'description':current['weatherDesc'][0]['value']}
        except (ValueError,KeyError,IndexError,TypeError) as exc:
            raise ConnectorError('Invalid weather response') from exc

class CalendarConnector:
    def __init__(self,ics_dir='data/calendar'):
        self.ics_dir=Path(ics_dir)
    def health(self):
        return {'ok':True,'ics_files':len(list(self.ics_dir.glob('*.ics'))),'outlook_com_available':False}
    def events(self,days=7):
        now=datetime.now().astimezone();end=now+timedelta(days=max(0,min(int(days),366)))
        result=[]
        for path in self.ics_dir.glob('*.ics'):
            text=path.read_text(encoding='utf-8-sig')
            text=re.sub(r'\r?\n[ \t]','',text)
            for block in text.split('BEGIN:VEVENT')[1:]:
                fields={}
                for line in block.split('END:VEVENT',1)[0].splitlines():
                    key,sep,value=line.partition(':')
                    if sep: fields[key.split(';')[0]]=value
                raw=fields.get('DTSTART','')
                try:
                    start=datetime.strptime(raw.rstrip('Z'),'%Y%m%dT%H%M%S' if 'T' in raw else '%Y%m%d')
                    start=start.replace(tzinfo=timezone.utc) if raw.endswith('Z') else start.astimezone()
                except ValueError:
                    continue
                if now <= start <= end:
                    result.append({'summary':fields.get('SUMMARY',''),'location':fields.get('LOCATION',''),'start':start.isoformat()})
        return sorted(result,key=lambda event:event['start'])
