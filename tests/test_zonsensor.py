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
@patch('somfy.Somfy.haalgegevens',
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
@patch('somfy.Somfy.haalgegevens',
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
@patch('somfy.Somfy.haalgegevens',
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
@patch('somfy.Somfy.haalgegevens',
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
@patch('somfy.Somfy.haalgegevens',
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
@patch('somfy.Somfy.haalgegevens',
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
                    [{'env': 'sensors', 'value': []}],
                    ])
@patch('somfy.Somfy.haalgegevens',
       side_effect=[{'value': 4567}])
@patch('thuis.haalzonnesensors', return_value=[])
def test_haalzonnesterkte_geensensor(mock_haalsensors, mock_somfy, mock_envdb):
  thuis.haalzonnesterkte.cache_clear()
  resultaat = thuis.haalzonnesterkte()

  assert resultaat == -4
  assert mock_envdb.call_count == 3
  assert mock_somfy.call_count == 0
  assert mock_haalsensors.call_count == 1


@patch('pysondb.db.JsonDatabase.add')
@patch('somfy.Somfy.haalgegevens',
       side_effect=[['io://sensorurl'],
                    {'label': 'zonlabel'}])
def test_haalzonnesensors(mock_somfy, mock_envdbadd):
  resultaat = thuis.haalzonnesensors('pod', 'token')

  assert resultaat == [{'label': 'zonlabel', 'device': 'io://sensorurl'}]
  assert mock_envdbadd.call_count == 1
  assert mock_somfy.call_count == 2


@patch('pysondb.db.JsonDatabase.getByQuery',
       side_effect=[[{'env': 'zonnesterkte', 'value': 1234, 'id': 29346023}],
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


@patch('thuis.haalzonnesterkteuitdb', return_value=978)
@patch('thuis.haalzonnesterkte', return_value=976)
@patch('thuis.schakellampenaan')
@patch('thuis.schakellampenuit')
@patch('pysondb.db.JsonDatabase.add')
@patch('pysondb.db.JsonDatabase.deleteById')
@patch('pysondb.db.JsonDatabase.getByQuery',
       side_effect=[[{'env': 'zonsterktelampen', 'value': 977, 'id': 9712382}],
                    [{'env': 'starttijd', 'value': 9, 'id': 13287633}],
                    [{'env': 'eindtijd', 'value': 23, 'id': 92379283}],
                    [],
                    ])
@freeze_time("2025-05-17 17:01:02")
def test_checkzonnesterkte_hoog_laag(mock_leesdb, mock_del, mock_add, mock_schakeluit, mock_schakelaan,
                                     mock_haalzonnesterkte,
                                     mock_haaluitdb):
  thuis.checkzonnesterkte()

  assert mock_haaluitdb.call_count == 1
  assert mock_haalzonnesterkte.call_count == 1
  assert mock_schakelaan.call_count == 1
  assert mock_schakeluit.call_count == 0
  assert mock_add.call_count == 1
  assert mock_del.call_count == 0
  assert mock_leesdb.call_count == 4


@patch('thuis.haalzonnesterkteuitdb', return_value=4321)
@patch('thuis.haalzonnesterkte', return_value=4000)
@patch('thuis.schakellampenaan')
@patch('thuis.schakellampenuit')
@patch('pysondb.db.JsonDatabase.getByQuery',
       side_effect=[[{'env': 'zonsterktelampen', 'value': 400, 'id': 9712382}],
                    [{'env': 'starttijd', 'value': 9, 'id': 13287633}],
                    [{'env': 'eindtijd', 'value': 23, 'id': 92379283}],
                    [],
                    ])
@patch('pysondb.db.JsonDatabase.add')
@freeze_time("2025-05-17 17:01:02")
def test_checkzonnesterkte_hoog_hoog(mock_adddb, mock_leesdb, mock_schakeluit, mock_schakelaan, mock_haalzonnesterkte,
                                     mock_haaluitdb):
  thuis.checkzonnesterkte()

  assert mock_haaluitdb.call_count == 1
  assert mock_haalzonnesterkte.call_count == 1
  assert mock_schakelaan.call_count == 0
  assert mock_schakeluit.call_count == 0
  assert mock_leesdb.call_count == 4
  assert mock_adddb.call_count == 1


@patch('thuis.haalzonnesterkteuitdb', return_value=401)
@patch('thuis.haalzonnesterkte', return_value=399)
@patch('thuis.schakellampenaan')
@patch('thuis.schakellampenuit')
@patch('pysondb.db.JsonDatabase.add')
@patch('pysondb.db.JsonDatabase.deleteById')
@patch('pysondb.db.JsonDatabase.getByQuery',
       side_effect=[[{'env': 'zonsterktelampen', 'value': None, 'id': 2983749273}],
                    [{'env': 'starttijd', 'value': 9, 'id': 13287633}],
                    [{'env': 'eindtijd', 'value': 23, 'id': 92379283}],
                    [],
                    ])
@freeze_time("2025-05-17 17:01:02")
def test_checkzonnesterkte_hoog_laag_default(mock_leesdb, mock_delete, mock_add, mock_schakeluit, mock_schakelaan,
                                             mock_haalzonnesterkte, mock_haaluitdb):
  thuis.checkzonnesterkte()

  assert mock_haaluitdb.call_count == 1
  assert mock_haalzonnesterkte.call_count == 1
  assert mock_schakelaan.call_count == 1
  assert mock_schakeluit.call_count == 0
  assert mock_add.call_count == 1
  assert mock_delete.call_count == 0
  assert mock_leesdb.call_count == 4


@patch('thuis.haalzonnesterkteuitdb', return_value=300)
@patch('thuis.haalzonnesterkte', return_value=350)
@patch('thuis.schakellampenaan')
@patch('thuis.schakellampenuit')
@patch('pysondb.db.JsonDatabase.getByQuery',
       side_effect=[[{'env': 'zonsterktelampen', 'value': 400, 'id': 9712382}],
                    [{'env': 'starttijd', 'value': 9, 'id': 13287633}],
                    [{'env': 'eindtijd', 'value': 23, 'id': 92379283}],
                    [],
                    ])
@patch('pysondb.db.JsonDatabase.add')
@freeze_time("2025-05-17 17:01:02")
def test_checkzonnesterkte_laag_laag(mock_adddb, mock_leesdb, mock_schakeluit, mock_schakelaan, mock_haalzonnesterkte,
                                     mock_haaluitdb):
  thuis.checkzonnesterkte()

  assert mock_haaluitdb.call_count == 1
  assert mock_haalzonnesterkte.call_count == 1
  assert mock_schakelaan.call_count == 0
  assert mock_schakeluit.call_count == 0
  assert mock_leesdb.call_count == 4
  assert mock_adddb.call_count == 1


@patch('thuis.haalzonnesterkteuitdb', return_value=390)
@patch('thuis.haalzonnesterkte', return_value=500)
@patch('thuis.schakellampenaan')
@patch('thuis.schakellampenuit')
@patch('pysondb.db.JsonDatabase.getByQuery',
       side_effect=[[{'env': 'zonsterktelampen', 'value': 400, 'id': 9712382}],
                    [{'env': 'starttijd', 'value': 9, 'id': 13287633}],
                    [{'env': 'eindtijd', 'value': 23, 'id': 92379283}],
                    [],
                    ])
@patch('pysondb.db.JsonDatabase.add')
@freeze_time("2025-05-17 17:01:02")
def test_checkzonnesterkte_laag_hoog(mock_adddb, mock_leesdb, mock_schakeluit, mock_schakelaan, mock_haalzonnesterkte,
                                     mock_haaluitdb):
  thuis.checkzonnesterkte()

  assert mock_haaluitdb.call_count == 1
  assert mock_haalzonnesterkte.call_count == 1
  assert mock_schakelaan.call_count == 0
  assert mock_schakeluit.call_count == 1
  assert mock_leesdb.call_count == 4
  assert mock_adddb.call_count == 1


@patch('thuis.haalzonnesterkteuitdb', return_value=600)
@patch('thuis.haalzonnesterkte', return_value=400)
@patch('thuis.schakellampenaan')
@patch('thuis.schakellampenuit')
@patch('pysondb.db.JsonDatabase.getByQuery',
       side_effect=[[{'env': 'zonsterktelampen', 'value': 400, 'id': 9712382}],
                    [{'env': 'starttijd', 'value': 15, 'id': 13287633}],
                    [{'env': 'eindtijd', 'value': 23, 'id': 92379283}],
                    [],
                    ])
@patch('pysondb.db.JsonDatabase.add')
@freeze_time("2025-05-17 14:34:56")
def test_checkzonnesterkte_vroeg(mock_adddb, mock_leesdb, mock_schakeluit, mock_schakelaan, mock_haalzonnesterkte,
                                 mock_haaluitdb):
  thuis.checkzonnesterkte()

  assert mock_haaluitdb.call_count == 1
  assert mock_haalzonnesterkte.call_count == 1
  assert mock_schakelaan.call_count == 0
  assert mock_schakeluit.call_count == 0
  assert mock_leesdb.call_count == 4
  assert mock_adddb.call_count == 1


@patch('thuis.haalzonnesterkteuitdb', return_value=600)
@patch('thuis.haalzonnesterkte', return_value=400)
@patch('thuis.schakellampenaan')
@patch('thuis.schakellampenuit')
@patch('pysondb.db.JsonDatabase.getByQuery',
       side_effect=[[{'env': 'zonsterktelampen', 'value': 400, 'id': 9712382}],
                    [],
                    [{'env': 'eindtijd', 'value': 23, 'id': 92379283}],
                    [],
                    ])
@patch('pysondb.db.JsonDatabase.add')
@freeze_time("2025-05-17 08:34:56")
def test_checkzonnesterkte_vroeg_default(mock_adddb, mock_leesdb, mock_schakeluit, mock_schakelaan,
                                         mock_haalzonnesterkte, mock_haaluitdb):
  thuis.checkzonnesterkte()

  assert mock_haaluitdb.call_count == 1
  assert mock_haalzonnesterkte.call_count == 1
  assert mock_schakelaan.call_count == 0
  assert mock_schakeluit.call_count == 0
  assert mock_leesdb.call_count == 4
  assert mock_adddb.call_count == 1


@patch('thuis.haalzonnesterkteuitdb', return_value=600)
@patch('thuis.haalzonnesterkte', return_value=400)
@patch('thuis.schakellampenaan')
@patch('thuis.schakellampenuit')
@patch('pysondb.db.JsonDatabase.getByQuery',
       side_effect=[[{'env': 'zonsterktelampen', 'value': 400, 'id': 9712382}],
                    [{'env': 'starttijd', 'value': 9, 'id': 13287633}],
                    [{'env': 'eindtijd', 'value': 20, 'id': 92379283}],
                    [],
                    ])
@patch('pysondb.db.JsonDatabase.add')
@freeze_time("2025-05-17 21:45:12")
def test_checkzonnesterkte_laat(mock_adddb, mock_leesdb, mock_schakeluit, mock_schakelaan, mock_haalzonnesterkte,
                                mock_haaluitdb):
  thuis.checkzonnesterkte()

  assert mock_haaluitdb.call_count == 1
  assert mock_haalzonnesterkte.call_count == 1
  assert mock_schakelaan.call_count == 0
  assert mock_schakeluit.call_count == 0
  assert mock_leesdb.call_count == 4
  assert mock_adddb.call_count == 1


@patch('thuis.haalzonnesterkteuitdb', return_value=600)
@patch('thuis.haalzonnesterkte', return_value=400)
@patch('thuis.schakellampenaan')
@patch('thuis.schakellampenuit')
@patch('pysondb.db.JsonDatabase.getByQuery',
       side_effect=[[{'env': 'zonsterktelampen', 'value': 400, 'id': 9712382}],
                    [{'env': 'starttijd', 'value': 9, 'id': 13287633}],
                    [],
                    [],
                    ])
@patch('pysondb.db.JsonDatabase.add')
@freeze_time("2025-05-17 23:45:12")
def test_checkzonnesterkte_laat_default(mock_adddb, mock_leesdb, mock_schakeluit, mock_schakelaan,
                                        mock_haalzonnesterkte, mock_haaluitdb):
  thuis.checkzonnesterkte()

  assert mock_haaluitdb.call_count == 1
  assert mock_haalzonnesterkte.call_count == 1
  assert mock_schakelaan.call_count == 0
  assert mock_schakeluit.call_count == 0
  assert mock_leesdb.call_count == 4
  assert mock_adddb.call_count == 1


@patch('thuis.verstuurberichtmonitoring')
@patch('thuis.zetlampaan')
@patch('pysondb.db.JsonDatabase.getByQuery',
       side_effect=[
         [{'env': 'lampen', 'value': [{"id": "dummyid1", "naam": "Lampnaam1", "volgorde": 11, "automatisch": True},
                                      {"id": "dummyid2", "naam": "Lampnaam2", "volgorde": 22, "automatisch": False}],
           'id': 92734098234}],
       ])
def test_schakellampenaan(mock_db, mock_lampaan, mock_bericht):
  thuis.schakellampenaan(654, 321)

  assert mock_bericht.call_count == 1
  assert mock_lampaan.call_count == 1
  assert mock_db.call_count == 1


@patch('thuis.verstuurberichtmonitoring')
@patch('thuis.zetlampaan')
@patch('pysondb.db.JsonDatabase.getByQuery',
       side_effect=[
         [{'env': 'lampen', 'value': [{"id": "dummyid1", "naam": "Lampnaam1", "volgorde": 11, "automatisch": False},
                                      {"id": "dummyid2", "naam": "Lampnaam2", "volgorde": 22, "automatisch": False}],
           'id': 92734098234}],
       ])
def test_schakellampenaan_minder(mock_db, mock_lampaan, mock_bericht):
  thuis.schakellampenaan(654, 321)

  assert mock_bericht.call_count == 1
  assert mock_lampaan.call_count == 0
  assert mock_db.call_count == 1


@patch('thuis.verstuurberichtmonitoring')
@patch('thuis.zetlampuit')
@patch('pysondb.db.JsonDatabase.getByQuery',
       side_effect=[
         [{'env': 'lampen', 'value': [{"id": "dummyid1", "naam": "Lampnaam1", "volgorde": 11, "automatisch": True},
                                      {"id": "dummyid2", "naam": "Lampnaam2", "volgorde": 22, "automatisch": False}],
           'id': 92734098234}],
       ])
def test_schakellampenuit(mock_db, mock_lampuit, mock_bericht):
  thuis.schakellampenuit(123, 456)

  assert mock_bericht.call_count == 1
  assert mock_lampuit.call_count == 1
  assert mock_db.call_count == 1


@patch('thuis.verstuurberichtmonitoring')
@patch('thuis.zetlampuit')
@patch('pysondb.db.JsonDatabase.getByQuery',
       side_effect=[
         [{'env': 'lampen', 'value': [{"id": "dummyid1", "naam": "Lampnaam1", "volgorde": 11, "automatisch": True},
                                      {"id": "dummyid2", "naam": "Lampnaam2", "volgorde": 22, "automatisch": True}],
           'id': 92734098234}],
       ])
def test_schakellampenuit_meer(mock_db, mock_lampuit, mock_bericht):
  thuis.schakellampenuit(123, 456)

  assert mock_bericht.call_count == 1
  assert mock_lampuit.call_count == 2
  assert mock_db.call_count == 1
