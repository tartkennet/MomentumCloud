"""Capital is derived after frozen membership; no capital-dependent selection."""
import copy
import math
from datetime import datetime
from quality_forward import NY, bootstrap, digest

CAPITAL_POLICY = 'TEN_WHOLE_SHARES_MINIMUM_V1'


def membership(rows):
    selected=[]
    for r in rows:
        if (r['ticker']=='SPY' or any(x['cik']==r['cik'] for x in selected) or
                sum(str(x['sic'])[:2]==str(r['sic'])[:2] for x in selected)>=2 or
                sum(x['division']==r['division'] for x in selected)>=4):continue
        selected.append(copy.deepcopy(r))
        if len(selected)==10:break
    return selected


def requirements(snapshot, fx):
    rows=membership((snapshot.get('selection') or {}).get('rows',[]))
    if len(rows)!=10:raise ValueError('TEN_INDIVIDUAL_STOCKS_REQUIRED')
    if not isinstance(fx,(int,float)) or not math.isfinite(fx) or fx<=0:raise ValueError('NO_VERIFIED_INITIAL_FX')
    for r in rows:
        price=snapshot.get('quotes',{}).get(r['ticker'])
        if not isinstance(price,(int,float)) or not math.isfinite(price) or price<=0:
            raise ValueError('MISSING_HELD_OR_TARGET_PRICE')
        r['price_usd']=price
        n=price*1.02
        r['one_share_cost_cents']=math.ceil((n+max(1,n*.0025)+n*.004)*fx*100)
    total=sum(r['one_share_cost_cents'] for r in rows)
    # Integer cents avoid a one-cent underestimate at a concentration boundary.
    minimum=max(total,max(r['one_share_cost_cents']*5 for r in rows),
        max((sum(x['one_share_cost_cents'] for x in rows if str(x['sic'])[:2]==str(r['sic'])[:2])*10+2)//3 for r in rows),
        max(sum(x['one_share_cost_cents'] for x in rows if x['division']==r['division'])*2 for r in rows))
    return dict(policy=CAPITAL_POLICY,targets=rows,minimum_one_each_sek=total/100,
                minimum_capital_sek=minimum/100,quotes_as_of=snapshot['quotes_as_of'],usdsek=fx)


def configure(prior, snapshot, report, now, fingerprint, requested=''):
    """Lock a funded start or an explicit owner's amount, once per new cohort.

    Legacy accounts with fills remain intact. An untraded legacy initialization
    is superseded, never edited; the complete predecessor must be archived.
    """
    if prior and (prior.get('capital_configuration') or
                  prior['strategy']['trades'] or prior['benchmark']['trades']):
        return copy.deepcopy(prior),None
    selection=snapshot.get('selection') or {}
    if not (snapshot.get('market_verified') and snapshot.get('selection_verified') and
            snapshot.get('coverage',0)>=.90 and report.get('risk_on') is True and
            snapshot.get('quotes_as_of')==report.get('price_as_of') and
            selection.get('month')==now.astimezone(NY).strftime('%Y-%m') and
            report.get('status')!='COLLECTION_FAILED' and not report.get('errors') and
            0<=(now-datetime.fromisoformat(report['generated_at'])).total_seconds()<1800):
        raise ValueError('CAPITAL_REQUIREMENTS_NOT_VERIFIED')
    funding=requirements(snapshot,(report.get('fx') or {}).get('usdsek'))
    if report['fx'].get('date','9999')>snapshot['quotes_as_of']:raise ValueError('NO_VERIFIED_INITIAL_FX')
    from audit_avanza10 import audit_funding
    audit_funding(snapshot,report['fx']['usdsek'],funding)
    if not requested or requested.strip().upper()=='AUTO_MINIMUM':
        mode='AUTO_MINIMUM';initial=funding['minimum_capital_sek']
    else:
        mode='EXPLICIT'
        try:initial=float(requested)
        except (ValueError,TypeError):raise ValueError('INVALID_INITIAL_CAPITAL') from None
        if not math.isfinite(initial) or initial<=0 or initial>1e9 or abs(initial*100-round(initial*100))>1e-5:
            raise ValueError('INVALID_INITIAL_CAPITAL')
    state=bootstrap(dict(initial_usd=initial/report['fx']['usdsek'],fx=report['fx']),fingerprint,now)
    config=dict(policy=CAPITAL_POLICY,mode=mode,initial_sek=initial,funding=funding,
                selection_sha256=digest(selection),configured_at=now.isoformat(),fx=report['fx'])
    state.update(initial_sek=initial,opening_quotes=[],valuation_fx={},trade_fx={},ranked_targets=[],
                 capital_configuration=config,cohort_id=digest(config))
    if prior:
        state['supersedes']=dict(sha256=digest(prior),initialized_at=prior['initialized_at'],
            initial_sek=prior['initial_sek'],reason='UNTRADED_LEGACY_CAPITAL_INITIALIZATION',
            archive='avanza-cohorts/'+digest(prior)+'.json')
    return state,copy.deepcopy(prior)


def validate_transition(old, new, archived):
    """Publication must prove preservation before allowing a fresh cash cohort."""
    assert not old['strategy']['trades'] and not old['benchmark']['trades']
    assert not old.get('capital_configuration')
    assert new['supersedes']['sha256']==digest(old)==digest(archived)
    assert new['supersedes']['archive']=='avanza-cohorts/'+digest(old)+'.json'
    assert all(not old[k]['shares'] and not old[k]['receivables'] for k in ('strategy','benchmark'))
    assert new['cohort_id']==digest(new['capital_configuration'])
    assert new['initialized_at']>old['initialized_at']
    assert new['capital_configuration']['configured_at']==new['initialized_at']
    for account in ('strategy','benchmark'):
        assert not new[account]['trades'] and not new[account]['equity'] and not new[account]['shares']
    assert all(d['created_at']>=new['initialized_at'] for d in new['decisions'])
    return True
