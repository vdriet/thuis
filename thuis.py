""" Besturing van apparatuur thuis """
import _thread
import colorsys
import json
import os
from datetime import datetime
from time import sleep
from urllib.parse import quote_plus

import requests
import schedule
import urllib3
import waitress
from cachetools import cached, TTLCache
from flask import Flask, render_template, request, redirect
from pysondb import db
from requests import ReadTimeout, JSONDecodeError

app = Flask(__name__,
            static_url_path='/static',
            template_folder='templates')
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


def haalinstellingenentoon():
  """ Haal de instellingen van de server en toon deze
      Wanneer er gegevens missen, redirect naar hoofdpagina
  """
  pod = leesenv('pod')
  jsessionid = leesenv('jsessionid')
  hueip = leesenv('hueip')
  hueuser = leesenv('hueuser')
  userid = leesenv('userid')
  password = leesenv('password')
  gridbreedte = leesenv('gridbreedte')
  gridhoogte = leesenv('gridhoogte')
  if not jsessionid and userid and password:
    jsessionid = somfylogin(userid, password)
    envdb.add({'env': 'jsessionid', 'value': jsessionid})
  tokens = []
  if pod and jsessionid:
    servertokens = getavailabletokens(jsessionid, pod)
    if isinstance(servertokens, dict) and not servertokens.get('error', None) is None:
      deleteenv('jsessionid')
      return redirect('/thuis/instellingen')
    for token in servertokens:
      aanmaaktijdstip = int(token['gatewayCreationTime'] / 1000)
      start = datetime.fromtimestamp(aanmaaktijdstip).strftime('%Y-%m-%d %H:%M:%S')
      tokens.append({'label': token['label'],
                     'pod': token['gatewayId'],
                     'start': start,
                     'uuid': token['uuid'],
                     })
  return render_template('instellingen.html',
                         tokens=tokens,
                         hueip=hueip,
                         hueuser=hueuser,
                         pod=pod,
                         userid=userid,
                         password=password,
                         gridbreedte=gridbreedte,
                         gridhoogte=gridhoogte, )


def haalgegevensvansomfy(token, pod, path):
  """ Ophalen van gegevens van het somfy kastje """
  url = f'https://{pod}.local:8443/enduser-mobile-web/1/enduserAPI/{path}'
  headers = {'Content-type': 'application/json', 'Authorization': f'Bearer {token}'}
  with requests.get(url=url,
                    headers=headers,
                    timeout=5,
                    verify='./cert/overkiz-root-ca-2048.crt') as response:
    return response.json()


def haalgegevensvanhue(hueip, hueuser, path):
  """ Ophalen van gegevens van de hue bridge """
  urllib3.disable_warnings()
  url = f'https://{hueip}/clip/v2/resource/{path}'
  headers = {'Content-type': 'application/json',
             'hue-application-key': hueuser}
  with requests.get(url=url,
                    headers=headers,
                    timeout=5,
                    verify=False) as response:
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


def stuurgegevensnaarhue(hueip, hueuser, path, data):
  """ Sturen van het hue kastje """
  urllib3.disable_warnings()
  url = f'https://{hueip}/clip/v2/resource/{path}'
  headers = {'Content-type': 'application/json',
             'hue-application-key': hueuser}
  with requests.put(url=url,
                    headers=headers,
                    timeout=5,
                    verify=False,
                    data=json.dumps(data)) as response:
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


def haalschermenentoon():
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
  return render_template('schermen.html', schermen=schermen, windbft=windbft)


def bepaalxyvanrgb(kleurwaarde):
  """ Bepaal de xy waarde vanuit rgb """
  rood = float(int(kleurwaarde[1:3], 16)) / 255.0
  groen = float(int(kleurwaarde[3:5], 16)) / 255.0
  blauw = float(int(kleurwaarde[5:7], 16)) / 255.0
  hwaarde, swaarde, vwaarde = colorsys.rgb_to_hsv(rood, groen, blauw)
  hwaarde = round(hwaarde, 2)
  swaarde = round(swaarde, 2)
  brightness = round(vwaarde * 100, 2)
  return hwaarde, swaarde, brightness


def bepaalhexrgbvanxy(xwaarde, ywaarde, dimwaarde):
  """ Bepaal de rgb waarde vanuit de x/y/dim """
  vwaarde = float(dimwaarde / 100)
  rood, groen, blauw = colorsys.hsv_to_rgb(xwaarde, ywaarde, vwaarde)
  rwaarde = int(rood * 255.0)
  gwaarde = int(groen * 255.0)
  bwaarde = int(blauw * 255.0)
  retvalue = f'#{rwaarde:02x}{gwaarde:02x}{bwaarde:02x}'
  return retvalue


def zetlampenindb(lampen):
  """ Plaats de lmapen in de envdb """
  dblampen = []
  gridbreedte = leesenv('gridbreedte')
  if gridbreedte is None:
    gridbreedte = 3
    envdb.add({'env': 'gridbreedte', 'value': gridbreedte})
  gridhoogte = leesenv('gridhoogte')
  if gridhoogte is None:
    gridhoogte = 4
    envdb.add({'env': 'gridhoogte', 'value': gridhoogte})
  volgordex = 1
  volgordey = 1
  for lamp in lampen:
    lampenv = {'id': lamp.get('id'),
               'naam': lamp.get('naam'),
               'volgorde': volgordey * 10 + volgordex}
    volgordex += 1
    if volgordex > gridbreedte:
      volgordex = 1
      volgordey += 1
    dblampen.append(lampenv)
  envdb.add({'env': 'lampen', 'value': dblampen})


def haallampenentoon():
  """ Haal de status van de lampen toon deze
      Wanneer er gegevens missen, redirect naar hoofdpagina
  """
  hueip = leesenv('hueip')
  hueuser = leesenv('hueuser')
  if not hueip or not hueuser:
    return redirect('/thuis')
  dblampen = leesenv('lampen')
  lampen = []
  lampdata = haalgegevensvanhue(hueip, hueuser, 'light')

  if len(lampdata.get('errors', [])) != 0:
    return redirect('/thuis')

  for lamp in lampdata.get('data', {}):
    lampmetadata = lamp.get('metadata')
    dimwaarde = 100
    if lamp.get('dimming', None) is not None:
      dimwaarde = lamp.get('dimming').get('brightness')
    color = lamp.get('color', None)
    rgbwaarde = '#000000'
    if color is not None:
      xywaarde = color.get('xy')
      xwaarde = xywaarde.get('x')
      ywaarde = xywaarde.get('y')
      rgbwaarde = bepaalhexrgbvanxy(xwaarde, ywaarde, dimwaarde)
    if lamp.get('on').get('on'):
      status = 'Aan'
    else:
      status = 'Uit'
    lampen.append({'id': lamp.get('id'),
                   'naam': lampmetadata.get('name'),
                   'archetype': lampmetadata.get('archetype'),
                   'dimable': lamp.get('dimming', None) is not None,
                   'dimwaarde': dimwaarde,
                   'color': color,
                   'rgbwaarde': rgbwaarde,
                   'status': status})
  if not dblampen:
    zetlampenindb(sorted(lampen, key=lambda x: x['naam']))
  return render_template('lampen.html',
                         lampen=sorted(lampen, key=lambda x: x['naam']),
                         gridbreedte=leesenv('gridbreedte'),
                         gridhoogte=leesenv('gridhoogte'),
                         )


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
  """ Ververs de opgeslagen schermen """
  deleteenv('schermen')


def doeactieoplamp(lampid, actie):
  """ voer een actie uit op een lamp """
  hueip = leesenv('hueip')
  hueuser = leesenv('hueuser')
  path = f'light/{lampid}'
  stuurgegevensnaarhue(hueip, hueuser, path, actie)


def zetlampaanuit(lampid, status):
  """ zet een lamp aan of uit """
  actie = {'on': {'on': status}}
  doeactieoplamp(lampid, actie)


def zetlampaan(lampid):
  """ zet een lamp aan """
  zetlampaanuit(lampid, True)


def zetlampuit(lampid):
  """ zet een lamp uit """
  zetlampaanuit(lampid, False)


def dimlamp(lampid, dimwaarde):
  """ dim een lamp """
  zetlampaan(lampid)
  actie = {'dimming': {'brightness': dimwaarde}}
  doeactieoplamp(lampid, actie)


def kleurlamp(lampid, kleurwaarde):
  """ verander de kleur van een lamp """
  xwaarde, ywaarde, brightness = bepaalxyvanrgb(kleurwaarde)
  dimlamp(lampid, brightness)
  actie = {'color': {'xy': {'x': xwaarde, 'y': ywaarde}}}
  doeactieoplamp(lampid, actie)


def allelampenuit():
  """ Alle lampen uit """
  lampen = leesenv('lampen')
  for lamp in lampen:
    lampid = lamp.get('id')
    zetlampuit(lampid)


def ververslampen():
  """ Ververs de opgeslagen lampen """
  deleteenv('lampen')


@cached(cache=weercache)
def haalwindsnelheid():  # pragma: no cover
  """ Haal de informatie van het weer van Hattem op """
  weerapikey = os.environ['WEER_API_KEY']
  url = f'https://weerlive.nl/api/weerlive_api_v2.php?key={weerapikey}&locatie=Hattem'
  try:
    with requests.get(url=url,
                      timeout=5) as response:
      weerinfo = response.json()
  except ReadTimeout as e:
    print(f'Timeout while getting weerinfo: {e}, return 0')
    return 0
  except JSONDecodeError as e:
    print(f'Result from weerlive.nl is not json: {e}, return 0')
    return 0
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
  if windbft > 5:
    verstuurberichtmonitoring(f'Windsnelheid: {windbft}, schermen openen!')
    openalles()


@app.route('/thuis', methods=['GET'])
def thuispagina():
  """ Toon de hoofdpagina """
  pod = leesenv('pod')
  jsessionid = leesenv('jsessionid')
  userid = leesenv('userid')
  password = leesenv('password')
  token = leesenv('token')
  hueip = leesenv('hueip')
  hueuser = leesenv('hueuser')
  return render_template('hoofdpagina.html',
                         pod=pod,
                         jsessionid=jsessionid,
                         userid=userid,
                         password=password,
                         token=token,
                         hueip=hueip,
                         hueuser=hueuser)


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


@app.route('/thuis/hueip', methods=['POST'])
def hueippagina():
  """ Verwerk het opvoeren van het ip van de hue """
  hueip = request.form['hueip']
  deleteenv('hueip')
  envdb.add({'env': 'hueip', 'value': hueip})
  return redirect('/thuis')


@app.route('/thuis/hueuser', methods=['POST'])
def hueuserpagina():
  """ Verwerk het opvoeren van de hueuser """
  hueuser = request.form['hueuser']
  deleteenv('hueuser')
  envdb.add({'env': 'hueuser', 'value': hueuser})
  return redirect('/thuis/instellingen')


@app.route('/thuis/grid', methods=['POST'])
def gridpagina():
  """ Verwerk het aanpassen van de gridlayout """
  deleteenv('gridbreedte')
  envdb.add({'env': 'gridbreedte', 'value': int(request.form['gridbreedte'])})
  deleteenv('gridhoogte')
  envdb.add({'env': 'gridhoogte', 'value': int(request.form['gridhoogte'])})
  return redirect('/thuis/instellingen')


@app.route('/thuis/instellingen', methods=['GET'])
def instellingenpagina():
  """ Toon de pagina met alle instellingen """
  return haalinstellingenentoon()


@app.route('/thuis/instellingen', methods=['POST'])
def instellingenactiepagina():
  """ Verwerk een actie voor een token """
  actie = request.form.get('actie', '')
  if actie == 'delete':
    uuid = request.form['uuid']
    responsecode = deletetoken(uuid)
    sleep(1)
    if responsecode == 200:
      return haalinstellingenentoon()
  elif actie == 'create':
    label = request.form['label']
    createtoken(label)
    sleep(1)
    return haalinstellingenentoon()
  return redirect('/thuis/instellingen')


@app.route('/thuis/schermen', methods=['GET'])
def schermenpagina():
  """ Toon de pagina met de status van de schermen """
  return haalschermenentoon()


@app.route('/thuis/lampen', methods=['GET'])
def lampenpagina():
  """ Toon de pagina met de lampen """
  return haallampenentoon()


@app.route('/thuis/schermen', methods=['POST'])
def schermenactiepagina():
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
  return redirect('/thuis/schermen')


@app.route('/thuis/lampen', methods=['POST'])
def lampenenactiepagina():
  """ Verwerk het verplaatsen van een of meer schermen """
  actie = request.form['actie']
  if actie == 'lampaan':
    lampid = request.form['lampid']
    zetlampaan(lampid)
  elif actie == 'lampuit':
    lampid = request.form['lampid']
    zetlampuit(lampid)
  elif actie == 'lampdim':
    lampid = request.form['lampid']
    dimwaarde = request.form['dimwaarde']
    dimlamp(lampid, float(dimwaarde))
  elif actie == 'lampkleur':
    lampid = request.form['lampid']
    kleurwaarde = request.form['kleurwaarde']
    kleurlamp(lampid, kleurwaarde)
  elif actie == 'allesuit':
    allelampenuit()
  elif actie == 'ververs':
    ververslampen()
  return redirect('/thuis/lampen')


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
