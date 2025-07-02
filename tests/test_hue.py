import unittest
from unittest import mock
from unittest.mock import ANY


class MyTestCaseHue(unittest.TestCase):
  @staticmethod
  def _mock_response(status=200,
                     content="CONTENT",
                     json_data=None,
                     cookies=None,
                     raise_for_status=None):
    mock_resp = mock.Mock()
    mock_resp.raise_for_status = mock.Mock()
    if raise_for_status:
      mock_resp.raise_for_status.side_effect = raise_for_status
    mock_resp.status_code = status
    mock_resp.content = content
    if cookies:
      mock_resp.cookies = cookies
    else:
      mock_resp.cookies = {}
    if json_data:
      mock_resp.json = mock.Mock(
        return_value=json_data
      )
    return mock_resp

  @mock.patch('pysondb.db.JsonDatabase.getByQuery',
              side_effect=[[{'env': 'hueip', 'value': '4.3.2.1', 'id': 82265347}],
                           [{'env': 'hueuser', 'value': 'abcd1234qwer8765', 'id': 918273548237}]
                           ])
  @mock.patch('requests.get')
  def test_huegetdata(self, mock_get, mock_envdb):
    import thuis
    mock_resp = self._mock_response(status=200,
                                    content="""{'json': 'data'}""")
    mock_get.return_value.__enter__.return_value = mock_resp

    bridge = thuis.gethue()
    response = bridge.haalgegevens('path')
    self.assertEqual(response, ANY)
    mock_get.assert_called_once()
    self.assertEqual(mock_envdb.call_count, 2)


  @mock.patch('pysondb.db.JsonDatabase.getByQuery',
              side_effect=[[{'env': 'hueip', 'value': '4.3.2.1', 'id': 82265347}],
                           [{'env': 'hueuser', 'value': 'abcd1234qwer8765', 'id': 918273548237}]
                           ])
  @mock.patch('requests.put')
  def test_zetlampaan(self, mock_requestput, mock_envdb):
    import thuis
    thuis.zetlampaan('lampid')
    self.assertEqual(mock_envdb.call_count, 2)
    self.assertEqual(mock_requestput.call_count, 1)

  @mock.patch('pysondb.db.JsonDatabase.getByQuery',
              side_effect=[[{'env': 'hueip', 'value': '4.3.2.1', 'id': 82265347}],
                           [{'env': 'hueuser', 'value': 'abcd1234qwer8765', 'id': 918273548237}]
                           ])
  @mock.patch('requests.put')
  def test_zetlampuit(self, mock_requestput, mock_envdb):
    import thuis
    thuis.zetlampaan('lampid')
    self.assertEqual(mock_envdb.call_count, 2)
    self.assertEqual(mock_requestput.call_count, 1)

  @mock.patch('pysondb.db.JsonDatabase.getByQuery',
              side_effect=[[{'env': 'lampen', 'value': [{"id": "guid-1-2-3", "naam": "Test Lamp"},
                                                        {"id": "guid-4-5-6", "naam": "Lamp 2"}], 'id': 192378239}],
                           [{'env': 'hueip', 'value': '4.3.2.1', 'id': 82265347}],
                           [{'env': 'hueuser', 'value': 'abcd1234qwer8765', 'id': 918273548237}],
                           [{'env': 'hueip', 'value': '4.3.2.1', 'id': 82265347}],
                           [{'env': 'hueuser', 'value': 'abcd1234qwer8765', 'id': 918273548237}],
                           ])
  @mock.patch('requests.put')
  def test_zetallelampenuit(self, mock_requestput, mock_envdb):
    import thuis
    thuis.allelampenuit()
    self.assertEqual(mock_envdb.call_count, 5)
    self.assertEqual(mock_requestput.call_count, 2)

  @mock.patch('pysondb.db.JsonDatabase.getByQuery',
              return_value=[{'env': 'lampen', 'value': [], 'id': 29346298364}])
  @mock.patch('pysondb.db.JsonDatabase.deleteById')
  def test_ververslampen(self, mock_delete, mock_query):
    import thuis
    thuis.ververslampen()

    self.assertEqual(mock_delete.call_count, 1)
    self.assertEqual(mock_query.call_count, 1)

  def test_kleurberekenen_04_04_40(self):
    import thuis
    kleurwaarde = thuis.bepaalhexrgbvanxy(0.4, 0.4, 40)
    self.assertEqual(kleurwaarde, '#3d664d')
    xwaarde, ywaarde, brightness = thuis.bepaalxyvanrgb(kleurwaarde)
    self.assertEqual(xwaarde, 0.4)
    self.assertEqual(ywaarde, 0.4)
    self.assertEqual(brightness, 40)

  def test_kleurberekenen_wit(self):
    import thuis
    kleurwaarde = thuis.bepaalhexrgbvanxy(0, 0, 100)
    self.assertEqual(kleurwaarde, '#ffffff')
    xwaarde, ywaarde, brightness = thuis.bepaalxyvanrgb(kleurwaarde)
    self.assertEqual(xwaarde, 0)
    self.assertEqual(ywaarde, 0)
    self.assertEqual(brightness, 100)
