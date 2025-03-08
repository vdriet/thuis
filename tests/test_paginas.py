from unittest.mock import patch

import pytest
from flask import Flask

import thuis


@pytest.fixture
def mock_env_weerapikey(monkeypatch):
  monkeypatch.setenv("WEER_API_KEY", "dummykey")


@pytest.fixture()
def app():
  app = Flask(__name__, template_folder='../templates', static_folder='../static')
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

  @app.route('/thuis/status', methods=['GET'])
  def thuisstatuspagina():
    return thuis.statuspagina()

  @app.route('/thuis/status', methods=['POST'])
  def thuisstatusactiepagina():
    return thuis.statusactiepagina()

  yield app


@pytest.fixture()
def client(app):
  return app.test_client()


@patch('waitress.serve')
def test_start(mock_server, client):
  thuis.startwebserver()

  assert mock_server.call_count == 1


def test_404(client):
  response = client.get('/home')
  assert b"404 Not Found" in response.data


@patch('pysondb.db.JsonDatabase.getByQuery',
       side_effect=[[{'env': 'pod', 'value': '1234-4321-5678', 'id': 28234834}],
                    [{'env': 'jsessionid', 'value': 'E3~1234CAFE5678DECA', 'id': 286349129001}],
                    [{'env': 'userid', 'value': 'email@adres.com', 'id': 23649273}],
                    [{'env': 'password', 'value': 'password', 'id': 9852364}],
                    [{'env': 'token', 'value': '4321c0de', 'id': 236910029}]
                    ])
def test_hoofdpaginaget(mock_dbgetbyquery, client):
  response = client.get('/thuis')
  assert b"<h1>Thuis</h1>" in response.data
  assert b"<li>Pod: 1234-4321-5678</li>" in response.data
  assert mock_dbgetbyquery.call_count == 5


@patch('pysondb.db.JsonDatabase.getByQuery',
       side_effect=[[],
                    [{'env': 'jsessionid', 'value': 'E3~1234CAFE5678DECA', 'id': 286349129001}],
                    [{'env': 'userid', 'value': 'email@adres.com', 'id': 23649273}],
                    [{'env': 'password', 'value': 'password', 'id': 9852364}],
                    [{'env': 'token', 'value': '4321c0de', 'id': 236910029}]
                    ])
def test_hoofdpaginaget_geenpod(mock_dbgetbyquery, client):
  response = client.get('/thuis')

  assert b"<h1>Thuis</h1>" in response.data
  assert b"id=\"pod\" name=\"pod\"" in response.data
  assert mock_dbgetbyquery.call_count == 5


@patch('pysondb.db.JsonDatabase.getByQuery',
       side_effect=[[{'env': 'pod', 'value': '1234-4321-5678', 'id': 28234834}],
                    [],
                    [{'env': 'userid', 'value': 'email@adres.com', 'id': 23649273}],
                    [{'env': 'password', 'value': 'password', 'id': 9852364}],
                    [{'env': 'token', 'value': '4321c0de', 'id': 236910029}]
                    ])
def test_hoofdpaginaget_geenjsessionid(mock_dbgetbyquery, client):
  response = client.get('/thuis')
  assert b"<h1>Thuis</h1>" in response.data
  assert b"<li>Pod: 1234-4321-5678</li>" in response.data
  assert mock_dbgetbyquery.call_count == 5


@patch('pysondb.db.JsonDatabase.getByQuery',
       side_effect=[[{'env': 'pod', 'value': '1234-4321-5678', 'id': 28234834}],
                    [],
                    [],
                    [],
                    [{'env': 'token', 'value': '4321c0de', 'id': 236910029}]
                    ])
def test_hoofdpaginaget_geenjsessionidengeenuserpass(mock_dbgetbyquery, client):
  response = client.get('/thuis')
  assert b"<h1>Thuis</h1>" in response.data
  assert b"id=\"userid\" name=\"userid\"" in response.data
  assert b"id=\"password\" name=\"password\"" in response.data
  assert mock_dbgetbyquery.call_count == 5


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


@patch('pysondb.db.JsonDatabase.getByQuery',
       side_effect=[[{'env': 'pod', 'value': '1234-4321-5678', 'id': 28234834}],
                    [{'env': 'jsessionid', 'value': 'E3~1234CAFE5678DECA', 'id': 286349129001}],
                    [{'env': 'userid', 'value': 'email@adres.com', 'id': 23649273}],
                    [{'env': 'password', 'value': 'password', 'id': 9852364}]
                    ])
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
def test_tokenspaginaget(mock_getavailabletokens, mock_dbgetbyquery, client):
  response = client.get('/thuis/tokens')

  assert b"<h1>Tokens</h1>" in response.data
  assert b"<td>Thuis token</td>" in response.data
  assert b"<td>2025-02-01 1" in response.data
  assert b":10:50</td>" in response.data
  assert mock_dbgetbyquery.call_count == 2
  assert mock_getavailabletokens.call_count == 1


@patch('pysondb.db.JsonDatabase.getByQuery',
       side_effect=[[{'env': 'pod', 'value': '1234-4321-5678', 'id': 28234834}],
                    [{'env': 'jsessionid', 'value': 'E3~1234CAFE5678DECA', 'id': 286349129001}],
                    [{'env': 'jsessionid', 'value': 'E3~5678DECA1234CAFE', 'id': 912900128634}],
                    [],
                    [],
                    ])
@patch('pysondb.db.JsonDatabase.deleteById',
       return_value=None)
@patch('thuis.getavailabletokens', return_value={'error': 'unauthorized'})
def test_tokenspaginaget_geensessie(mock_getavailabletokens, mock_dbdelete, mock_dbquery, client):
  response = client.get('/thuis/tokens')

  assert response.status_code == 302
  assert b"Redirecting..." in response.data
  assert b"/thuis" in response.data
  assert mock_dbquery.call_count == 5
  assert mock_dbdelete.call_count == 1
  assert mock_getavailabletokens.call_count == 1


@patch('pysondb.db.JsonDatabase.getByQuery',
       side_effect=[[{'env': 'pod', 'value': '1234-4321-5678', 'id': 28234834}],
                    [{'env': 'jsessionid', 'value': 'E3~1234CAFE5678DECA', 'id': 286349129001}],
                    [{'env': 'jsessionid', 'value': 'E3~5678DECA1234CAFE', 'id': 912900128634}],
                    [{'env': 'userid', 'value': 'email@adres.com', 'id': 236910029}],
                    [{'env': 'password', 'value': 'password', 'id': 236910029}],
                    ])
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
                                              client):
  response = client.get('/thuis/tokens')

  assert b"<h1>Tokens</h1>" in response.data
  assert b"<td>Thuis token</td>" in response.data
  assert b"<td>2025-02-01 1" in response.data
  assert b":10:50</td>" in response.data
  assert mock_dbquery.call_count == 5
  assert mock_dbdelete.call_count == 1
  assert mock_dbadd.call_count == 1
  assert mock_getavailabletokens.call_count == 2


@patch('pysondb.db.JsonDatabase.getByQuery',
       side_effect=[[],
                    [{'env': 'jsessionid', 'value': 'E3~1234CAFE5678DECA', 'id': 286349129001}]
                    ])
@patch('thuis.getavailabletokens', return_value=[{'data': 'dummytoken'}])
def test_tokenspaginaget_geenpod(mock_getavailabletokens, mock_dbquery, client):
  response = client.get('/thuis/tokens')

  assert response.status_code == 302
  assert b"<h1>Redirecting...</h1>" in response.data
  assert b"/thuis" in response.data
  assert b"dummytoken" not in response.data
  assert mock_dbquery.call_count == 2
  assert mock_getavailabletokens.call_count == 0


@patch('pysondb.db.JsonDatabase.getByQuery',
       side_effect=[[{'env': 'pod', 'value': '1234-4321-5678', 'id': 28234834}],
                    [],
                    []
                    ])
@patch('thuis.getavailabletokens', return_value=[{'data': 'dummytoken'}])
def test_tokenspaginaget_geenjsessionid(mock_getavailabletokens, mock_dbquery, client):
  response = client.get('/thuis/tokens')

  assert response.status_code == 302
  assert b"<h1>Redirecting...</h1>" in response.data
  assert b"/thuis" in response.data
  assert b"dummytoken" not in response.data
  assert mock_dbquery.call_count == 2
  assert mock_getavailabletokens.call_count == 0


@patch('pysondb.db.JsonDatabase.getByQuery',
       side_effect=[[{'env': 'pod', 'value': '1234-4321-5678', 'id': 28234834}],
                    [{'env': 'jsessionid', 'value': 'E3~1234CAFE5678DECA', 'id': 286349129001}],
                    ])
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
def test_tokenspaginapost_delete(mock_deletetoken, mock_gettokens, mock_getquery, client):
  data = {'actie': 'delete', 'uuid': '20547c11-73ce-475b-88be-6e30824b2b54'}
  response = client.post('/thuis/tokens', data=data)

  assert b"<h1>Tokens</h1>" in response.data
  assert mock_gettokens.call_count == 1
  assert mock_getquery.call_count == 2
  assert mock_deletetoken.call_count == 1


@patch('pysondb.db.JsonDatabase.getByQuery',
       side_effect=[[{'env': 'pod', 'value': '1234-4321-5678', 'id': 28234834}],
                    [{'env': 'jsessionid', 'value': 'E3~1234CAFE5678DECA', 'id': 286349129001}],
                    ])
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
def test_tokenspaginapost_delete_geensessie(mock_deletetoken, mock_gettokens, mock_dbquery, client):
  data = {'actie': 'delete', 'uuid': '20547c11-73ce-475b-88be-6e30824b2b54'}
  response = client.post('/thuis/tokens', data=data)

  assert response.status_code == 302
  assert b"<h1>Redirecting...</h1>" in response.data
  assert b"/thuis/tokens" in response.data
  assert mock_gettokens.call_count == 0
  assert mock_dbquery.call_count == 0
  assert mock_deletetoken.call_count == 1


@patch('pysondb.db.JsonDatabase.getByQuery',
       side_effect=[[{'env': 'pod', 'value': '1234-4321-5678', 'id': 28234834}],
                    [{'env': 'jsessionid', 'value': 'E3~1234CAFE5678DECA', 'id': 286349129001}]
                    ])
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
@patch('thuis.createtoken')
def test_tokenspaginapost_createtoken(mock_createtoken, mock_gettokens, mock_dbquery, client):
  data = {'actie': 'create', 'label': 'dummy label'}
  response = client.post('/thuis/tokens', data=data)

  assert b"<h1>Tokens</h1>" in response.data
  assert mock_gettokens.call_count == 1
  assert mock_dbquery.call_count == 2
  assert mock_createtoken.call_count == 1


@patch('pysondb.db.JsonDatabase.getByQuery',
       side_effect=[[{'env': 'pod', 'value': '1234-4321-5678', 'id': 28234834}],
                    [{'env': 'jsessionid', 'value': 'E3~1234CAFE5678DECA', 'id': 286349129001}],
                    [{'env': 'schermen', 'value': [{'label': 'label 1.1', 'device': 'io://1234-4321-5678/13579'},
                                                   {'label': 'label 2.2', 'device': 'io://1234-4321-5678/24680'}]}]
                    ]
       )
@patch('thuis.haalgegevensvansomfy',
       side_effect=[{'value': '0'},
                    {'value': '50'}
                    ])
@patch('thuis.haalwindsnelheid', return_value=2)
def test_statuspagina(mock_wind, mock_somfy, mock_env, mock_env_weerapikey, client):
  response = client.get('/thuis/status')

  assert b"<h1>Status</h1>" in response.data
  assert b">label 1.1<" in response.data
  assert b">0<" in response.data
  assert b">Windsnelheid 2 bft<" in response.data
  assert mock_env.call_count == 3
  assert mock_somfy.call_count == 2
  assert mock_wind.call_count == 1


@patch('pysondb.db.JsonDatabase.getByQuery',
       side_effect=[[],
                    [{'env': 'jsessionid', 'value': 'E3~1234CAFE5678DECA', 'id': 286349129001}]
                    ])
@patch('thuis.haalgegevensvansomfy',
       return_value={'error': 'dummy'})
@patch('thuis.haalwindsnelheid', return_value=2)
def test_statuspagina_geenpod(mock_wind, mock_somfy, mock_env, mock_env_weerapikey, client):
  response = client.get('/thuis/status')

  assert response.status_code == 302
  assert b"<h1>Redirecting...</h1>" in response.data
  assert b"/thuis" in response.data
  assert mock_env.call_count == 2
  assert mock_somfy.call_count == 0
  assert mock_wind.call_count == 0


@patch('pysondb.db.JsonDatabase.getByQuery',
       side_effect=[[{'env': 'pod', 'value': '1234-4321-5678', 'id': 28234834}],
                    [{'env': 'jsessionid', 'value': 'E3~1234CAFE5678DECA', 'id': 286349129001}],
                    []
                    ]
       )
@patch('thuis.getschermen',
       return_value=[{'label': 'label 1.2', 'device': 'io://1234-4321-5678/13579'},
                     {'label': 'label 2.2', 'device': 'io://1234-4321-5678/24680'}]
       )
@patch('thuis.haalgegevensvansomfy',
       side_effect=[{'value': '0'},
                    {'value': '50'}
                    ]
       )
@patch('thuis.haalwindsnelheid', return_value=2)
def test_statuspagina_geenschermcache(mock_wind, mock_somfy, mock_schermen, mock_envquery, mock_env_weerapikey, client):
  response = client.get('/thuis/status')

  assert b"<h1>Status</h1>" in response.data
  assert b">label 1.2<" in response.data
  assert b">0<" in response.data
  assert mock_envquery.call_count == 3
  assert mock_schermen.call_count == 1
  assert mock_somfy.call_count == 2
  assert mock_wind.call_count == 1


@patch('pysondb.db.JsonDatabase.getByQuery',
       side_effect=[[{'env': 'pod', 'value': '1234-4321-5678', 'id': 28234834}],
                    [{'env': 'jsessionid', 'value': 'E3~1234CAFE5678DECA', 'id': 286349129001}],
                    [{'env': 'schermen', 'value': [{'label': 'label 1.3', 'device': 'io://1234-4321-5678/13579'},
                                                   {'label': 'label 2.3', 'device': 'io://1234-4321-5678/24680'}]}]
                    ])
@patch('thuis.haalgegevensvansomfy',
       return_value={'error': 'dummy'})
@patch('thuis.haalwindsnelheid', return_value=2)
def test_statuspagina_error(mock_wind, mock_somfy, mock_env, mock_env_weerapikey, client):
  response = client.get('/thuis/status')

  assert response.status_code == 302
  assert b"<h1>Redirecting...</h1>" in response.data
  assert b"/thuis" in response.data
  assert mock_env.call_count == 3
  assert mock_somfy.call_count == 1
  assert mock_wind.call_count == 0


@patch('thuis.verplaatsscherm')
def test_statuspaginapost(mock_verplaats, client):
  data = {'actie': 'zetscherm', 'device': 'dummyid', 'percentage': '20'}
  response = client.post('/thuis/status', data=data)

  assert response.status_code == 302
  assert b"<h1>Redirecting...</h1>" in response.data
  assert b"/thuis/status" in response.data
  assert mock_verplaats.call_count == 1


@patch('thuis.verplaatsscherm')
def test_statuspaginapost_geengetal(mock_verplaats, client):
  data = {'actie': 'zetscherm', 'device': 'dummyid', 'percentage': 'abc'}
  response = client.post('/thuis/status', data=data)

  assert response.status_code == 302
  assert b"<h1>Redirecting...</h1>" in response.data
  assert b"/thuis/status" in response.data
  assert mock_verplaats.call_count == 0


@patch('thuis.sluitalles')
@patch('thuis.openalles')
def test_statuspaginapost_sluitalles(mock_openalles, mock_sluitalles, client):
  data = {'actie': 'sluitalles', 'device': 'dummyid', 'percentage': 'abc'}
  response = client.post('/thuis/status', data=data)

  assert response.status_code == 302
  assert b"<h1>Redirecting...</h1>" in response.data
  assert b"/thuis/status" in response.data
  assert mock_openalles.call_count == 0
  assert mock_sluitalles.call_count == 1


@patch('thuis.sluitalles')
@patch('thuis.openalles')
def test_statuspaginapost_openalles(mock_openalles, mock_sluitalles, client):
  data = {'actie': 'openalles', 'device': 'dummyid', 'percentage': 'abc'}
  response = client.post('/thuis/status', data=data)

  assert response.status_code == 302
  assert b"<h1>Redirecting...</h1>" in response.data
  assert b"/thuis/status" in response.data
  assert mock_openalles.call_count == 1
  assert mock_sluitalles.call_count == 0


@patch('thuis.verversschermen')
def test_statuspaginapost_ververs(mock_ververs, client):
  data = {'actie': 'ververs', 'device': 'dummyid', 'percentage': 'abc'}
  response = client.post('/thuis/status', data=data)

  assert response.status_code == 302
  assert b"<h1>Redirecting...</h1>" in response.data
  assert b"/thuis/status" in response.data
  assert mock_ververs.call_count == 1
