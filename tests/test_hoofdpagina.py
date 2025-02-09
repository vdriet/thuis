import pytest
from flask import Flask

import thuis


@pytest.fixture()
def app():
  app = Flask(__name__, template_folder='../templates')
  app.config.update({
    "TESTING": True,
  })

  @app.route('/thuis', methods=['GET'])
  def thuishoofdpagina():
    return thuis.thuispagina()

  yield app


@pytest.fixture()
def client(app):
  return app.test_client()


def test_404(client):
  response = client.get('/home')
  assert b"404 Not Found" in response.data


def test_hoofdpaginaget(client):
  response = client.get('/thuis')
  assert b"<h1>Thuis</h1>" in response.data
