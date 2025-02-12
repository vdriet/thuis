import unittest
from unittest.mock import ANY

import mock


class MyTestCaseTokens(unittest.TestCase):
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
                                    content="""[{'label': 'token 1', 'gatewayId': '1234-8765-1234',
                                              'gatewayCreationTime': 1738422650000,
                                              'uuid': '20547c11-73ce-475b-88be-9f8a8f345328', 'scope': 'devmode'},
                                             {'label': 'token2', 'gatewayId': '1234-8765-1234',
                                              'gatewayCreationTime': 1739117276000,
                                              'uuid': 'b3d4be51-1c5f-4f3c-acce-6e30824b2b54', 'scope': 'devmode'}]""")
    mock_get.return_value.__enter__.return_value = mock_resp

    response = thuis.getavailabletokens("jsessionid", "pod")
    self.assertEqual(response, ANY)
    mock_get.assert_called_once()

  @mock.patch('requests.delete')
  @mock.patch('pysondb.db.JsonDatabase.getAll',
              return_value=[{'env': 'pod', 'value': '1234-4321-5678', 'id': 28234834},
                            {'env': 'jsessionid', 'value': 'E3~1234CAFE5678DECA', 'id': 286349129001},
                            {'env': 'token', 'value': '4321c0de', 'id': 236910029}]
              )
  def test_deletetoken(self, mock_envdb, mock_delete):
    import thuis
    mock_resp = self._mock_response(status=200)
    mock_delete.return_value.__enter__.return_value = mock_resp
    returncode = thuis.deletetoken('b3d4be51-1c5f-4f3c-acce-6e30824b2b54')
    self.assertEqual(returncode, 200)
    mock_envdb.assert_called_once()
    mock_delete.assert_called_once()

  @mock.patch('requests.get')
  @mock.patch('pysondb.db.JsonDatabase.getAll',
              return_value=[{'env': 'pod', 'value': '1234-4321-5678', 'id': 28234834},
                            {'env': 'jsessionid', 'value': 'E3~1234CAFE5678DECA', 'id': 286349129001},
                            {'env': 'token', 'value': '4321c0de', 'id': 236910029}]
              )
  @mock.patch('pysondb.db.JsonDatabase.add')
  @mock.patch('pysondb.db.JsonDatabase.getByQuery')
  @mock.patch('pysondb.db.JsonDatabase.deleteById')
  def test_createtoken(self, mock_envdbdelete, mock_envdbget, mock_envdbadd, mock_envdball, mock_get):
    import thuis
    mock_resp = self._mock_response(status=200, json_data={'token': 'dummy'})
    mock_get.return_value.__enter__.return_value = mock_resp
    thuis.createtoken('label')

    mock_envdball.assert_called_once()
    mock_envdbadd.assert_called_once()
    mock_envdbget.assert_called_once()
    mock_envdbdelete.assert_called_once()
    mock_get.assert_called_once()


if __name__ == '__main__':
  unittest.main()
