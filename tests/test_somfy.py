import unittest
from unittest.mock import ANY

import mock


class MyTestCaseSomfy(unittest.TestCase):
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
  def test_somfylogin(self, mock_get):
    import thuis
    mock_resp = self._mock_response(status=200,
                                    content="""{'json': 'data'}""")
    mock_get.return_value.__enter__.return_value = mock_resp

    response = thuis.haalgegevensvansomfy('token', 'pod', 'path')
    self.assertEqual(response, ANY)
    mock_get.assert_called_once()

  @mock.patch('thuis.haalgegevensvansomfy',
              side_effect=[['io://1234-4321-5678/13579', 'io://1234-4321-5678/24680'],
                           {'label': 'label 1.0'},
                           {'label': 'label 2.0'}
                           ]
              )
  @mock.patch('pysondb.db.JsonDatabase.add')
  def test_getschermen(self, mock_dbadd, mock_somfy):
    import thuis
    reponse = thuis.getschermen('pod', 'token')
    expected = [{'label': 'label 1.0', 'device': 'io://1234-4321-5678/13579'},
                {'label': 'label 2.0', 'device': 'io://1234-4321-5678/24680'}]
    self.assertEqual(reponse, expected)
    self.assertEqual(mock_somfy.call_count, 3)
    self.assertEqual(mock_dbadd.call_count, 1)

  @mock.patch('pysondb.db.JsonDatabase.getByQuery',
              side_effect=[[{'env': 'token', 'value': '4321c0de', 'id': 236910029}],
                           [{'env': 'pod', 'value': '1234-4321-5678', 'id': 28234834}]
                           ])
  @mock.patch('requests.post')
  def test_verplaatsscherm(self, mock_requestspost, mock_getenv):
    import thuis
    thuis.verplaatsscherm('device', '20')
    self.assertEqual(mock_getenv.call_count, 2)
    self.assertEqual(mock_requestspost.call_count, 1)

  @mock.patch('pysondb.db.JsonDatabase.getByQuery',
              side_effect=[[{'env': 'schermen', 'value': [{'label': 'label 1.1', 'device': 'io://1234-4321-5678/13579'},
                                                          {'label': 'label 2.2',
                                                           'device': 'io://1234-4321-5678/24680'}]}],
                           [{'env': 'token', 'value': 'token', 'id': 286349129001}],
                           [{'env': 'pod', 'value': '1234-4321-5678', 'id': 28234834}],
                           [{'env': 'token', 'value': 'token', 'id': 286349129001}],
                           [{'env': 'pod', 'value': '1234-4321-5678', 'id': 28234834}]
                           ]
              )
  @mock.patch('thuis.stuurgegevensnaarsomfy')
  def test_sluitalles(self, mock_somfy, mock_query):
    import thuis
    thuis.sluitalles()
    self.assertEqual(mock_somfy.call_count, 2)
    self.assertEqual(mock_query.call_count, 5)

  @mock.patch('pysondb.db.JsonDatabase.getByQuery',
              side_effect=[[{'env': 'schermen', 'value': [{'label': 'label 1.1', 'device': 'io://1234-4321-5678/13579'},
                                                          {'label': 'label 2.2',
                                                           'device': 'io://1234-4321-5678/24680'}]}],
                           [{'env': 'token', 'value': 'token', 'id': 286349129001}],
                           [{'env': 'pod', 'value': '1234-4321-5678', 'id': 28234834}],
                           [{'env': 'token', 'value': 'token', 'id': 286349129001}],
                           [{'env': 'pod', 'value': '1234-4321-5678', 'id': 28234834}]
                           ]
              )
  @mock.patch('thuis.stuurgegevensnaarsomfy')
  def test_openalles(self, mock_somfy, mock_query):
    import thuis
    thuis.openalles()
    self.assertEqual(mock_somfy.call_count, 2)
    self.assertEqual(mock_query.call_count, 5)


if __name__ == '__main__':
  unittest.main()
