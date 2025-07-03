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
    from somfy import Somfy
    mock_resp = self._mock_response(status=204,
                                    cookies={'JSESSIONID': 'dummy'})
    mock_post.return_value.__enter__.return_value = mock_resp

    response = Somfy.login("user", "pass")
    self.assertEqual(response, 'dummy')
    mock_post.assert_called_once()

  @mock.patch('requests.post')
  def test_activeertoken(self, mock_post):
    from somfy import Somfy
    mock_resp = self._mock_response(status=200,
                                    cookies={'JSESSIONID': 'dummy'},
                                    json_data={'requestId': 'eb77acc1-0a19-0482-25aa-49b027f4797e'})
    mock_post.return_value.__enter__.return_value = mock_resp
    Somfy.activatetoken('jsessionid', 'pod', 'label', 'token')
    mock_post.assert_called_once()


if __name__ == '__main__':
  unittest.main()
