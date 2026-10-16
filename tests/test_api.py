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
