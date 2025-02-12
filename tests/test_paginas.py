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

  @app.route('/thuis/tokens', methods=['POST'])
  def thuistokensactiepagina():
    return thuis.tokensactiepagina()

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
def test_loginpaginapost_save(mock_dbadd, client):
  data = {'userid': 'dummy', 'password': '<PASSWORD>', 'savelogin': 'on'}
  response = client.post('/thuis/login', data=data)

  assert response.status_code == 302
  assert b"<h1>Redirecting...</h1>" in response.data
  assert b"/thuis" in response.data
  assert mock_dbadd.call_count == 3


@patch('pysondb.db.JsonDatabase.add')
def test_loginpaginapost_nosave(mock_dbadd, client):
  data = {'userid': 'dummy', 'password': '<PASSWORD>', 'savelogin': 'off'}
  response = client.post('/thuis/login', data=data)

  assert response.status_code == 302
  assert b"<h1>Redirecting...</h1>" in response.data
  assert b"/thuis" in response.data
  assert mock_dbadd.call_count == 1


@patch('pysondb.db.JsonDatabase.add')
def test_podpaginapost(mock_dbadd, client):
  data = {'pod': 'dummy'}
  response = client.post('/thuis/pod', data=data)

  assert response.status_code == 302
  assert b"<h1>Redirecting...</h1>" in response.data
  assert b"/thuis" in response.data
  assert mock_dbadd.call_count == 1


@patch('pysondb.db.JsonDatabase.getAll',
       return_value=[{'env': 'pod', 'value': '1234-4321-5678', 'id': 28234834},
                     {'env': 'jsessionid', 'value': 'E3~1234CAFE5678DECA', 'id': 286349129001},
                     {'env': 'token', 'value': '4321c0de', 'id': 236910029}]
       )
@patch('thuis.getavailabletokens',
       return_value=[{'label': 'Python token',
                      'gatewayId': '1234-4321-5678',
                      'gatewayCreationTime': 1738422650000,
                      'uuid': '20547c11-73ce-475b-88be-6e30824b2b54',
                      'scope': 'devmode'},
                     {'label': 'Thuis token',
                      'gatewayId': '1234-4321-5678',
                      'gatewayCreationTime': 1739117276000,
                      'uuid': 'b3d4be51-1c5f-4f3c-acce-9f8a8f345328',
                      'scope': 'devmode'}])
def test_tokenspaginaget(mock_getavailabletokens, mock_dbgetall, client):
  response = client.get('/thuis/tokens')

  assert b"<h1>Tokens</h1>" in response.data
  assert b"<td>Thuis token</td>" in response.data
  assert b"<td>2025-02-01 1" in response.data
  assert b":10:50</td>" in response.data
  assert mock_dbgetall.call_count == 1
  assert mock_getavailabletokens.call_count == 1


@patch('pysondb.db.JsonDatabase.getAll',
       return_value=[{'env': 'pod', 'value': '1234-4321-5678', 'id': 28234834},
                     {'env': 'jsessionid', 'value': 'E3~1234CAFE5678DECA', 'id': 286349129001},
                     {'env': 'token', 'value': '4321c0de', 'id': 236910029}]
       )
@patch('pysondb.db.JsonDatabase.getByQuery',
       return_value=[{'env': 'jsessionid', 'value': 'E3~1234CAFE5678DECA', 'id': 286349129001}])
@patch('pysondb.db.JsonDatabase.deleteById',
       return_value=None)
@patch('thuis.getavailabletokens', return_value={'error': 'unauthorized'})
def test_tokenspaginaget_geensessie(mock_getavailabletokens, mock_dbdelete, mock_dbquery, mock_dbgetall, client):
  response = client.get('/thuis/tokens')

  assert response.status_code == 302
  assert b"Redirecting..." in response.data
  assert b"/thuis" in response.data
  assert mock_dbgetall.call_count == 1
  assert mock_dbquery.call_count == 1
  assert mock_dbdelete.call_count == 1
  assert mock_getavailabletokens.call_count == 1


@patch('pysondb.db.JsonDatabase.getAll',
       return_value=[{'env': 'pod', 'value': '1234-4321-5678', 'id': 28234834},
                     {'env': 'jsessionid', 'value': 'E3~1234CAFE5678DECA', 'id': 286349129001},
                     {'env': 'token', 'value': '4321c0de', 'id': 236910029},
                     {'env': 'userid', 'value': 'dummyuser', 'id': 9236492384},
                     {'env': 'password', 'value': 'dummypass', 'id': 982369283}]
       )
@patch('pysondb.db.JsonDatabase.getByQuery',
       return_value=[{'env': 'jsessionid', 'value': 'E3~1234CAFE5678DECA', 'id': 286349129001}])
@patch('pysondb.db.JsonDatabase.deleteById',
       return_value=None)
@patch('pysondb.db.JsonDatabase.add',
       return_value=None)
@patch('thuis.getavailabletokens',
       side_effect=[{'error': 'unauthorized'},
                    [{'label': 'Python token',
                      'gatewayId': '1234-4321-5678',
                      'gatewayCreationTime': 1738422650000,
                      'uuid': '20547c11-73ce-475b-88be-6e30824b2b54',
                      'scope': 'devmode'},
                     {'label': 'Thuis token',
                      'gatewayId': '1234-4321-5678',
                      'gatewayCreationTime': 1739117276000,
                      'uuid': 'b3d4be51-1c5f-4f3c-acce-9f8a8f345328',
                      'scope': 'devmode'}]])
def test_tokenspaginaget_geensessie_autologin(mock_getavailabletokens, mock_dbadd, mock_dbdelete, mock_dbquery,
                                              mock_dbgetall,
                                              client):
  response = client.get('/thuis/tokens')

  assert b"<h1>Tokens</h1>" in response.data
  assert b"<td>Thuis token</td>" in response.data
  assert b"<td>2025-02-01 1" in response.data
  assert b":10:50</td>" in response.data
  assert mock_dbgetall.call_count == 1
  assert mock_dbquery.call_count == 1
  assert mock_dbdelete.call_count == 1
  assert mock_dbadd.call_count == 1
  assert mock_getavailabletokens.call_count == 2


@patch('pysondb.db.JsonDatabase.getAll',
       return_value=[{'env': 'jsessionid', 'value': 'E3~1234CAFE5678DECA', 'id': 286349129001},
                     {'env': 'token', 'value': '4321c0de', 'id': 236910029}]
       )
@patch('thuis.getavailabletokens', return_value=[{'data': 'dummytoken'}])
def test_tokenspaginaget_geenpod(mock_getavailabletokens, mock_dbgetall, client):
  response = client.get('/thuis/tokens')

  assert response.status_code == 302
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

  assert response.status_code == 302
  assert b"<h1>Redirecting...</h1>" in response.data
  assert b"/thuis" in response.data
  assert b"dummytoken" not in response.data
  assert mock_dbgetall.call_count == 1
  assert mock_getavailabletokens.call_count == 0


@patch('pysondb.db.JsonDatabase.getAll',
       return_value=[{'env': 'pod', 'value': '1234-4321-5678', 'id': 28234834},
                     {'env': 'jsessionid', 'value': 'E3~1234CAFE5678DECA', 'id': 286349129001},
                     {'env': 'token', 'value': '4321c0de', 'id': 236910029}]
       )
@patch('thuis.getavailabletokens',
       return_value=[{'label': 'Python token',
                      'gatewayId': '1234-4321-5678',
                      'gatewayCreationTime': 1738422650000,
                      'uuid': '20547c11-73ce-475b-88be-6e30824b2b54',
                      'scope': 'devmode'},
                     {'label': 'Thuis token',
                      'gatewayId': '1234-4321-5678',
                      'gatewayCreationTime': 1739117276000,
                      'uuid': 'b3d4be51-1c5f-4f3c-acce-9f8a8f345328',
                      'scope': 'devmode'}])
@patch('thuis.deletetoken', return_value=200)
def test_tokenspaginapost_delete(mock_deletetoken, mock_gettokens, mock_getenvdb, client):
  data = {'actie': 'delete', 'uuid': '20547c11-73ce-475b-88be-6e30824b2b54'}
  response = client.post('/thuis/tokens', data=data)

  assert b"<h1>Tokens</h1>" in response.data
  assert mock_gettokens.call_count == 1
  assert mock_getenvdb.call_count == 1
  assert mock_deletetoken.call_count == 1


@patch('pysondb.db.JsonDatabase.getAll',
       return_value=[{'env': 'pod', 'value': '1234-4321-5678', 'id': 28234834},
                     {'env': 'jsessionid', 'value': 'E3~1234CAFE5678DECA', 'id': 286349129001},
                     {'env': 'token', 'value': '4321c0de', 'id': 236910029}]
       )
@patch('thuis.getavailabletokens',
       return_value=[{'label': 'Python token',
                      'gatewayId': '1234-4321-5678',
                      'gatewayCreationTime': 1738422650000,
                      'uuid': '20547c11-73ce-475b-88be-6e30824b2b54',
                      'scope': 'devmode'},
                     {'label': 'Thuis token',
                      'gatewayId': '1234-4321-5678',
                      'gatewayCreationTime': 1739117276000,
                      'uuid': 'b3d4be51-1c5f-4f3c-acce-9f8a8f345328',
                      'scope': 'devmode'}])
@patch('thuis.deletetoken', return_value=400)
def test_tokenspaginapost_delete_geensessie(mock_deletetoken, mock_gettokens, mock_getenvdb, client):
  data = {'actie': 'delete', 'uuid': '20547c11-73ce-475b-88be-6e30824b2b54'}
  response = client.post('/thuis/tokens', data=data)

  assert response.status_code == 302
  assert b"<h1>Redirecting...</h1>" in response.data
  assert b"/thuis/tokens" in response.data
  assert mock_gettokens.call_count == 0
  assert mock_getenvdb.call_count == 0
  assert mock_deletetoken.call_count == 1
