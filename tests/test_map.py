import pytest

from eleicoes_sp.map_api import GEO,catalog,map_data
from eleicoes_sp.query import connection

pytestmark=pytest.mark.skipif(not (GEO/'catalog.json').exists(),reason='Malhas não preparadas')

def test_municipality_bridge_and_regions_cover_state():
    c=catalog()
    assert len(c['municipalities'])==645
    assert len({m['ibge'] for m in c['municipalities']})==645
    assert len(c['regions'])==11 and len(c['immediate_regions'])==53

def test_multicity_totals_and_candidate_denominator():
    with connection() as con:
        first=map_data(con,1,1,'municipality',municipalities=[71072])
        second=map_data(con,1,1,'municipality',municipalities=[62910])
        both=map_data(con,1,1,'municipality',municipalities=[71072,62910])
        assert both['total']==first['total']+second['total']
        candidate=first['candidates'][0]['candidate_id']
        selected=map_data(con,1,1,'municipality',municipalities=[71072],candidate_ids=[candidate])
        assert selected['total']==first['total']
        assert selected['areas'][0]['others']>0
        for area in both['areas']+selected['areas']:
            assert sum(area['votes'].values())+area['others']==area['total']

def test_multineighborhood_selection_matches_original_aggregates():
    with connection() as con:
        keys=['71072|VILA MARIANA','71072|IPIRANGA']
        result=map_data(con,1,1,'neighborhood',municipalities=[71072],neighborhoods=keys)
        assert {a['key'] for a in result['areas']}==set(keys)
        expected=con.execute("SELECT sum(votes) FROM summary_neighborhood WHERE office=1 AND round=1 AND municipality=71072 AND neighborhood IN ('VILA MARIANA','IPIRANGA')").fetchone()[0]
        assert result['total']==expected
        for a in result['areas']:assert sum(a['votes'].values())+a['others']==a['total']

def test_region_filter_is_an_intersection_with_cities():
    with connection() as con:
        city=next(m for m in catalog()['municipalities'] if m['municipality']==71072)
        good=map_data(con,1,1,'municipality',municipalities=[71072],regions=[city['region']])
        bad=map_data(con,1,1,'municipality',municipalities=[71072],regions=['invalid'])
        assert good['total']>0 and bad['total']==0

def test_hover_top_five_uses_full_national_totals_and_filters_candidates():
    from eleicoes_sp.national import REFERENCE
    if not REFERENCE.exists():pytest.skip('Referência nacional não importada')
    with connection() as con:
        args=dict(municipalities=[71072],neighborhoods=['71072|VILA MARIANA'])
        original=map_data(con,1,1,'neighborhood',**args)
        ranking=original['areas'][0]['top_five']
        assert len(ranking)==5
        assert [c['position'] for c in ranking]==[1,2,3,4,5]
        assert all(ranking[i]['votes']>=ranking[i+1]['votes'] for i in range(4))
        selected=map_data(con,1,1,'neighborhood',candidate_ids=[ranking[-1]['candidate_id']],**args)
        assert selected['areas'][0]['top_five']==[dict(ranking[-1],position=1)]
        all_ids=[r[0] for r in con.execute('SELECT candidate_id FROM summary_neighborhood WHERE office=1 AND round=1 AND municipality=71072 AND neighborhood=? ORDER BY votes DESC,candidate_id LIMIT 8',['VILA MARIANA']).fetchall()]
        for level in ('neighborhood','municipality'):
            chosen=all_ids[2:]
            filtered=map_data(con,1,1,level,candidate_ids=chosen,**args)
            top=filtered['areas'][0]['top_five']
            assert len(top)==5
            assert [c['candidate_id'] for c in top]==chosen[:5]
            assert [c['position'] for c in top]==[1,2,3,4,5]
            assert all(c['national_share_pct']==pytest.approx(100*c['votes']/c['national_votes']) for c in top)
        for candidate in ranking:
            sp=con.execute('SELECT votes FROM candidate_search WHERE office=1 AND round=1 AND candidate_id=?',[candidate['candidate_id']]).fetchone()[0]
            assert candidate['national_votes']>sp
            assert candidate['national_share_pct']==pytest.approx(100*candidate['votes']/candidate['national_votes'])
            assert candidate['national_share_pct']!=pytest.approx(100*candidate['votes']/sp)


def test_area_details_include_candidates_beyond_hover_and_conserve_votes():
    from eleicoes_sp.map_api import area_candidates
    with connection() as con:
        key='71072|VILA MARIANA'
        details=area_candidates(con,1,1,'neighborhood',key)
        assert len(details)>5
        assert all(c['votes']>0 for c in details)
        assert sum(c['local_share_pct'] for c in details)==pytest.approx(100)
        area=map_data(con,1,1,'neighborhood',municipalities=[71072],neighborhoods=[key])['areas'][0]
        assert sum(c['votes'] for c in details)==area['total']
        combined=area_candidates(con,1,1,'municipality','71072',[key])
        assert details==combined
        assert area_candidates(con,1,2,'neighborhood',key)==[]


def test_area_details_filter_selected_candidates_without_changing_percentages():
    from eleicoes_sp.map_api import area_candidates
    with connection() as con:
        for level,key in [('municipality','71072'),('neighborhood','71072|VILA MARIANA')]:
            all_rows=area_candidates(con,1,1,level,key)
            selected=[r['candidate_id'] for r in all_rows[2:9]]
            filtered=area_candidates(con,1,1,level,key,candidate_ids=selected)
            assert filtered==all_rows[2:9]
            assert len(filtered)>5
            assert all(r['votes']>0 for r in filtered)
            assert area_candidates(con,1,1,level,key,candidate_ids=[-1])==[]


def test_presidential_winner_uses_actual_top_two_and_local_percentage_points():
    with connection() as con:
        args=dict(municipalities=[71072],neighborhoods=['71072|VILA MARIANA'])
        for level in ('municipality','neighborhood'):
            original=map_data(con,1,1,level,**args)
            area=original['areas'][0];top=area['top_five'];winner=area['winner']
            assert winner['candidate_id']==top[0]['candidate_id']
            assert winner['runner_up']['candidate_id']==top[1]['candidate_id']
            assert winner['margin_votes']==top[0]['votes']-top[1]['votes']
            assert winner['margin_pp']==pytest.approx(100*(top[0]['votes']-top[1]['votes'])/area['total'])
            selected=map_data(con,1,1,level,candidate_ids=[top[-1]['candidate_id']],**args)
            assert selected['areas'][0]['winner']==winner
        assert all('winner' not in a for a in map_data(con,3,1,'municipality',municipalities=[71072])['areas'])
