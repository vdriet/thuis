from unittest.mock import patch, MagicMock

import pytest
from requests import ReadTimeout

import thuis


@pytest.fixture(autouse=True)
def mock_env_weerapikey(monkeypatch):
  monkeypatch.setenv("WEER_API_KEY", "dummykey")


def maakmockresponse(jsondata):
  mock_response = MagicMock()
  mock_response.getcode.return_value = 200
  mock_response.json.return_value = jsondata
  mock_response.__enter__.return_value = mock_response
  return mock_response


@patch('requests.get')
def test_haalwindsnelheid(mock_requestsget):
  mock_requestsget.return_value = maakmockresponse({'liveweer': [{'windbft': '3'}]})

  resultaat = thuis.haalwindsnelheid()
  assert resultaat == 3
  assert mock_requestsget.call_count == 1


@patch('requests.get')
def test_haalwindsnelheid_uitcache(mock_requestsget):
  mock_requestsget.return_value = maakmockresponse({'liveweer': [{'windbft': '4'}]})

  resultaat = thuis.haalwindsnelheid()
  assert resultaat == 3
  assert mock_requestsget.call_count == 0


@patch('requests.get')
def test_haalwindsnelheid_geenweer(mock_requestsget):
  mock_requestsget.return_value = maakmockresponse({'geenweer': [{'windbft': '4'}]})
  thuis.haalwindsnelheid.cache_clear()

  resultaat = thuis.haalwindsnelheid()
  assert resultaat == 0
  assert mock_requestsget.call_count == 1


@patch('requests.get', side_effect=ReadTimeout)
def test_haalwindsnelheid_timeout(mock_requestsget):
  thuis.haalwindsnelheid.cache_clear()

  resultaat = thuis.haalwindsnelheid()
  assert resultaat == 0
  assert mock_requestsget.call_count == 1


@patch("thuis.haalwindsnelheid", return_value=3)
@patch("requests.post")
@patch("thuis.sluitalles")
def test_checkwindsnelheid_geenbericht(mock_sluiten, mock_post, mock_wind):
  thuis.checkwindsnelheid()

  assert mock_wind.call_count == 1
  assert mock_post.call_count == 0
  assert mock_sluiten.call_count == 0


@patch("thuis.haalwindsnelheid", return_value=5)
@patch("requests.post")
@patch("thuis.sluitalles")
def test_checkwindsnelheid_geenbericht_rand(mock_sluiten, mock_post, mock_wind):
  thuis.checkwindsnelheid()

  assert mock_wind.call_count == 1
  assert mock_post.call_count == 0
  assert mock_sluiten.call_count == 0


@patch("thuis.haalwindsnelheid", return_value=6)
@patch("requests.post")
@patch("thuis.openalles")
def test_checkwindsnelheid_welbericht(mock_openen, mock_post, mock_wind):
  thuis.checkwindsnelheid()

  assert mock_wind.call_count == 1
  assert mock_post.call_count == 1
  assert mock_openen.call_count == 1
