from unittest.mock import patch

import pytest
from flask import Flask

import thuis


@pytest.fixture()
def app():
  app = Flask(__name__, template_folder='../templates')
  app.config.update({
    "TESTING": True,
  })

  @app.route('/thuis', methods=['GET'])
  def thuishoofdpagina():
    return thuis.thuispagina()

  @app.route('/thuis/login', methods=['POST'])
  def thuisloginpagina():
    return thuis.loginpagina()

  @app.route('/thuis/pod', methods=['POST'])
  def thuispodpagina():
    return thuis.podpagina()

  @app.route('/thuis/tokens', methods=['GET'])
  def thuistokenspagina():
    return thuis.tokenspagina()

  yield app


@pytest.fixture()
def client(app):
  return app.test_client()


def test_404(client):
  response = client.get('/home')
  assert b"404 Not Found" in response.data


@patch('pysondb.db.JsonDatabase.getAll',
       return_value=[{'env': 'pod', 'value': '1234-4321-5678', 'id': 28234834},
                     {'env': 'jsessionid', 'value': 'E3~1234CAFE5678DECA', 'id': 286349129001},
                     {'env': 'token', 'value': '4321c0de', 'id': 236910029}]
       )
def test_hoofdpaginaget(mock_dbgetall, client):
  response = client.get('/thuis')
  assert b"<h1>Thuis</h1>" in response.data
  assert mock_dbgetall.call_count == 1


@patch('pysondb.db.JsonDatabase.getAll',
       return_value=[]
       )
def test_hoofdpaginaget_geenpod(mock_dbgetall, client):
  response = client.get('/thuis')
  assert b"<h1>Thuis</h1>" in response.data
  assert b"input name=\"pod\"" in response.data
  assert mock_dbgetall.call_count == 1


@patch('pysondb.db.JsonDatabase.getAll',
       return_value=[{'env': 'pod', 'value': '1234-4321-5678', 'id': 28234834}]
       )
def test_hoofdpaginaget_geenjsessionid(mock_dbgetall, client):
  response = client.get('/thuis')
  assert b"<h1>Thuis</h1>" in response.data
  assert b"input name=\"userid\"" in response.data
  assert b"input name=\"password\"" in response.data
  assert mock_dbgetall.call_count == 1


@patch('pysondb.db.JsonDatabase.add')
def test_loginpaginapost(mock_dbadd, client):
  data = {'userid': 'dummy', 'password': '<PASSWORD>'}
  response = client.post('/thuis/login', data=data)
  assert b"<h1>Redirecting...</h1>" in response.data
  assert b"/thuis" in response.data
  assert mock_dbadd.call_count == 1


@patch('pysondb.db.JsonDatabase.add')
def test_podpaginapost(mock_dbadd, client):
  data = {'pod': 'dummy'}
  response = client.post('/thuis/pod', data=data)
  assert b"<h1>Redirecting...</h1>" in response.data
  assert b"/thuis" in response.data
  assert mock_dbadd.call_count == 1


@patch('pysondb.db.JsonDatabase.getAll',
       return_value=[{'env': 'pod', 'value': '1234-4321-5678', 'id': 28234834},
                     {'env': 'jsessionid', 'value': 'E3~1234CAFE5678DECA', 'id': 286349129001},
                     {'env': 'token', 'value': '4321c0de', 'id': 236910029}]
       )
@patch('thuis.getavailabletokens', return_value=[{'data': 'dummytoken'}])
def test_tokenspaginaget(mock_getavailabletokens, mock_dbgetall, client):
  response = client.get('/thuis/tokens')
  assert b"<h1>Tokens</h1>" in response.data
  assert b"dummytoken" in response.data
  assert mock_dbgetall.call_count == 1
  assert mock_getavailabletokens.call_count == 1


@patch('pysondb.db.JsonDatabase.getAll',
       return_value=[{'env': 'pod', 'value': '1234-4321-5678', 'id': 28234834},
                     {'env': 'jsessionid', 'value': 'E3~1234CAFE5678DECA', 'id': 286349129001},
                     {'env': 'token', 'value': '4321c0de', 'id': 236910029}]
       )
@patch('thuis.getavailabletokens', return_value={'error': 'unauthorized'})
def test_tokenspaginaget_geensessie(mock_getavailabletokens, mock_dbgetall, client):
  response = client.get('/thuis/tokens')
  assert b"Redirecting..." in response.data
  assert b"/thuis" in response.data
  assert mock_dbgetall.call_count == 1
  assert mock_getavailabletokens.call_count == 1


@patch('pysondb.db.JsonDatabase.getAll',
       return_value=[{'env': 'jsessionid', 'value': 'E3~1234CAFE5678DECA', 'id': 286349129001},
                     {'env': 'token', 'value': '4321c0de', 'id': 236910029}]
       )
@patch('thuis.getavailabletokens', return_value=[{'data': 'dummytoken'}])
def test_tokenspaginaget_geenpod(mock_getavailabletokens, mock_dbgetall, client):
  response = client.get('/thuis/tokens')
  assert b"<h1>Redirecting...</h1>" in response.data
  assert b"/thuis" in response.data
  assert b"dummytoken" not in response.data
  assert mock_dbgetall.call_count == 1
  assert mock_getavailabletokens.call_count == 0


@patch('pysondb.db.JsonDatabase.getAll',
       return_value=[{'env': 'pod', 'value': '1234-4321-5678', 'id': 28234834},
                     {'env': 'token', 'value': '4321c0de', 'id': 236910029}]
       )
@patch('thuis.getavailabletokens', return_value=[{'data': 'dummytoken'}])
def test_tokenspaginaget_geenjsessionid(mock_getavailabletokens, mock_dbgetall, client):
  response = client.get('/thuis/tokens')
  assert b"<h1>Redirecting...</h1>" in response.data
  assert b"/thuis" in response.data
  assert b"dummytoken" not in response.data
  assert mock_dbgetall.call_count == 1
  assert mock_getavailabletokens.call_count == 0
