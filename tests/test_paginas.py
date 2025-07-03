from unittest.mock import patch, MagicMock

import pytest
from flask import Flask

import thuis


@pytest.fixture
def mock_env_weerapikey(monkeypatch):
  monkeypatch.setenv("WEER_API_KEY", "dummykey")


def maakmockresponse(jsondata):
  mock_response = MagicMock()
  mock_response.getcode.return_value = 200
  mock_response.json.return_value = jsondata
  mock_response.__enter__.return_value = mock_response
  return mock_response


@pytest.fixture()
def app():
  app = Flask(__name__, template_folder='../templates', static_folder='../static')
  app.config.update({
    "TESTING": True,
  })

  @app.route('/thuis', methods=['GET'])
  def thuishoofdpagina():
    return thuis.thuispagina()

  @app.route('/thuis/instellingen', methods=['GET'])
  def thuisinstellingenpagina():
    return thuis.instellingenpagina()

  @app.route('/thuis/instellingen', methods=['POST'])
  def thuisinstellingenactiepagina():
    return thuis.instellingenactiepagina()

  @app.route('/thuis/schermen', methods=['GET'])
  def thuisschermenpagina():
    return thuis.schermenpagina()

  @app.route('/thuis/schermen', methods=['POST'])
  def thuisschermenactiepagina():
    return thuis.schermenactiepagina()

  @app.route('/thuis/lampen', methods=['GET'])
  def thuislampenpagina():
    return thuis.lampenpagina()

  @app.route('/thuis/lampen', methods=['POST'])
  def thuislampenactiepagina():
    return thuis.lampenactiepagina()

  @app.route('/thuis/lampengrid', methods=['GET'])
  def thuislampengridpagina():
    return thuis.lampengridpagina()

  @app.route('/thuis/lampengrid', methods=['POST'])
  def thuislampengridactiepagina():
    return thuis.lampengridactiepagina()

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
       side_effect=[[{'env': 'gridbreedte', 'value': 2, 'id': 23964723}],
                    [{'env': 'gridhoogte', 'value': 5, 'id': 129462834}],
                    [{'env': 'pod', 'value': '1234-4321-5678', 'id': 28234834}],
                    [{'env': 'jsessionid', 'value': 'E3~1234CAFE5678DECA', 'id': 286349129001}],
                    ])
@patch('thuis.haallampen')
@patch('thuis.haalzonnesterkte')
def test_hoofdpaginaget(mock_zonnesterkte, mock_haallampen, mock_dbgetbyquery, client):
  response = client.get('/thuis')
  assert b"<h1>Thuis</h1>" in response.data
  assert mock_dbgetbyquery.call_count == 2
  assert mock_haallampen.call_count == 1
  assert mock_zonnesterkte.call_count == 1


@patch('pysondb.db.JsonDatabase.getByQuery',
       side_effect=[[{'env': 'pod', 'value': '1234-4321-5678', 'id': 28234834}],
                    [],
                    [{'env': 'gridbreedte', 'value': 2, 'id': 23964723}],
                    [{'env': 'gridhoogte', 'value': 5, 'id': 129462834}],
                    ])
@patch('thuis.haalzonnesterkte')
def test_hoofdpaginaget_geenjsessionid(mock_zonnesterkte, mock_dbgetbyquery, client):
  response = client.get('/thuis')
  assert b"<h1>Thuis</h1>" in response.data
  assert mock_dbgetbyquery.call_count == 4
  assert mock_zonnesterkte.call_count == 1


@patch('pysondb.db.JsonDatabase.getByQuery',
       side_effect=[[{'env': 'pod', 'value': '1234-4321-5678', 'id': 28234834}],
                    [],
                    [{'env': 'hueip', 'value': '1.2.3.4', 'id': 298346936}],
                    [{'env': 'hueuser', 'value': '7da7a68792t3r', 'id': 23164382}],
                    [],
                    [],
                    [],
                    [],
                    [],
                    [],
                    [],
                    ])
def test_instellingenget_geenjsessionidengeenuserpass(mock_dbgetbyquery, client):
  response = client.get('/thuis/instellingen')
  assert b"<h1>Instellingen</h1>" in response.data
  assert b"id=\"userid\" name=\"userid\"" in response.data
  assert b"id=\"password\" name=\"password\"" in response.data
  assert mock_dbgetbyquery.call_count == 11


@patch('pysondb.db.JsonDatabase.add')
@patch('gegevens.Gegevens.verwijder')
def test_loginpaginapost_save(mock_deleteenv, mock_dbadd, client):
  data = {'actie': 'login', 'userid': 'dummy', 'password': '<PASSWORD>', 'savelogin': 'on'}
  response = client.post('/thuis/instellingen', data=data)

  assert response.status_code == 302
  assert b"<h1>Redirecting...</h1>" in response.data
  assert b"/thuis/instellingen" in response.data
  assert mock_dbadd.call_count == 3
  assert mock_deleteenv.call_count == 3


@patch('pysondb.db.JsonDatabase.add')
def test_loginpaginapost_nosave(mock_dbadd, client):
  data = {'actie': 'login', 'userid': 'dummy', 'password': '<PASSWORD>', 'savelogin': 'off'}
  response = client.post('/thuis/instellingen', data=data)

  assert response.status_code == 302
  assert b"<h1>Redirecting...</h1>" in response.data
  assert b"/thuis/instellingen" in response.data
  assert mock_dbadd.call_count == 1


@patch('pysondb.db.JsonDatabase.getByQuery',
       side_effect=[[{'env': 'pod', 'value': 'oldvalue', 'id': 92374834}],
                    ])
@patch('pysondb.db.JsonDatabase.deleteById',
       return_value=None)
@patch('pysondb.db.JsonDatabase.add')
def test_instellingen_pod(mock_dbadd, mock_dbdelete, mock_dbget, client):
  data = {'actie': 'updatepod', 'pod': 'dummy'}
  response = client.post('/thuis/instellingen', data=data)

  assert response.status_code == 302
  assert b"<h1>Redirecting...</h1>" in response.data
  assert b"/thuis" in response.data
  assert mock_dbadd.call_count == 1
  assert mock_dbdelete.call_count == 1
  assert mock_dbget.call_count == 1


@patch('pysondb.db.JsonDatabase.getByQuery',
       side_effect=[[{'env': 'hueip', 'value': 'oldvalue', 'id': 192639182}],
                    ])
@patch('pysondb.db.JsonDatabase.deleteById',
       return_value=None)
@patch('pysondb.db.JsonDatabase.add')
def test_hueippaginapost(mock_dbadd, mock_dbdelete, mock_dbget, client):
  data = {'actie': 'updatehueip', 'hueip': 'dummy'}
  response = client.post('/thuis/instellingen', data=data)

  assert response.status_code == 302
  assert b"<h1>Redirecting...</h1>" in response.data
  assert b"/thuis/instellingen" in response.data
  assert mock_dbadd.call_count == 1
  assert mock_dbdelete.call_count == 1
  assert mock_dbget.call_count == 1


@patch('pysondb.db.JsonDatabase.getByQuery',
       side_effect=[[{'env': 'hueuser', 'value': 'oldvalue', 'id': 192639182}],
                    ])
@patch('pysondb.db.JsonDatabase.deleteById',
       return_value=None)
@patch('pysondb.db.JsonDatabase.add')
def test_hueuserpaginapost(mock_dbadd, mock_dbdelete, mock_dbget, client):
  data = {'actie': 'updatehueuser', 'hueuser': 'dummy'}
  response = client.post('/thuis/instellingen', data=data)

  assert response.status_code == 302
  assert b"<h1>Redirecting...</h1>" in response.data
  assert b"/thuis/instellingen" in response.data
  assert mock_dbadd.call_count == 1
  assert mock_dbdelete.call_count == 1
  assert mock_dbget.call_count == 1


@patch('pysondb.db.JsonDatabase.getByQuery',
       side_effect=[[{'env': 'gridbreedte', 'value': 2, 'id': 13478564}],
                    [{'env': 'gridhoogte', 'value': 5, 'id': 923784393}],
                    ])
@patch('pysondb.db.JsonDatabase.deleteById',
       return_value=None)
@patch('pysondb.db.JsonDatabase.add')
def test_gridpaginapost(mock_dbadd, mock_dbdelete, mock_dbget, client):
  data = {'actie': 'updategrid', 'gridhoogte': 7, 'gridbreedte': 8}
  response = client.post('/thuis/instellingen', data=data)

  assert response.status_code == 302
  assert b"<h1>Redirecting...</h1>" in response.data
  assert b"/thuis/instellingen" in response.data
  assert mock_dbadd.call_count == 2
  assert mock_dbdelete.call_count == 2
  assert mock_dbget.call_count == 2


@patch('pysondb.db.JsonDatabase.getByQuery',
       side_effect=[[{'env': 'pod', 'value': '1234-4321-5678', 'id': 28234834}],
                    [{'env': 'jsessionid', 'value': 'E3~1234CAFE5678DECA', 'id': 286349129001}],
                    [],
                    [],
                    [{'env': 'userid', 'value': 'email@adres.com', 'id': 23649273}],
                    [{'env': 'password', 'value': 'password', 'id': 9852364}],
                    [],
                    [],
                    [],
                    [],
                    [],
                    ])
@patch('somfy.Somfy.getavailabletokens',
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
def test_instellingenpaginaget(mock_getavailabletokens, mock_dbgetbyquery, client):
  response = client.get('/thuis/instellingen')

  assert b"<h1>Instellingen</h1>" in response.data
  assert b"<td>Thuis token</td>" in response.data
  assert b"<td>2025-02-01 1" in response.data
  assert b":10:50</td>" in response.data
  assert mock_dbgetbyquery.call_count == 11
  assert mock_getavailabletokens.call_count == 1


@patch('pysondb.db.JsonDatabase.getByQuery',
       side_effect=[[{'env': 'pod', 'value': '1234-4321-5678', 'id': 28234834}],
                    [{'env': 'jsessionid', 'value': 'E3~1234CAFE5678DECA', 'id': 286349129001}],
                    [],
                    [],
                    [],
                    [],
                    [],
                    [],
                    [],
                    [],
                    ])
@patch('pysondb.db.JsonDatabase.deleteById',
       return_value=None)
@patch('somfy.Somfy.getavailabletokens', return_value={'error': 'unauthorized'})
def test_instellingenpaginaget_geensessie(mock_getavailabletokens, mock_dbdelete, mock_dbquery, client):
  response = client.get('/thuis/instellingen')

  assert response.status_code == 302
  assert b"Redirecting..." in response.data
  assert b"/thuis" in response.data
  assert mock_dbquery.call_count == 10
  assert mock_dbdelete.call_count == 0
  assert mock_getavailabletokens.call_count == 1


@patch('pysondb.db.JsonDatabase.getByQuery',
       side_effect=[[{'env': 'pod', 'value': '1234-4321-5678', 'id': 28234834}],
                    [{'env': 'jsessionid', 'value': 'E3~1234CAFE5678DECA', 'id': 286349129001}],
                    [{'env': 'hueip', 'value': '1.2.3.4', 'id': 298346936}],
                    [{'env': 'hueuser', 'value': '7da7a68792t3r', 'id': 23164382}],
                    [{'env': 'userid', 'value': 'email@adres.com', 'id': 236910029}],
                    [{'env': 'password', 'value': 'password', 'id': 236910029}],
                    [],
                    [],
                    [],
                    [{'env': 'jsessionid', 'value': 'E3~1234CAFE5678DECA', 'id': 286349129001}],
                    ])
@patch('pysondb.db.JsonDatabase.deleteById',
       return_value=None)
@patch('pysondb.db.JsonDatabase.add',
       return_value=None)
@patch('somfy.Somfy.getavailabletokens',
       side_effect=[{'error': 'unauthorized'}])
def test_instellingenpaginaget_invalidsessie_login(mock_getavailabletokens, mock_dbadd, mock_dbdelete, mock_dbquery,
                                                   client):
  response = client.get('/thuis/instellingen')

  assert response.status_code == 302
  assert b"<h1>Redirecting...</h1>" in response.data
  assert b"/thuis/instellingen" in response.data
  assert mock_dbquery.call_count == 10
  assert mock_getavailabletokens.call_count == 1
  assert mock_dbdelete.call_count == 1
  assert mock_dbadd.call_count == 0


@patch('pysondb.db.JsonDatabase.getByQuery',
       side_effect=[[],
                    [{'env': 'jsessionid', 'value': 'E3~1234CAFE5678DECA', 'id': 286349129001}],
                    [],
                    [],
                    [],
                    [],
                    [],
                    [],
                    [],
                    [],
                    [],
                    ])
@patch('somfy.Somfy.getavailabletokens', return_value=[{'data': 'dummytoken'}])
def test_instellingenpaginaget_geenpod(mock_getavailabletokens, mock_dbquery, client):
  response = client.get('/thuis/instellingen')

  assert response.status_code == 200
  assert b"<h1>Instellingen</h1>" in response.data
  assert b"Voor de werking is het nummer van de POD nodig" in response.data
  assert b"dummytoken" not in response.data
  assert mock_dbquery.call_count == 11
  assert mock_getavailabletokens.call_count == 0


@patch('pysondb.db.JsonDatabase.getByQuery',
       side_effect=[[{'env': 'pod', 'value': '1234-4321-5678', 'id': 28234834}],
                    [],
                    [{'env': 'hueip', 'value': '1.2.3.4', 'id': 298346936}],
                    [{'env': 'hueuser', 'value': '7da7a68792t3r', 'id': 23164382}],
                    [{'env': 'userid', 'value': 'email@adres.com', 'id': 236910029}],
                    [{'env': 'password', 'value': 'password', 'id': 236910029}],
                    [],
                    [],
                    [],
                    [],
                    [],
                    [],
                    ])
@patch('somfy.Somfy.getavailabletokens',
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
@patch('somfy.Somfy.login', return_value='E3~5678CAFE1234DECA')
@patch('pysondb.db.JsonDatabase.add')
def test_instellingenpaginaget_geenjsessionid_autologin(mock_adddb, mock_somfylogin, mock_getavailabletokens,
                                                        mock_dbquery, client):
  response = client.get('/thuis/instellingen')

  assert response.status_code == 200
  assert b"<h1>Instellingen</h1>" in response.data
  assert b"<td>Thuis token</td>" in response.data
  assert b"<td>2025-02-01 1" in response.data
  assert b":10:50</td>" in response.data
  assert mock_somfylogin.call_count == 1
  assert mock_dbquery.call_count == 12
  assert mock_getavailabletokens.call_count == 1
  assert mock_adddb.call_count == 1


@patch('pysondb.db.JsonDatabase.getByQuery',
       side_effect=[[{'env': 'pod', 'value': '1234-4321-5678', 'id': 28234834}],
                    [{'env': 'jsessionid', 'value': 'E3~1234CAFE5678DECA', 'id': 286349129001}],
                    [],
                    [],
                    [],
                    [],
                    [],
                    [],
                    [],
                    [],
                    ])
@patch('somfy.Somfy.getavailabletokens',
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
@patch('somfy.Somfy.deletetoken', return_value=200)
def test_instellingenpaginapost_delete(mock_deletetoken, mock_gettokens, mock_getquery, client):
  data = {'actie': 'delete', 'uuid': '20547c11-73ce-475b-88be-6e30824b2b54'}
  response = client.post('/thuis/instellingen', data=data)
  assert b"<h1>Redirecting...</h1>" in response.data
  assert b"/thuis/instellingen" in response.data
  assert mock_gettokens.call_count == 0
  assert mock_getquery.call_count == 2
  assert mock_deletetoken.call_count == 1


@patch('pysondb.db.JsonDatabase.getByQuery',
       side_effect=[[{'env': 'pod', 'value': '1234-4321-5678', 'id': 28234834}],
                    [{'env': 'jsessionid', 'value': 'E3~1234CAFE5678DECA', 'id': 286349129001}],
                    [],
                    [],
                    [],
                    [],
                    [],
                    [],
                    [],
                    ])
@patch('somfy.Somfy.getavailabletokens',
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
@patch('somfy.Somfy.createtoken')
@patch('gegevens.Gegevens.wijzig')
def test_instellingenpaginapost_createtoken(mock_gegevens, mock_createtoken, mock_gettokens, mock_dbquery, client):
  data = {'actie': 'create', 'label': 'dummy label'}
  response = client.post('/thuis/instellingen', data=data)

  assert b"<h1>Redirecting...</h1>" in response.data
  assert b"/thuis/instellingen" in response.data
  assert mock_gettokens.call_count == 0
  assert mock_dbquery.call_count == 2
  assert mock_createtoken.call_count == 1
  assert mock_gegevens.call_count == 1


@patch('pysondb.db.JsonDatabase.getByQuery',
       side_effect=[[{'env': 'zonsterktelampen', 'value': 375, 'id': 92374019283}],
                    [{'env': 'starttijd', 'value': 10, 'id': 3937243}],
                    [{'env': 'eindtijd', 'value': 21, 'id': 8237849237}],
                    ])
@patch('pysondb.db.JsonDatabase.deleteById', return_value=None)
@patch('pysondb.db.JsonDatabase.add')
def test_instellingenpaginapost_zonsterkte(mock_dbadd, mock_dbdel, mock_dbget, client):
  data = {'actie': 'updateautolampen',
          'zonsterkte': '350',
          'starttijd': '9',
          'eindtijd': '23',
          }
  response = client.post('/thuis/instellingen', data=data)
  assert b"<h1>Redirecting...</h1>" in response.data
  assert b"/thuis/instellingen" in response.data
  assert mock_dbadd.call_count == 3
  assert mock_dbdel.call_count == 3
  assert mock_dbget.call_count == 3


@patch('pysondb.db.JsonDatabase.getByQuery',
       side_effect=[[{'env': 'hueip', 'value': '1.2.3.4', 'id': 298346936}],
                    [{'env': 'hueuser', 'value': '7da7a68792t3r', 'id': 23164382}],
                    [],
                    [{'env': 'gridbreedte', 'value': 2, 'id': 13478564}],
                    [{'env': 'gridhoogte', 'value': 5, 'id': 923784393}],
                    [{"env": "lampen",
                      "value": [{"id": "dummyaan_id", "naam": "dummyaan", "volgorde": 11},
                                {"id": "dummyuit_id", "naam": "dummyuit", "volgorde": 12},
                                {"id": "dummydimbaar_id", "naam": "dummydimbaar", "volgorde": 21}],
                      "id": 293874398
                      }
                     ],
                    [{'env': 'gridbreedte', 'value': 2, 'id': 13478564}],
                    [{'env': 'gridhoogte', 'value': 5, 'id': 923784393}],
                    [],
                    ]
       )
@patch('requests.get')
@patch('pysondb.db.JsonDatabase.add')
@patch('thuis.haalzonnesterkte', side_effect=[{'value': 123}])
def test_lampenpagina(mock_zonnesterkte, mock_envadd, mock_requestsget, mock_env, client):
  mock_requestsget.return_value = maakmockresponse({'errors': [],
                                                    'data': [{'id': 'dummyaan_id',
                                                              'metadata': {'name': 'dummyaan'},
                                                              'on': {'on': True}
                                                              },
                                                             {'id': 'dummyuit_id',
                                                              'metadata': {'name': 'dummyuit'},
                                                              'on': {'on': False}
                                                              },
                                                             {'id': 'dummydimbaar_id',
                                                              'metadata': {'name': 'dummydimbaar'},
                                                              'on': {'on': False},
                                                              'dimming': {'brightness': 23.34},
                                                              'color': {'xy': {'x': 0.5612, 'y': 0.4042}}
                                                              }
                                                             ]}
                                                   )
  response = client.get('/thuis/lampen')

  assert b"<h1>Lampen</h1>" in response.data
  assert b">dummyaan<" in response.data
  assert b">Aan<" in response.data
  assert b">dummyuit<" in response.data
  assert b">Uit<" in response.data
  assert b">dummydimbaar<" in response.data
  assert b"value=\"23.34\">" in response.data
  assert mock_requestsget.call_count == 1
  assert mock_env.call_count == 8
  assert mock_envadd.call_count == 1
  assert mock_zonnesterkte.call_count == 1


@patch('pysondb.db.JsonDatabase.getByQuery',
       side_effect=[[{'env': 'hueip', 'value': '1.2.3.4', 'id': 298346936}],
                    [{'env': 'hueuser', 'value': '7da7a68792t3r', 'id': 23164382}],
                    [],
                    [],
                    [],
                    [{"env": "lampen",
                      "value": [{"id": "dummyaan_id", "naam": "dummyaan", "volgorde": 11},
                                {"id": "dummyuit_id", "naam": "dummyuit", "volgorde": 12},
                                {"id": "dummydimbaar_id", "naam": "dummydimbaar", "volgorde": 21}],
                      "id": 293874398
                      }
                     ],
                    [{'env': 'gridbreedte', 'value': 3, 'id': 13478564}],
                    [{'env': 'gridhoogte', 'value': 4, 'id': 923784393}],
                    [],
                    ]
       )
@patch('requests.get')
@patch('pysondb.db.JsonDatabase.add')
@patch('thuis.haalzonnesterkte', side_effect=[{'value': 123}])
def test_lampenpagina_defaultgrid(mock_zonnesterkte, mock_envadd, mock_requestsget, mock_env, client):
  mock_requestsget.return_value = maakmockresponse({'errors': [],
                                                    'data': [{'id': 'dummyaan_id',
                                                              'metadata': {'name': 'dummyaan'},
                                                              'on': {'on': True}
                                                              },
                                                             {'id': 'dummyuit_id',
                                                              'metadata': {'name': 'dummyuit'},
                                                              'on': {'on': False}
                                                              },
                                                             {'id': 'dummydimbaar_id',
                                                              'metadata': {'name': 'dummydimbaar'},
                                                              'on': {'on': False},
                                                              'dimming': {'brightness': 23.34},
                                                              'color': {'xy': {'x': 0.5612, 'y': 0.4042}}
                                                              }
                                                             ]}
                                                   )
  response = client.get('/thuis/lampen')

  assert b"<h1>Lampen</h1>" in response.data
  assert b">dummyaan<" in response.data
  assert b">Aan<" in response.data
  assert b">dummyuit<" in response.data
  assert b">Uit<" in response.data
  assert b">dummydimbaar<" in response.data
  assert b"value=\"23.34\">" in response.data
  assert mock_requestsget.call_count == 1
  assert mock_env.call_count == 8
  assert mock_envadd.call_count == 3
  assert mock_zonnesterkte.call_count == 1


@patch('pysondb.db.JsonDatabase.getByQuery',
       side_effect=[[],
                    [{'env': 'hueuser', 'value': '7da7a68792t3r', 'id': 23164382}],
                    ]
       )
@patch('requests.get')
def test_lampenpagina_missendegegevens(mock_requestsget, mock_env, client):
  mock_requestsget.return_value = maakmockresponse({'errors': [],
                                                    'data': [{'metadata': {'name': 'dummy'},
                                                              'on': {'on': True}
                                                              }]}
                                                   )
  response = client.get('/thuis/lampen')

  assert response.status_code == 302
  assert b"<h1>Redirecting...</h1>" in response.data
  assert b"/thuis" in response.data
  assert mock_requestsget.call_count == 0
  assert mock_env.call_count == 2


@patch('pysondb.db.JsonDatabase.getByQuery',
       side_effect=[[{'env': 'hueip', 'value': '1.2.3.4', 'id': 298346936}],
                    [{'env': 'hueuser', 'value': '7da7a68792t3r', 'id': 23164382}],
                    [],
                    ]
       )
@patch('requests.get')
def test_lampenpagina_error(mock_requestsget, mock_env, client):
  mock_requestsget.return_value = maakmockresponse({'errors': [{'error': 'error'}],
                                                    'data': [{'metadata': {'name': 'dummy'},
                                                              'on': {'on': True}
                                                              }]}
                                                   )
  response = client.get('/thuis/lampen')

  assert response.status_code == 302
  assert b"<h1>Redirecting...</h1>" in response.data
  assert b"/thuis" in response.data
  assert mock_requestsget.call_count == 1
  assert mock_env.call_count == 3


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
def test_schermenpagina(mock_wind, mock_somfy, mock_env, mock_env_weerapikey, client):
  response = client.get('/thuis/schermen')

  assert b"<h1>Schermen</h1>" in response.data
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
def test_schermenpagina_geenpod(mock_wind, mock_somfy, mock_env, mock_env_weerapikey, client):
  response = client.get('/thuis/schermen')

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
def test_schermenpagina_geenschermcache(mock_wind, mock_somfy, mock_schermen, mock_envquery, mock_env_weerapikey,
                                        client):
  response = client.get('/thuis/schermen')

  assert b"<h1>Schermen</h1>" in response.data
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
def test_schermenpagina_error(mock_wind, mock_somfy, mock_env, mock_env_weerapikey, client):
  response = client.get('/thuis/schermen')

  assert response.status_code == 302
  assert b"<h1>Redirecting...</h1>" in response.data
  assert b"/thuis" in response.data
  assert mock_env.call_count == 3
  assert mock_somfy.call_count == 1
  assert mock_wind.call_count == 0


@patch('thuis.verplaatsscherm')
def test_schermenpaginapost(mock_verplaats, client):
  data = {'actie': 'zetscherm', 'device': 'dummyid', 'percentage': '20'}
  response = client.post('/thuis/schermen', data=data)

  assert response.status_code == 302
  assert b"<h1>Redirecting...</h1>" in response.data
  assert b"/thuis/schermen" in response.data
  assert mock_verplaats.call_count == 1


@patch('thuis.verplaatsscherm')
def test_schermenpaginapost_geengetal(mock_verplaats, client):
  data = {'actie': 'zetscherm', 'device': 'dummyid', 'percentage': 'abc'}
  response = client.post('/thuis/schermen', data=data)

  assert response.status_code == 302
  assert b"<h1>Redirecting...</h1>" in response.data
  assert b"/thuis/schermen" in response.data
  assert mock_verplaats.call_count == 0


@patch('thuis.sluitalles')
@patch('thuis.openalles')
def test_schermenpaginapost_sluitalles(mock_openalles, mock_sluitalles, client):
  data = {'actie': 'sluitalles', 'device': 'dummyid', 'percentage': 'abc'}
  response = client.post('/thuis/schermen', data=data)

  assert response.status_code == 302
  assert b"<h1>Redirecting...</h1>" in response.data
  assert b"/thuis/schermen" in response.data
  assert mock_openalles.call_count == 0
  assert mock_sluitalles.call_count == 1


@patch('thuis.sluitalles')
@patch('thuis.openalles')
def test_schermenpaginapost_openalles(mock_openalles, mock_sluitalles, client):
  data = {'actie': 'openalles', 'device': 'dummyid', 'percentage': 'abc'}
  response = client.post('/thuis/schermen', data=data)

  assert response.status_code == 302
  assert b"<h1>Redirecting...</h1>" in response.data
  assert b"/thuis/schermen" in response.data
  assert mock_openalles.call_count == 1
  assert mock_sluitalles.call_count == 0


@patch('thuis.sluitalles')
@patch('thuis.openalles')
def test_schermenpaginapost_openalles_vanafhoofdpagina(mock_openalles, mock_sluitalles, client):
  data = {'actie': 'openalles', 'device': 'dummyid', 'percentage': 'abc'}
  headers = {'Referer': '/thuis'}
  response = client.post('/thuis/schermen', data=data, headers=headers)

  assert response.status_code == 302
  assert b"<h1>Redirecting...</h1>" in response.data
  assert b"/thuis" in response.data
  assert mock_openalles.call_count == 1
  assert mock_sluitalles.call_count == 0


@patch('thuis.verversschermen')
def test_schermenpaginapost_ververs(mock_ververs, client):
  data = {'actie': 'ververs'}
  response = client.post('/thuis/schermen', data=data)

  assert response.status_code == 302
  assert b"<h1>Redirecting...</h1>" in response.data
  assert b"/thuis/schermen" in response.data
  assert mock_ververs.call_count == 1


@patch('thuis.doeactieoplamp')
def test_lampenpaginapost_aan(mock_doeactieoplamp, client):
  data = {'actie': 'lampaan', 'lampid': 'dummyid'}
  response = client.post('/thuis/lampen', data=data)

  assert response.status_code == 302
  assert b"<h1>Redirecting...</h1>" in response.data
  assert b"/thuis/lampen" in response.data
  assert mock_doeactieoplamp.call_count == 1


@patch('thuis.doeactieoplamp')
def test_lampenpaginapost_uit(mock_doeactieoplamp, client):
  data = {'actie': 'lampuit', 'lampid': 'dummyid'}
  response = client.post('/thuis/lampen', data=data)

  assert response.status_code == 302
  assert b"<h1>Redirecting...</h1>" in response.data
  assert b"/thuis/lampen" in response.data
  assert mock_doeactieoplamp.call_count == 1


@patch('thuis.doeactieoplamp')
def test_lampenpaginapost_vanhoofdpagina(mock_doeactieoplamp, client):
  data = {'actie': 'lampuit', 'lampid': 'dummyid'}
  headers = {'Referer': '/thuis'}
  response = client.post('/thuis/lampen', data=data, headers=headers)

  assert response.status_code == 302
  assert b"<h1>Redirecting...</h1>" in response.data
  assert b"/thuis" in response.data
  assert mock_doeactieoplamp.call_count == 1


@patch('thuis.doeactieoplamp')
def test_lampenpaginapost_dim(mock_doeactieoplamp, client):
  data = {'actie': 'lampdim', 'lampid': 'dummyid', 'dimwaarde': '12.34'}
  response = client.post('/thuis/lampen', data=data)

  assert response.status_code == 302
  assert b"<h1>Redirecting...</h1>" in response.data
  assert b"/thuis/lampen" in response.data
  assert mock_doeactieoplamp.call_count == 2


@patch('thuis.doeactieoplamp')
def test_lampenpaginapost_kleur(mock_doeactieoplamp, client):
  data = {'actie': 'lampkleur', 'lampid': 'dummyid', 'kleurwaarde': '#a1b2c3'}
  response = client.post('/thuis/lampen', data=data)

  assert response.status_code == 302
  assert b"<h1>Redirecting...</h1>" in response.data
  assert b"/thuis/lampen" in response.data
  assert mock_doeactieoplamp.call_count == 3


@patch('thuis.allelampenuit')
def test_lampenpaginapost_allesuit(mock_allelampenuit, client):
  data = {'actie': 'allesuit'}
  response = client.post('/thuis/lampen', data=data)

  assert response.status_code == 302
  assert b"<h1>Redirecting...</h1>" in response.data
  assert b"/thuis/lampen" in response.data
  assert mock_allelampenuit.call_count == 1


@patch('thuis.ververslampen')
def test_lampenpaginapost_ververs(mock_ververs, client):
  data = {'actie': 'ververs'}
  response = client.post('/thuis/lampen', data=data)

  assert response.status_code == 302
  assert b"<h1>Redirecting...</h1>" in response.data
  assert b"/thuis/lampen" in response.data
  assert mock_ververs.call_count == 1


@patch('pysondb.db.JsonDatabase.getByQuery',
       side_effect=[
         [{'env': 'lampen', 'value': [{"id": "dummyid1", "naam": "Lampnaam1", "volgorde": 11, "automatisch": True},
                                      {"id": "dummyid2", "naam": "Lampnaam2", "volgorde": 22, "automatisch": False}],
           'id': 92734098234}],
         [{'env': 'gridbreedte', 'value': 2, 'id': 13478564}],
         [{'env': 'gridhoogte', 'value': 5, 'id': 923784393}],
       ])
def test_lampengrid(mock_env, client):
  response = client.get('/thuis/lampengrid')
  assert b"<h1>Lampengrid</h1>" in response.data
  assert b">Lampnaam1<" in response.data
  assert b"id=\"dummyid1-plek\"" in response.data
  assert b"value=\"11\"" in response.data
  assert b"id=\"dummyid1-auto\"" in response.data
  assert b">Lampnaam2<" in response.data
  assert b"id=\"dummyid2-plek\"" in response.data
  assert b"value=\"22\"" in response.data
  assert b"id=\"dummyid2-auto\"" in response.data
  assert mock_env.call_count == 3


@patch('pysondb.db.JsonDatabase.getByQuery',
       side_effect=[
         [{'env': 'lampen', 'value': [{"id": "dummyid1", "naam": "Lampnaam1", "volgorde": 11},
                                      {"id": "dummyid2", "naam": "Lampnaam2", "volgorde": 22}], 'id': 92734098234}],
         [{'env': 'gridbreedte', 'value': 2, 'id': 13478564}],
         [{'env': 'gridhoogte', 'value': 5, 'id': 923784393}],
       ])
@patch('pysondb.db.JsonDatabase.deleteById', return_value=None)
@patch('pysondb.db.JsonDatabase.add')
def test_lampengrid_post(mock_add, mock_del, mock_env, client):
  data = {'dummyid1-plek': '11', 'dummyid2-plek': '33', 'dummyid1-auto': 'on'}
  response = client.post('/thuis/lampengrid', data=data)

  assert response.status_code == 302
  assert b"<h1>Redirecting...</h1>" in response.data
  assert b"/thuis" in response.data
  assert mock_env.call_count == 2
  assert mock_del.call_count == 1
  assert mock_add.call_count == 1
