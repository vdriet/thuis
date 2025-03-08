""" Besturing van apparatuur thuis """
import _thread
import json
import os
from datetime import datetime
from time import sleep
from urllib.parse import quote_plus

import requests
import schedule
import waitress
from cachetools import cached, TTLCache
from flask import Flask, render_template, request, redirect
from pysondb import db

app = Flask(__name__)
envdb = db.getDb('envdb.json')
BASEURL = 'ha101-1.overkiz.com'
weercache = TTLCache(maxsize=1, ttl=900)
monitoringcache = TTLCache(maxsize=1, ttl=86400)


def leesenv(env: str):
  """ Lees een gegeven uit de envdb """
  rows = envdb.getByQuery({'env': env})
  if len(rows) != 1:
    return None
  return rows[0].get('value')


def deleteenv(env: str):
  """ Verwijder een gegeven uit de envdb """
  rows = envdb.getByQuery({'env': env})
  for row in rows:
    envdb.deleteById(row.get('id'))


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
  pod = leesenv('pod')
  jsessionid = leesenv('jsessionid')
  url = f'https://{BASEURL}/enduser-mobile-web/enduserAPI/config/{pod}/local/tokens/generate'
  headers = {'Content-Type': 'application/json'
    , 'Cookie': f'JSESSIONID={jsessionid}'}
  with requests.get(url=url, headers=headers, timeout=10) as response:
    contentjson = response.json()
    rettoken = contentjson['token']
    deleteenv('token')
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
  pod = leesenv('pod')
  jsessionid = leesenv('jsessionid')
  url = f'https://{BASEURL}/enduser-mobile-web/enduserAPI/config/{pod}/local/tokens/{uuid}'
  headers = {'Content-Type': 'application/json'
    , 'Cookie': f'JSESSIONID={jsessionid}'}
  with requests.delete(url=url, headers=headers, timeout=10) as response:
    return response.status_code


def haaltokensentoon():
  """ Haal de tokens van de server en toon deze
      Wanneer er gegevens missen, redirect naar hoofdpagina
  """
  pod = leesenv('pod')
  jsessionid = leesenv('jsessionid')
  if not pod or not jsessionid:
    return redirect('/thuis')
  servertokens = getavailabletokens(jsessionid, pod)
  if isinstance(servertokens, dict) and not servertokens.get('error', None) is None:
    deleteenv('jsessionid')
    userid = leesenv('userid')
    password = leesenv('password')
    if not userid or not password:
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


def haalgegevensvansomfy(token, pod, path):
  """ Ophalen van gegevens van het somfy kastje """
  url = f'https://{pod}.local:8443/enduser-mobile-web/1/enduserAPI/{path}'
  headers = {'Content-type': 'application/json', 'Authorization': f'Bearer {token}'}
  with requests.get(url=url,
                    headers=headers,
                    timeout=5,
                    verify='./cert/overkiz-root-ca-2048.crt') as response:
    return response.json()


def stuurgegevensnaarsomfy(token, pod, path, data):
  """ Sturen van gegevens naar het somfy kastje """
  url = f'https://{pod}.local:8443/enduser-mobile-web/1/enduserAPI/{path}'
  headers = {'Content-type': 'application/json', 'Authorization': f'Bearer {token}'}
  with requests.post(url=url,
                     headers=headers,
                     timeout=5,
                     verify='./cert/overkiz-root-ca-2048.crt',
                     data=data) as response:
    return response.json()


def getschermen(pod, token):
  """ Ophalen van de schermen en in de db zetten """
  schermlijst = []
  path = f'setup/devices/controllables/{quote_plus("io:VerticalExteriorAwningIOComponent")}'
  schermurls = haalgegevensvansomfy(token, pod, path)
  if not (isinstance(schermurls, dict) and not schermurls.get('error', None) is None):
    for schermurl in schermurls:
      scherurlencoded = quote_plus(schermurl)
      device = haalgegevensvansomfy(token, pod, f'setup/devices/{scherurlencoded}')
      schermlijst.append({'label': device['label'], 'device': schermurl})
  envdb.add({'env': 'schermen', 'value': schermlijst})
  return schermlijst


def haalstatusentoon():
  """ Haal de status van de schermen toon deze
      Wanneer er gegevens missen, redirect naar hoofdpagina
  """
  pod = leesenv('pod')
  token = leesenv('token')
  if not pod or not token:
    return redirect('/thuis')
  envschermen = leesenv('schermen')
  if not envschermen:
    envschermen = getschermen(pod, token)
  schermen = []
  percopenstate = quote_plus("core:DeploymentState")
  for scherm in envschermen:
    schermurlencoded = quote_plus(scherm['device'])
    schermstate = haalgegevensvansomfy(token,
                                       pod,
                                       f'setup/devices/{schermurlencoded}/states/{percopenstate}')
    if isinstance(schermstate, dict) and not schermstate.get('error', None) is None:
      return redirect('/thuis')
    schermen.append({'label': scherm['label'],
                     'device': scherm['device'],
                     'percentage': schermstate['value']
                     })
  windbft = haalwindsnelheid()
  return render_template('status.html', schermen=schermen, windbft=windbft)


def verplaatsscherm(device, percentage):
  """ Verplaats een scherm """
  token = leesenv('token')
  pod = leesenv('pod')
  data = json.dumps({
    "label": "verplaats scherm",
    "actions": [
      {
        "commands": [
          {
            "name": "setClosure",
            "parameters": [percentage]
          }
        ],
        "deviceURL": device
      }
    ]
  })
  stuurgegevensnaarsomfy(token=token, pod=pod, path='exec/apply', data=data)


def verplaatsalleschermen(percentage):
  """ Verplaats alle schermen naar zelfde percentage """
  schermen = leesenv('schermen')
  for scherm in schermen:
    deviceid = scherm.get('device')
    verplaatsscherm(deviceid, percentage)


def sluitalles():
  """ Sluiten van alle schermen """
  verplaatsalleschermen(100)


def openalles():
  """ Openen van alle schermen """
  verplaatsalleschermen(0)


def verversschermen():
  """ Verplaats alle schermen """
  deleteenv('schermen')


@cached(cache=weercache)
def haalwindsnelheid():  # pragma: no cover
  """ Haal de informatie van het weer van Hattem op """
  weerapikey = os.environ['WEER_API_KEY']
  url = f'https://weerlive.nl/api/weerlive_api_v2.php?key={weerapikey}&locatie=Hattem'
  with requests.get(url=url,
                    timeout=5) as response:
    weerinfo = response.json()
  if weerinfo is None or \
      weerinfo.get('liveweer', None) is None or \
      weerinfo.get('liveweer')[0].get('fout', None) is not None:
    return 0
  return int(weerinfo['liveweer'][0]['windbft'])


@cached(cache=monitoringcache)
def verstuurberichtmonitoring(bericht):
  """
    Verstuur bericht naar de monitoring,
    maar niet vaker dan eenmaal per dag
  """
  requests.post(url="https://ntfy.sh/vanderiethattemmonitoring",
                timeout=5,
                data=bericht)


def checkwindsnelheid():
  """ Check de windsnelheid """
  windbft = haalwindsnelheid()
  if windbft > 1:
    verstuurberichtmonitoring(f'Windsnelheid: {windbft}')


@app.route('/thuis', methods=['GET'])
def thuispagina():
  """ Toon de hoofdpagina """
  pod = leesenv('pod')
  jsessionid = leesenv('jsessionid')
  userid = leesenv('userid')
  password = leesenv('password')
  token = leesenv('token')
  return render_template('hoofdpagina.html',
                         pod=pod,
                         jsessionid=jsessionid,
                         userid=userid,
                         password=password,
                         token=token)


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


@app.route('/thuis/status', methods=['GET'])
def statuspagina():
  """ Toon de pagina met de status van de schermen """
  return haalstatusentoon()


@app.route('/thuis/status', methods=['POST'])
def statusactiepagina():
  """ Verwerk het verplaatsen van een of meer schermen """
  actie = request.form['actie']
  if actie == 'zetscherm':
    device = request.form['device']
    percentage = request.form['percentage']
    if percentage.isnumeric():
      verplaatsscherm(device, percentage)
  elif actie == 'sluitalles':
    sluitalles()
  elif actie == 'openalles':
    openalles()
  elif actie == 'ververs':
    verversschermen()
  return redirect('/thuis/status')


def startwebserver():
  """ Start webserver """
  waitress.serve(app, host="0.0.0.0", port=8088)


if __name__ == '__main__':
  # Start webserver
  _thread.start_new_thread(startwebserver, ())

  checkwindsnelheid()
  # Elke kwartier check windsnelheid
  schedule.every(15).minutes.do(checkwindsnelheid)
  while True:
    waittime = schedule.idle_seconds()
    print(f'wacht {waittime} seconden')
    sleep(waittime)
    schedule.run_pending()
