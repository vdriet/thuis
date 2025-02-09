import os
import unittest

import mock


class MyTestCase(unittest.TestCase):
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

  @mock.patch('requests.post')
  def test_somfylogin(self, mock_post):
    import thuis
    mock_resp = self._mock_response(status=204, cookies={'JSESSIONID': 'dummy'})
    mock_post.return_value.__enter__.return_value = mock_resp

    response = thuis.somfylogin("user", "pass")
    self.assertEqual(response, 'dummy')
    mock_post.assert_called_once()

  @mock.patch('requests.get')
  def test_getapitoken(self, mock_get):
    import thuis
    os.environ['pod'] = '1234-5678-1234'
    mock_resp = self._mock_response(status=200, json_data={'token': 'abcd1234'})
    mock_get.return_value.__enter__.return_value = mock_resp
    response = thuis.getapitoken("jsessionid")
    self.assertEqual(response, 'abcd1234')
    mock_get.assert_called_once()


if __name__ == '__main__':
  unittest.main()
