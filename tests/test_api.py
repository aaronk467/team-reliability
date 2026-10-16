from fastapi.testclient import TestClient
from responsewatch.api import app
client=TestClient(app)
ROW=dict(id='1',zone='North',priority='high',dispatched_at='2026-01-01T12:00:00Z',arrived_at='2026-01-01T12:09:00Z')

def test_health():
    assert client.get('/api/health').json()=={'status':'ok'}

def test_analyze_and_validation():
    response=client.post('/api/analyze',json={'records':[ROW]})
    assert response.status_code==200
    result=response.json()
    assert result['summary']['late_count']==1
    assert result['zones'][0]['imr']['ucl'] is None
    assert client.post('/api/analyze',json={'records':[ROW,ROW]}).status_code==422
    assert client.post('/api/analyze',json={'records':[ROW],'baseline_days':True}).status_code==422
    assert client.post('/api/analyze',json={'records':[ROW],'priority':'missing'}).status_code==422
    assert client.post('/api/validate-record',json={**ROW,'arrived_at':'unknown'}).status_code==422

def test_datasets():
    response=client.get('/api/datasets')
    assert response.status_code==200
    for entry in response.json():
        data=client.get('/api/datasets/'+entry['name']).json()
        analysis=client.post('/api/analyze',json={'records':data['records']})
        assert analysis.status_code==200, analysis.text
    assert client.get('/api/datasets/missing').status_code==404


def test_monitoring_options_and_strict_inputs():
    request = {"records": [ROW], "imr_scale": "raw", "aggregation_days": 1}
    result = client.post('/api/analyze', json=request)
    assert result.status_code == 200
    assert result.json()['imr_scale'] == 'raw'
    assert result.json()['aggregation_days'] == 1
    for change in ({"aggregation_days": True}, {"aggregation_days": 0}, {"aggregation_days": 366},
                   {"imr_scale": "unknown"}, {"target_minutes": True}):
        assert client.post('/api/analyze', json={**request, **change}).status_code == 422


def test_typed_analysis_matches_library_without_omitted_fields():
    """HTTP response serialization must retain every calculated nested field."""
    from responsewatch.stats import analyze

    records = client.get('/api/datasets/south_shift').json()['records']
    for method in ('beta_binomial', 'exact_binomial'):
        options = dict(records=records, priority='high', p_method=method)
        response = client.post('/api/analyze', json=options)
        assert response.status_code == 200, response.text
        assert response.json() == analyze(**options)
        result = response.json()
        assert result['p_method'] == method
        assert result['zones'][0]['p_chart']['method'] == method
        assert 'delay_patterns' in result
        assert 'baseline_quality' in result['zones'][0]


def test_typed_context_preserves_additional_deidentified_fields():
    payload = {**ROW, 'shift': 'night', 'traffic': 'heavy',
               'units_available': '0', 'delay_reason': 'traffic',
               'dispatch_batch': 'B-17'}
    response = client.post('/api/validate-record', json=payload)
    assert response.status_code == 200, response.text
    clean = response.json()
    assert clean['minutes'] == 9
    assert clean['dispatch_batch'] == 'B-17'
    assert clean['shift'] == 'night'
    result = client.post('/api/analyze', json={'records': [payload]})
    assert result.status_code == 200, result.text
    patterns = result.json()['delay_patterns']
    assert patterns['reason_coverage'] == 1
    assert patterns['late_reason_coverage'] == 1
    assert patterns['reasons'][0]['reason'] == 'traffic'


def test_api_rejects_invalid_context_and_ambiguous_timestamps():
    for change in ({'units_available': True}, {'units_available': -1},
                   {'units_available': '1.5'}, {'units_available': 1.5},
                   {'shift': 10}, {'traffic': False},
                   {'dispatched_at': '2026-01-01T12:00:00'}, {'delay_reason': 5}):
        payload = {**ROW, **change}
        assert client.post('/api/validate-record', json=payload).status_code == 422, change
        assert client.post('/api/analyze', json={'records': [payload]}).status_code == 422, change
    assert client.post('/api/analyze', json={'records': [ROW], 'p_method': 'unknown'}).status_code == 422
    assert client.post('/api/analyze', json={'records': [ROW], 'baseline_days': '20'}).status_code == 422


def test_openapi_documents_complete_nested_analysis_and_record_contracts():
    document = client.get('/openapi.json').json()
    assert document['info']['version'] == '0.3.0'
    models = document['components']['schemas']
    assert set(models['DispatchRecord']['required']) == {
        'id', 'zone', 'priority', 'dispatched_at', 'arrived_at'}
    assert {'shift', 'traffic', 'units_available'} <= models['DispatchRecord']['properties'].keys()
    for model, fields in {
        'AnalysisResponse': {'summary', 'zones', 'delay_patterns', 'p_method'},
        'ZoneAnalysis': {'imr', 'p_chart', 'comparison', 'baseline_quality', 'delay_patterns'},
        'LateRateChart': {'posterior_alpha', 'posterior_beta', 'points', 'baseline_signal_policy'},
        'PeriodPoint': {'signal_evaluated', 'period_start', 'period_end'},
        'BaselineQuality': {'review_recommended', 'reasons'},
        'DelayPatterns': {'late_reason_coverage', 'strata', 'reasons'},
    }.items():
        assert fields <= models[model]['properties'].keys()
        assert models[model]['additionalProperties'] is False
    response_schema = document['paths']['/api/analyze']['post']['responses']['200']['content']['application/json']['schema']
    assert response_schema['$ref'].endswith('/AnalysisResponse')
