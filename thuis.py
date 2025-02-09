""" Besturing van appartuur thuis """
import os
from urllib.parse import quote_plus

import requests
import waitress
from flask import Flask, render_template

app = Flask(__name__)

BASEURL = 'ha101-1.overkiz.com'


def somfylogin(userid, password):
  """ Inloggen bij somfy voor ophalen key """
  url = f'https://{BASEURL}/enduser-mobile-web/enduserAPI/login'

  data = f'userId={quote_plus(userid)}&userPassword={quote_plus(password)}'
  headers = {'Content-Type': 'application/x-www-form-urlencoded'}
  with requests.post(url=url, timeout=10, headers=headers, data=data) as response:
    jsessionid = response.cookies.get('JSESSIONID')
  return jsessionid


def getapitoken(userjsessionid):
  """ Ophalen van een nieuw token """
  pod = os.environ['pod']
  url = f'https://{BASEURL}/enduser-mobile-web/enduserAPI/config/{pod}/local/tokens/generate'
  headers = {'Content-Type': 'application/json'
    , 'Cookie': f'JSESSIONID={userjsessionid}'}
  with requests.get(url=url, headers=headers, timeout=10) as response:
    contentjson = response.json()
    rettoken = contentjson['token']
  return rettoken


@app.route('/thuis', methods=['GET'])
def thuispagina():
  """ toon de hoofdpagina """
  return render_template('hoofdpagina.html')


if __name__ == '__main__':
  # userid = os.environ.get('userid')
  # password = os.environ.get('password')
  # jsessionid = somfylogin(userid, password)
  # token = getapitoken(jsessionid)
  waitress.serve(app, host="0.0.0.0", port=8088)
