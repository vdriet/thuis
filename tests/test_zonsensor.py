from unittest.mock import patch

import thuis


@patch('pysondb.db.JsonDatabase.getByQuery',
       side_effect=[[{'env': 'token', 'value': 'token', 'id': 286349129001}],
                    [{'env': 'pod', 'value': '1234-4321-5678', 'id': 28234834}],
                    [{'env': 'sensors',
                      'value': [{"label": "zonsensor", "device": "io://1234-4321-5678/93682392"}]}],
                    ])
@patch('thuis.haalzonnesensors',
       side_effect=[{"label": "zonsensor", "device": "io://1234-4321-5678/93682392"}])
@patch('thuis.haalgegevensvansomfy',
       side_effect=[{'value': 1234}])
def test_haalzonnesterkte(mock_somfy, mock_sensors, mock_envdb):
  resultaat = thuis.haalzonnesterkte()

  assert resultaat == 1234
  assert mock_envdb.call_count == 3
  assert mock_sensors.call_count == 0
  assert mock_somfy.call_count == 1


@patch('pysondb.db.JsonDatabase.getByQuery',
       side_effect=[[{'env': 'token', 'value': 'token', 'id': 286349129001}],
                    [{'env': 'pod', 'value': '1234-4321-5678', 'id': 28234834}],
                    [{'env': 'sensors',
                      'value': [{"label": "zonsensor", "device": "io://1234-4321-5678/93682392"}]}],
                    ])
@patch('thuis.haalgegevensvansomfy',
       side_effect=[{'value': 4321}])
def test_haalzonnesterkte_uitcache(mock_somfy, mock_envdb):
  resultaat = thuis.haalzonnesterkte()

  assert resultaat == 1234
  assert mock_envdb.call_count == 0
  assert mock_somfy.call_count == 0


@patch('pysondb.db.JsonDatabase.getByQuery',
       side_effect=[[],
                    [{'env': 'pod', 'value': '1234-4321-5678', 'id': 28234834}],
                    [{'env': 'sensors',
                      'value': [{"label": "zonsensor", "device": "io://1234-4321-5678/93682392"}]}],
                    ])
@patch('thuis.haalgegevensvansomfy',
       side_effect=[{'value': 2345}])
def test_haalzonnesterkte_geentoken(mock_somfy, mock_envdb):
  thuis.haalzonnesterkte.cache_clear()
  resultaat = thuis.haalzonnesterkte()

  assert resultaat == -1
  assert mock_envdb.call_count == 2
  assert mock_somfy.call_count == 0


@patch('pysondb.db.JsonDatabase.getByQuery',
       side_effect=[[{'env': 'token', 'value': 'token2', 'id': 286349129001}],
                    [],
                    [{'env': 'sensors',
                      'value': [{"label": "zonsensor", "device": "io://1234-4321-5678/93682392"}]}],
                    ])
@patch('thuis.haalgegevensvansomfy',
       side_effect=[{'value': 3456}])
def test_haalzonnesterkte_geenpod(mock_somfy, mock_envdb):
  thuis.haalzonnesterkte.cache_clear()
  resultaat = thuis.haalzonnesterkte()

  assert resultaat == -1
  assert mock_envdb.call_count == 2
  assert mock_somfy.call_count == 0


@patch('pysondb.db.JsonDatabase.getByQuery',
       side_effect=[[{'env': 'token', 'value': 'token2', 'id': 286349129001}],
                    [{'env': 'pod', 'value': '1234-4321-5678', 'id': 28234834}],
                    [],
                    ])
@patch('thuis.haalzonnesensors',
       side_effect=[[{"label": "zonsensor", "device": "io://1234-4321-5678/93682392"}]])
@patch('thuis.haalgegevensvansomfy',
       side_effect=[{'value': 4567}])
def test_haalzonnesterkte_geensensors(mock_somfy, mock_sensors, mock_envdb):
  thuis.haalzonnesterkte.cache_clear()
  resultaat = thuis.haalzonnesterkte()

  assert resultaat == 4567
  assert mock_envdb.call_count == 3
  assert mock_sensors.call_count == 1
  assert mock_somfy.call_count == 1


@patch('pysondb.db.JsonDatabase.getByQuery',
       side_effect=[[{'env': 'token', 'value': 'token2', 'id': 286349129001}],
                    [{'env': 'pod', 'value': '1234-4321-5678', 'id': 28234834}],
                    [{'env': 'sensors',
                      'value': [{"label": "zonsensor", "device": "io://1234-4321-5678/93682392"}]}],
                    ])
@patch('thuis.haalgegevensvansomfy',
       return_value={'error': 'dummy'})
def test_haalzonnesterkte_somfyerror(mock_somfy, mock_envdb):
  thuis.haalzonnesterkte.cache_clear()
  resultaat = thuis.haalzonnesterkte()

  assert resultaat == -2
  assert mock_envdb.call_count == 3
  assert mock_somfy.call_count == 1


@patch('pysondb.db.JsonDatabase.getByQuery',
       side_effect=[[{'env': 'token', 'value': 'token2', 'id': 286349129001}],
                    [{'env': 'pod', 'value': '1234-4321-5678', 'id': 28234834}],
                    [{'env': 'sensors',
                      'value': []}],
                    ])
@patch('thuis.haalgegevensvansomfy',
       side_effect=[{'value': 4567}])
def test_haalzonnesterkte_geensensor(mock_somfy, mock_envdb):
  thuis.haalzonnesterkte.cache_clear()
  resultaat = thuis.haalzonnesterkte()

  assert resultaat == -4
  assert mock_envdb.call_count == 3
  assert mock_somfy.call_count == 0


@patch('pysondb.db.JsonDatabase.add')
@patch('thuis.haalgegevensvansomfy',
       side_effect=[['io://sensorurl'],
                    {'label': 'zonlabel'}])
def test_haalzonnesensors(mock_somfy, mock_envdbadd):
  resultaat = thuis.haalzonnesensors('pod', 'token')

  assert resultaat == [{'label': 'zonlabel', 'device': 'io://sensorurl'}]
  assert mock_envdbadd.call_count == 1
  assert mock_somfy.call_count == 2
