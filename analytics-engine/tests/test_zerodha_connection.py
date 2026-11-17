import hashlib
import secrets
from urllib.parse import urlparse, parse_qs
from unittest.mock import Mock
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from services import zerodha_connection as broker

@pytest.fixture
def client(monkeypatch):
    broker._states.clear(); broker._tokens.clear(); broker._outcomes.clear()
    for key in ("ZERODHA_CLIENT_ID", "ZERODHA_CLIENT_SECRET"):
        monkeypatch.setenv(key, secrets.token_urlsafe(24))
    monkeypatch.setenv("FRONTEND_ORIGIN", "http://127.0.0.1:5173")
    app = FastAPI(); app.include_router(broker.router)
    app.dependency_overrides[broker.owner] = lambda: "user-one"
    return TestClient(app)

def test_login_state_checksum_and_single_use(client, monkeypatch):
    query = parse_qs(urlparse(client.post('/brokers/zerodha/connect').json()['url']).query)
    state = parse_qs(query['redirect_params'][0])['state'][0]
    token = secrets.token_urlsafe(24)
    post = Mock(return_value=Mock(ok=True, json=lambda: {'status':'success', 'data':{'access_token':token}}))
    monkeypatch.setattr(broker.requests, 'post', post)
    params = {'state':state, 'request_token':'mock-request', 'status':'success'}
    response = client.get('/brokers/zerodha/callback', params=params, follow_redirects=False)
    assert response.headers['location'].endswith('?zerodha=connected')
    assert broker._tokens['user-one'] == token
    expected = hashlib.sha256((broker.os.environ['ZERODHA_CLIENT_ID'] + 'mock-request' + broker.os.environ['ZERODHA_CLIENT_SECRET']).encode()).hexdigest()
    assert post.call_args.kwargs['data']['checksum'] == expected
    assert client.get('/brokers/zerodha/callback', params=params).status_code == 400
    assert token not in response.text

def test_forged_expired_and_denied(client):
    assert client.get('/brokers/zerodha/callback?state=forged').status_code == 400
    broker._states['old'] = ('user-one', 0)
    assert client.get('/brokers/zerodha/callback?state=old').status_code == 400
    broker._states['denied'] = ('user-one', broker.time.time()+60)
    response = client.get('/brokers/zerodha/callback?state=denied&status=cancelled', follow_redirects=False)
    assert response.headers['location'].endswith('zerodha=invalid_code')

@pytest.mark.parametrize('payload', [{}, {'status':'success','data':None}, {'status':'success','data':{'access_token':123}}])
def test_invalid_token_response(client, monkeypatch, payload):
    broker._states['pending'] = ('user-one', broker.time.time()+60)
    monkeypatch.setattr(broker.requests, 'post', Mock(return_value=Mock(ok=True,json=lambda:payload)))
    response = client.get('/brokers/zerodha/callback?state=pending&request_token=fake&status=success', follow_redirects=False)
    assert response.headers['location'].endswith('zerodha=invalid_response')
    assert not broker._tokens

def test_account_isolation_and_disconnect(client):
    broker._tokens['other-user'] = secrets.token_urlsafe(24)
    assert client.post('/brokers/zerodha/portfolio').status_code == 409
    assert client.delete('/brokers/zerodha/connection').status_code == 200
    assert 'other-user' in broker._tokens

def test_expired_token_cleared(client, monkeypatch):
    broker._tokens['user-one'] = secrets.token_urlsafe(24)
    monkeypatch.setattr(broker.requests, 'get', Mock(return_value=Mock(status_code=403)))
    assert client.post('/brokers/zerodha/portfolio').status_code == 401
    assert 'user-one' not in broker._tokens

def test_sections_and_nav_fallback(client, monkeypatch):
    broker._tokens['user-one'] = secrets.token_urlsafe(24)
    def get(url, **kwargs):
        if 'amfiindia' in url:
            return Mock(text='123456;INF000000001;;Test Fund;12.5;16-Nov-2026', raise_for_status=lambda:None)
        data = ([{'tradingsymbol':'INF000000001', 'last_price_date':''}] if url.endswith('mf/holdings')
                else {} if url.endswith(('positions','margins')) else [])
        return Mock(status_code=200, raise_for_status=lambda:None, json=lambda:{'status':'success','data':data})
    monkeypatch.setattr(broker.requests, 'get', get)
    result = client.post('/brokers/zerodha/portfolio').json()
    assert result['source'] == 'Zerodha'
    assert result['read_only'] is True
    fund = result['sections']['mutual_funds']['data'][0]
    assert fund['last_price_date'] == '2026-11-16'
    assert fund['valuation_source'] == 'AMFI'


def test_legacy_upstox_callback_routes_kite_response_without_bypassing_state(client, monkeypatch):
    from services import upstox_connection as upstox
    client.app.include_router(upstox.router)
    token = secrets.token_urlsafe(24)
    post = Mock(return_value=Mock(ok=True, json=lambda: {'status':'success','data':{'access_token':token}}))
    monkeypatch.setattr(broker.requests, 'post', post)
    path = '/brokers/upstox/callback'
    params = {'request_token':'mock-request','status':'success','state':'unknown'}
    assert client.get(path, params=params).status_code == 400
    post.assert_not_called()
    broker._states['valid'] = ('user-one', broker.time.time()+60)
    params['state'] = 'valid'
    response = client.get(path, params=params, follow_redirects=False)
    assert response.headers['location'].endswith('?zerodha=connected')
    assert broker._tokens['user-one'] == token
    assert post.call_args.args[0] == 'https://api.kite.trade/session/token'
    assert client.get(path, params=params).status_code == 400
    assert post.call_count == 1
