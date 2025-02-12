""" Besturing van appartuur thuis """
from datetime import datetime
from time import sleep
from urllib.parse import quote_plus

import requests
import waitress
from flask import Flask, render_template, request, redirect
from pysondb import db

app = Flask(__name__)
envdb = db.getDb('envdb.json')
BASEURL = 'ha101-1.overkiz.com'


def leesenv():
  """ Lees de gegevens uit de envdb """
  pod, jsessionid, token, userid, password = None, None, None, None, None
  rows = envdb.getAll()
  for row in rows:
    env = row.get('env', '')
    if env == 'pod':
      pod = row['value']
    if env == 'jsessionid':
      jsessionid = row['value']
    if env == 'token':
      token = row['value']
    if env == 'userid':
      userid = row['value']
    if env == 'password':
      password = row['value']
  return pod, jsessionid, token, userid, password


def somfylogin(userid, password):
  """ Inloggen bij somfy voor ophalen key """
  url = f'https://{BASEURL}/enduser-mobile-web/enduserAPI/login'

  data = f'userId={quote_plus(userid)}&userPassword={quote_plus(password)}'
  headers = {'Content-Type': 'application/x-www-form-urlencoded'}
  with requests.post(url=url, timeout=10, headers=headers, data=data) as response:
    jsessionid = response.cookies.get('JSESSIONID')
  return jsessionid


def getavailabletokens(jsessionid, pod):
  """ Haal beschikbare tokens van de server """
  url = f'https://{BASEURL}/enduser-mobile-web/enduserAPI/config/{pod}/local/tokens/devmode'
  headers = {'Accept': 'application/json',
             'Cookie': f'JSESSIONID={jsessionid}'}
  with requests.get(url=url, headers=headers, timeout=10) as response:
    contentjson = response.json()
  return contentjson


def createtoken(label):
  """ Voeg een token toe op de server """
  pod, jsessionid, _, _, _ = leesenv()
  url = f'https://{BASEURL}/enduser-mobile-web/enduserAPI/config/{pod}/local/tokens/generate'
  headers = {'Content-Type': 'application/json'
    , 'Cookie': f'JSESSIONID={jsessionid}'}
  with requests.get(url=url, headers=headers, timeout=10) as response:
    contentjson = response.json()
    rettoken = contentjson['token']
    row = envdb.getByQuery({'env': 'token'})
    envdb.deleteById(row[0].get('id'))
    envdb.add({'env': 'token', 'value': rettoken})
    activatetoken(jsessionid, pod, label, rettoken)
    return 200


def activatetoken(jsessionid, pod, label, token):
  """ Activeer een token """
  url = f'https://{BASEURL}/enduser-mobile-web/enduserAPI/config/{pod}/local/tokens'
  headers = {'Content-Type': 'application/json',
             'Cookie': f'JSESSIONID={jsessionid}'}
  data = f'{{"label": "{label}", "token": "{token}", "scope": "devmode"}}'.encode('utf-8')
  with requests.post(url=url, headers=headers, data=data, timeout=10):
    pass


def deletetoken(uuid):
  """ Verwijder een token van de server """
  pod, jsessionid, _, _, _ = leesenv()
  url = f'https://{BASEURL}/enduser-mobile-web/enduserAPI/config/{pod}/local/tokens/{uuid}'
  headers = {'Content-Type': 'application/json'
    , 'Cookie': f'JSESSIONID={jsessionid}'}
  with requests.delete(url=url, headers=headers, timeout=10) as response:
    return response.status_code


def haaltokensentoon():
  """ Haal de tokens van de server en toon deze
      Wanneer er gegevens missen, redirect naar hoofdpagina
  """
  pod, jsessionid, _, userid, password = leesenv()
  if not pod or not jsessionid:
    return redirect('/thuis')
  servertokens = getavailabletokens(jsessionid, pod)
  if isinstance(servertokens, dict) and not servertokens.get('error', None) is None:
    row = envdb.getByQuery({'env': 'jsessionid'})
    envdb.deleteById(row[0].get('id'))
    if userid is None or password is None:
      return redirect('/thuis')
    jsessionid = somfylogin(userid, password)
    envdb.add({'env': 'jsessionid', 'value': jsessionid})
    servertokens = getavailabletokens(jsessionid, pod)
  tokens = []
  for token in servertokens:
    aanmaaktijdstip = int(token['gatewayCreationTime'] / 1000)
    start = datetime.fromtimestamp(aanmaaktijdstip).strftime('%Y-%m-%d %H:%M:%S')
    tokens.append({'label': token['label'],
                   'pod': token['gatewayId'],
                   'start': start,
                   'uuid': token['uuid'],
                   })
  return render_template('tokens.html', tokens=tokens)


@app.route('/thuis', methods=['GET'])
def thuispagina():
  """ Toon de hoofdpagina """
  pod, jsessionid, _, _, _ = leesenv()
  return render_template('hoofdpagina.html',
                         pod=pod, jsessionid=jsessionid)


@app.route('/thuis/login', methods=['POST'])
def loginpagina():
  """ Verwerk de login """
  userid = request.form['userid']
  password = request.form['password']
  bewaargegevens = request.form['savelogin']
  if bewaargegevens == 'on':
    envdb.add({'env': 'userid', 'value': userid})
    envdb.add({'env': 'password', 'value': password})
  jsessionid = somfylogin(userid, password)
  envdb.add({'env': 'jsessionid', 'value': jsessionid})
  return redirect('/thuis')


@app.route('/thuis/pod', methods=['POST'])
def podpagina():
  """ Verwerk het opvoeren van de pod """
  pod = request.form['pod']
  envdb.add({'env': 'pod', 'value': pod})
  return redirect('/thuis')


@app.route('/thuis/tokens', methods=['GET'])
def tokenspagina():
  """ Toon de pagina met alle tokens """
  return haaltokensentoon()


@app.route('/thuis/tokens', methods=['POST'])
def tokensactiepagina():
  """ Verwerk een actie voor een token """
  actie = request.form.get('actie', '')
  if actie == 'delete':
    uuid = request.form['uuid']
    responsecode = deletetoken(uuid)
    sleep(1)
    if responsecode == 200:
      return haaltokensentoon()
  elif actie == 'create':
    label = request.form['label']
    createtoken(label)
    sleep(1)
    return haaltokensentoon()
  return redirect('/thuis/tokens')


if __name__ == '__main__':
  waitress.serve(app, host="0.0.0.0", port=8088)
