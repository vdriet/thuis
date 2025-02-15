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
                           {'label': 'label 1'},
                           {'label': 'label 2'}
                           ]
              )
  def test_getschermen(self, mock_somfy):
    import thuis
    reponse = thuis.getschermen('pod', 'token')
    expected = [{'label': 'label 1', 'device': 'io://1234-4321-5678/13579'},
                {'label': 'label 2', 'device': 'io://1234-4321-5678/24680'}]
    self.assertEqual(reponse, expected)
    self.assertEqual(mock_somfy.call_count, 3)


if __name__ == '__main__':
  unittest.main()
