from fastapi import FastAPI
from fastapi.testclient import TestClient
from services import upstox_connection as broker
import pytest

@pytest.fixture
def client(monkeypatch):
    broker._states.clear()
    broker._tokens.clear()
    broker._outcomes.clear()
    for name in ('UPSTOX_CLIENT_ID', 'UPSTOX_CLIENT_SECRET', 'UPSTOX_REDIRECT_URI', 'SUPABASE_URL', 'SUPABASE_ANON_KEY', 'FRONTEND_ORIGIN'):
        monkeypatch.delenv(name, raising=False)
    app = FastAPI()
    app.include_router(broker.router)
    return TestClient(app)

def test_unconfigured_and_forged_callback_rejected(client):
    assert client.get('/brokers/upstox/status').json() == {'configured': False}
    assert client.post('/brokers/upstox/connect').status_code == 503
    assert client.get('/brokers/upstox/callback?state=forged&code=x').status_code == 400

def test_connected_holdings_are_bound_to_verified_user(client):
    client.app.dependency_overrides[broker.owner] = lambda: 'another-user'
    broker._tokens['first-user'] = 'private'
    assert client.post('/brokers/upstox/holdings').status_code == 409
    assert client.delete('/brokers/upstox/connection').status_code == 200
    assert broker._tokens['first-user'] == 'private'

@pytest.fixture
def oauth(client, monkeypatch):
    for key, value in {
        'UPSTOX_CLIENT_ID': 'test-client', 'UPSTOX_CLIENT_SECRET': 'test-secret',
        'UPSTOX_REDIRECT_URI': 'http://127.0.0.1:8000/brokers/upstox/callback',
        'FRONTEND_ORIGIN': 'http://127.0.0.1:5173',
    }.items():
        monkeypatch.setenv(key, value)
    broker._states['test-state'] = ('account-one', broker.time.time() + 600)
    return client


def test_callback_success_and_single_use(oauth, monkeypatch):
    from unittest.mock import Mock
    post = Mock(return_value=Mock(ok=True, json=lambda: {'access_token': 'private-token'}))
    monkeypatch.setattr(broker.requests, 'post', post)
    response = oauth.get('/brokers/upstox/callback?state=test-state&code=private-code', follow_redirects=False)
    assert response.headers['location'] == 'http://127.0.0.1:5173/dashboard/portfolio?upstox=connected'
    assert response.headers['cache-control'] == 'no-store'
    assert broker._tokens == {'account-one': 'private-token'}
    assert oauth.get('/brokers/upstox/callback?state=test-state&code=private-code').status_code == 400
    assert post.call_count == 1


@pytest.mark.parametrize('code,reason', [
    ('UDAPI100069', 'invalid_credentials'), ('UDAPI100070', 'invalid_redirect'),
    ('UDAPI100057', 'invalid_code'), ('unknown', 'token_rejected'),
])
def test_callback_safe_provider_errors(oauth, monkeypatch, code, reason):
    from unittest.mock import Mock
    monkeypatch.setattr(broker.requests, 'post', Mock(return_value=Mock(
        ok=False, json=lambda: {'errors': [{'errorCode': code, 'message': 'private-secret'}]})))
    response = oauth.get('/brokers/upstox/callback?state=test-state&code=private-code', follow_redirects=False)
    assert response.headers['location'].endswith('?upstox=' + reason)
    assert 'private' not in str(response.headers)
    assert broker._tokens == {}
    oauth.app.dependency_overrides[broker.owner] = lambda: 'account-one'
    assert oauth.get('/brokers/upstox/connection').json()['authorization_result'] == reason


def test_callback_network_failure(oauth, monkeypatch):
    from unittest.mock import Mock
    monkeypatch.setattr(broker.requests, 'post', Mock(side_effect=broker.requests.Timeout('private')))
    response = oauth.get('/brokers/upstox/callback?state=test-state&code=x', follow_redirects=False)
    assert response.headers['location'].endswith('?upstox=network_error')
    assert broker._tokens == {}


@pytest.mark.parametrize('payload', [{}, {'access_token': ''}, [], {'access_token': 123}])
def test_callback_invalid_token_response(oauth, monkeypatch, payload):
    from unittest.mock import Mock
    monkeypatch.setattr(broker.requests, 'post', Mock(return_value=Mock(ok=True, json=lambda: payload)))
    response = oauth.get('/brokers/upstox/callback?state=test-state&code=x', follow_redirects=False)
    assert response.headers['location'].endswith('?upstox=invalid_response')
    assert broker._tokens == {}


def test_connection_status_is_user_scoped(client):
    client.app.dependency_overrides[broker.owner] = lambda: 'new-account'
    broker._tokens['old-account'] = 'private'
    assert client.get('/brokers/upstox/connection').json()['connected'] is False
    broker._tokens['new-account'] = 'other-private'
    assert client.get('/brokers/upstox/connection').json()['connected'] is True
    client.delete('/brokers/upstox/connection')
    assert client.get('/brokers/upstox/connection').json()['connected'] is False
    assert broker._tokens == {'old-account': 'private'}


def test_empty_holdings_are_success_not_disconnected(client, monkeypatch):
    from unittest.mock import Mock
    client.app.dependency_overrides[broker.owner] = lambda: 'account'
    broker._tokens['account'] = 'private'
    monkeypatch.setattr(broker.requests, 'get', Mock(return_value=Mock(
        status_code=200, json=lambda: {'status': 'success', 'data': []})))
    response = client.post('/brokers/upstox/holdings')
    assert response.status_code == 200
    assert response.json() == {'holdings': []}
    assert client.get('/brokers/upstox/connection').json()['connected'] is True


def test_expired_broker_token_clears_connection(client, monkeypatch):
    from unittest.mock import Mock
    client.app.dependency_overrides[broker.owner] = lambda: 'account'
    broker._tokens['account'] = 'private'
    monkeypatch.setattr(broker.requests, 'get', Mock(return_value=Mock(status_code=401)))
    assert client.post('/brokers/upstox/holdings').status_code == 401
    assert client.get('/brokers/upstox/connection').json()['connected'] is False

from unittest.mock import Mock

def test_portfolio_sections_partial_access_and_pagination(client, monkeypatch):
    client.app.dependency_overrides[broker.owner] = lambda: 'account'
    broker._tokens['account'] = 'secret'
    calls = []
    def get(url, **kwargs):
        calls.append((url, kwargs.get('params')))
        if '/mf/holdings' in url:
            return Mock(status_code=200, json=lambda: {'status':'success','data':[{'instrument_key':'INF200K01T51','quantity':2}]})
        if '/mf/sips' in url:
            page = kwargs['params']['page_number']
            return Mock(status_code=200, json=lambda: {'status':'success','data':[{'sip_id':str(page)}], 'meta_data':{'page':{'total_pages':2}}})
        if '/mf/orders' in url: return Mock(status_code=403)
        return Mock(status_code=200, json=lambda: {'status':'success','data':{} if 'margin' in url else []})
    monkeypatch.setattr(broker.requests, 'get', get)
    response = client.post('/brokers/upstox/portfolio')
    assert response.status_code == 200
    sections = response.json()['sections']
    assert len(sections['mutual_funds']['data']) == 1
    assert len(sections['sips']['data']) == 2
    assert sections['fund_orders']['data'] is None
    assert sections['fund_orders']['status'] == 'unavailable'
    assert broker._tokens['account'] == 'secret'
    assert len(sections) == 7


def test_portfolio_requires_connection(client):
    client.app.dependency_overrides[broker.owner] = lambda: 'account'
    assert client.post('/brokers/upstox/portfolio').status_code == 409


def test_portfolio_expired_token(client, monkeypatch):
    client.app.dependency_overrides[broker.owner] = lambda: 'account'
    broker._tokens['account'] = 'secret'
    monkeypatch.setattr(broker.requests, 'get', Mock(return_value=Mock(status_code=401)))
    assert client.post('/brokers/upstox/portfolio').status_code == 401
    assert 'account' not in broker._tokens
