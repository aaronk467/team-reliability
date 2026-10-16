from fastapi.testclient import TestClient
from responsewatch.api import app

client=TestClient(app)
TOKEN='test-only-review-key-with-at-least-32-characters'
HEADER={'Authorization':'Bearer '+TOKEN}
ROW=dict(source='stable',zone='South',owner='reviewer-01',status='in_progress',action='Check synchronized clocks',version=0)


def setup_store(monkeypatch,tmp_path):
    monkeypatch.setenv('RESPONSEWATCH_DB_PATH',str(tmp_path/'reviews.sqlite3'))
    monkeypatch.setenv('RESPONSEWATCH_REVIEW_TOKEN',TOKEN)


def test_unconfigured_store_does_not_accept_or_expose_reviews(monkeypatch):
    monkeypatch.delenv('RESPONSEWATCH_DB_PATH',raising=False)
    monkeypatch.delenv('RESPONSEWATCH_REVIEW_TOKEN',raising=False)
    assert client.get('/api/reviews/config').json()['storage']=='browser_local'
    assert client.get('/api/reviews',params={'source':'stable'}).status_code==503
    assert client.put('/api/reviews',json=ROW).status_code==503


def test_shared_reviews_auth_persistence_source_isolation_and_conflicts(monkeypatch,tmp_path):
    setup_store(monkeypatch,tmp_path)
    assert client.get('/api/reviews/config').json()['shared_enabled']
    assert client.get('/api/reviews',params={'source':'stable'}).status_code==401
    assert client.put('/api/reviews',json=ROW).status_code==401
    first=client.put('/api/reviews',json=ROW,headers=HEADER)
    assert first.status_code==200,first.text
    assert first.json()['version']==1
    # New client/connection reads the same file, unlike session-only state.
    other=TestClient(app)
    assert other.get('/api/reviews',params={'source':'stable'},headers=HEADER).json()[0]['action']==ROW['action']
    assert other.get('/api/reviews',params={'source':'south_shift'},headers=HEADER).json()==[]
    assert client.put('/api/reviews',json=ROW,headers=HEADER).status_code==409
    assert client.put('/api/reviews',json={**ROW,'version':1,'status':'resolved'},headers=HEADER).json()['version']==2


def test_resolved_review_requires_owner_and_documented_action(monkeypatch,tmp_path):
    setup_store(monkeypatch,tmp_path)
    assert client.put('/api/reviews',json={**ROW,'status':'resolved','action':''},headers=HEADER).status_code==422
    assert client.put('/api/reviews',json={**ROW,'owner':'','status':'in_progress'},headers=HEADER).status_code==422
    assert client.put('/api/reviews',json={**ROW,'version':True},headers=HEADER).status_code==422
