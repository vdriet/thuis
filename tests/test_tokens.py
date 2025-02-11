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
  def test_somfylogin(self, mock_post):
    import thuis
    mock_resp = self._mock_response(status=200,
                                    content="""[{'label': 'token 1', 'gatewayId': '1234-8765-1234',
                                              'gatewayCreationTime': 1738422650000,
                                              'uuid': '20547c11-73ce-475b-88be-9f8a8f345328', 'scope': 'devmode'},
                                             {'label': 'token2', 'gatewayId': '1234-8765-1234',
                                              'gatewayCreationTime': 1739117276000,
                                              'uuid': 'b3d4be51-1c5f-4f3c-acce-6e30824b2b54', 'scope': 'devmode'}]""")
    mock_post.return_value.__enter__.return_value = mock_resp

    response = thuis.getavailabletokens("jsessionid", "pod")
    self.assertEqual(response, ANY)
    mock_post.assert_called_once()


if __name__ == '__main__':
  unittest.main()
