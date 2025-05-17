from unittest.mock import patch

from freezegun import freeze_time

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


@patch('pysondb.db.JsonDatabase.getByQuery',
       side_effect=[[{'key': 'zonnesterkte', 'value': 1234, 'id': 29346023}],
                    ])
@patch('pysondb.db.JsonDatabase.add')
def test_haalzonnesterkteuitdb(mock_envdbadd, mock_zondbget):
  resultaat = thuis.haalzonnesterkteuitdb()

  assert resultaat == 1234
  assert mock_zondbget.call_count == 1
  assert mock_envdbadd.call_count == 0


@patch('pysondb.db.JsonDatabase.getByQuery',
       side_effect=[[],
                    ])
@patch('pysondb.db.JsonDatabase.add')
def test_haalzonnesterkteuitdb_nieuw(mock_envdbadd, mock_zondbget):
  resultaat = thuis.haalzonnesterkteuitdb()

  assert resultaat == 0
  assert mock_zondbget.call_count == 1
  assert mock_envdbadd.call_count == 1


@patch('thuis.haalzonnesterkteuitdb', return_value=600)
@patch('thuis.haalzonnesterkte', return_value=400)
@patch('thuis.schakellampenaan')
@patch('pysondb.db.JsonDatabase.updateByQuery')
@freeze_time("2025-05-17 17:01:02")
def test_checkzonnesterkte_hoog_laag(mock_updatedb, mock_schakelaan, mock_haalzonnesterkte, mock_haaluitdb):
  thuis.checkzonnesterkte()

  assert mock_haaluitdb.call_count == 1
  assert mock_haalzonnesterkte.call_count == 1
  assert mock_schakelaan.call_count == 1
  assert mock_updatedb.call_count == 1


@patch('thuis.haalzonnesterkteuitdb', return_value=4321)
@patch('thuis.haalzonnesterkte', return_value=4000)
@patch('thuis.schakellampenaan')
@patch('pysondb.db.JsonDatabase.updateByQuery')
@freeze_time("2025-05-17 17:01:02")
def test_checkzonnesterkte_hoog_hoog(mock_updatedb, mock_schakelaan, mock_haalzonnesterkte, mock_haaluitdb):
  thuis.checkzonnesterkte()

  assert mock_haaluitdb.call_count == 1
  assert mock_haalzonnesterkte.call_count == 1
  assert mock_schakelaan.call_count == 0
  assert mock_updatedb.call_count == 1


@patch('thuis.haalzonnesterkteuitdb', return_value=300)
@patch('thuis.haalzonnesterkte', return_value=350)
@patch('thuis.schakellampenaan')
@patch('pysondb.db.JsonDatabase.updateByQuery')
@freeze_time("2025-05-17 17:01:02")
def test_checkzonnesterkte_laag_laag(mock_updatedb, mock_schakelaan, mock_haalzonnesterkte, mock_haaluitdb):
  thuis.checkzonnesterkte()

  assert mock_haaluitdb.call_count == 1
  assert mock_haalzonnesterkte.call_count == 1
  assert mock_schakelaan.call_count == 0
  assert mock_updatedb.call_count == 1


@patch('thuis.haalzonnesterkteuitdb', return_value=490)
@patch('thuis.haalzonnesterkte', return_value=600)
@patch('thuis.schakellampenaan')
@patch('pysondb.db.JsonDatabase.updateByQuery')
@freeze_time("2025-05-17 17:01:02")
def test_checkzonnesterkte_laag_hoog(mock_updatedb, mock_schakelaan, mock_haalzonnesterkte, mock_haaluitdb):
  thuis.checkzonnesterkte()

  assert mock_haaluitdb.call_count == 1
  assert mock_haalzonnesterkte.call_count == 1
  assert mock_schakelaan.call_count == 0
  assert mock_updatedb.call_count == 1


@patch('thuis.haalzonnesterkteuitdb', return_value=600)
@patch('thuis.haalzonnesterkte', return_value=400)
@patch('thuis.schakellampenaan')
@patch('pysondb.db.JsonDatabase.updateByQuery')
@freeze_time("2025-05-17 08:34:56")
def test_checkzonnesterkte_vroeg(mock_updatedb, mock_schakelaan, mock_haalzonnesterkte, mock_haaluitdb):
  thuis.checkzonnesterkte()

  assert mock_haaluitdb.call_count == 1
  assert mock_haalzonnesterkte.call_count == 1
  assert mock_schakelaan.call_count == 0
  assert mock_updatedb.call_count == 1


@patch('thuis.haalzonnesterkteuitdb', return_value=600)
@patch('thuis.haalzonnesterkte', return_value=400)
@patch('thuis.schakellampenaan')
@patch('pysondb.db.JsonDatabase.updateByQuery')
@freeze_time("2025-05-17 23:45:12")
def test_checkzonnesterkte_laat(mock_updatedb, mock_schakelaan, mock_haalzonnesterkte, mock_haaluitdb):
  thuis.checkzonnesterkte()

  assert mock_haaluitdb.call_count == 1
  assert mock_haalzonnesterkte.call_count == 1
  assert mock_schakelaan.call_count == 0
  assert mock_updatedb.call_count == 1


@patch('thuis.verstuurberichtmonitoring')
def test_schakellampenaan(mock_bericht):
  thuis.schakellampenaan(654, 321)

  assert mock_bericht.call_count == 1
