"""BEST-only completed-session adapter; existing accounts are not modified."""
from datetime import timedelta,time
import time as clock
import requests
from quality_forward import NY
from quality_sources import Provider,DataUnavailable
from collect_quality import extend_events
from run_core_risk_research import make_data
from research_core_actions import supplement
from research_momentum10_fx import ReferenceFX
from momentum_core_data import read_json


class BestProvider(Provider):
    def get(self,*args,**kwargs):
        for attempt in range(3):
            try:return super().get(*args,**kwargs)
            except DataUnavailable as exc:
                if str(exc) not in ('HTTP_429','HTTP_502','HTTP_503','HTTP_504') or attempt==2:raise
                clock.sleep(2**attempt)
    def _get(self,*args,**kwargs):return self.get(*args,**kwargs)


def completed_end(now):
    local=now.astimezone(NY)
    return (local.date() if local.weekday()<5 and local.time().replace(tzinfo=None)>=time(16,15)
            else local.date()-timedelta(days=1)).isoformat()


def data_for(cache,now):
    import run_core_risk_research as adapter
    client=BestProvider();end=completed_end(now)
    extend_events(cache,now.astimezone(NY).date().isoformat(),client)
    adapter.PolygonClient=lambda key:client
    data=supplement(make_data(cache,end,False))
    for kind,column in [('splits','execution_date'),('dividends','ex_dividend_date')]:
        paths=sorted(cache.glob(kind+'-*-v1.json.gz'));rows=read_json(paths[-1]);setattr(data.source,kind,rows)
        groups={}
        for event in rows:groups.setdefault(event[column],[]).append(event)
        setattr(data,kind+'_by_day',groups)
    response=requests.get('https://www.ecb.europa.eu/stats/eurofxref/eurofxref-hist-90d.xml',timeout=(3,10))
    if response.status_code!=200:raise DataUnavailable('FX_HTTP_'+str(response.status_code))
    path=cache/'best-fx.xml';path.write_bytes(response.content);data.native_usd=ReferenceFX(path).usd
    return data,client
