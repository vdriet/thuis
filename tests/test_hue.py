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

  @mock.patch('requests.get')
  def test_huegetdata(self, mock_get):
    import thuis
    mock_resp = self._mock_response(status=200,
                                    content="""{'json': 'data'}""")
    mock_get.return_value.__enter__.return_value = mock_resp

    response = thuis.haalgegevensvanhue('hueip', 'hueuser', 'path')
    self.assertEqual(response, ANY)
    mock_get.assert_called_once()

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
