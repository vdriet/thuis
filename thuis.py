""" Besturing van appartuur thuis """
import os
from urllib.parse import quote_plus

import requests
import waitress
from flask import Flask, render_template, request, redirect
from pysondb import db

app = Flask(__name__)
envdb = db.getDb('envdb.json')
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


def activatetoken(localjsessionid, localtoken):
  """ Activeer een token """
  pod = os.environ['pod']
  url = f'https://{BASEURL}/enduser-mobile-web/enduserAPI/config/{pod}/local/tokens'
  headers = {'Content-Type': 'application/json'
    , 'Cookie': f'JSESSIONID={localjsessionid}'}
  data = f'{{"label": "Python token", "token": "{localtoken}", "scope": "devmode"}}'.encode('utf-8')
  with requests.post(url=url, headers=headers, data=data, timeout=10) as response:
    response.json()


@app.route('/thuis', methods=['GET'])
def thuispagina():
  """ Toon de hoofdpagina """
  pod, jsessionid = None, None
  rows = envdb.getAll()
  for row in rows:
    if row['env'] == 'pod':
      pod = row['value']
    if row['env'] == 'jsessionid':
      jsessionid = row['value']
  return render_template('hoofdpagina.html',
                         pod=pod, jsessionid=jsessionid)


@app.route('/thuis/login', methods=['POST'])
def loginpagina():
  """ Verwerk de login """
  userid = request.form['userid']
  password = request.form['password']
  jsessionid = somfylogin(userid, password)
  envdb.add({'env': 'jsessionid', 'value': jsessionid})
  return redirect('/thuis')


@app.route('/thuis/pod', methods=['POST'])
def podpagina():
  """ Verwerk het opvoeren van de pod """
  pod = request.form['pod']
  envdb.add({'env': 'pod', 'value': pod})
  return redirect('/thuis')


if __name__ == '__main__':
  waitress.serve(app, host="0.0.0.0", port=8088)
