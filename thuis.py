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
zondb = db.getDb('zonnesterkte.json')
BASEURL = 'ha101-1.overkiz.com'
weercache = TTLCache(maxsize=1, ttl=900)
zonnesterktecache = TTLCache(maxsize=1, ttl=60)
monitoringcache = TTLCache(maxsize=1, ttl=86400)


def leesenv(env: str):
  """ Lees een gegeven uit de envdb 

  Args: env (str): De naam van het op te halen gegeven

  Returns: De waarde van het gegeven of None als het niet bestaat
  """
  rows = envdb.getByQuery({'env': env})
  if len(rows) != 1:
    return None
  return rows[0].get('value')


def deleteenv(env: str) -> None:
  """ Verwijder een gegeven uit de envdb 

  Args: env (str): De naam van het te verwijderen gegeven
  """
  rows = envdb.getByQuery({'env': env})
  for row in rows:
    envdb.deleteById(row.get('id'))


def somfylogin(userid: str, password: str) -> str:
  """ Inloggen bij somfy voor ophalen key 

  Args: userid (str): De gebruikersnaam voor Somfy
        password (str): Het wachtwoord voor Somfy

  Returns: str: De verkregen sessie-ID
  """
  url = f'https://{BASEURL}/enduser-mobile-web/enduserAPI/login'

  data = f'userId={quote_plus(userid)}&userPassword={quote_plus(password)}'
  headers = {'Content-Type': 'application/x-www-form-urlencoded'}
  with requests.post(url=url, timeout=10, headers=headers, data=data) as response:
    jsessionid = response.cookies.get('JSESSIONID')
  return jsessionid


def getavailabletokens(jsessionid: str, pod: str) -> list:
  """ Haal beschikbare tokens van de server 

  Args: jsessionid (str): De geldige sessie-ID
        pod (str): De pod-identificatie

  Returns: list: Lijst met beschikbare tokens
  """
  url = f'https://{BASEURL}/enduser-mobile-web/enduserAPI/config/{pod}/local/tokens/devmode'
  headers = {'Accept': 'application/json',
             'Cookie': f'JSESSIONID={jsessionid}'}
  with requests.get(url=url, headers=headers, timeout=10) as response:
    contentjson = response.json()
  return contentjson


def createtoken(label: str) -> int:
  """ Voeg een token toe op de server 

  Args: label (str): Het label voor de nieuwe token

  Returns: int: HTTP-statuscode (200 bij succes)
  """
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


def activatetoken(jsessionid: str, pod: str, label: str, token: str) -> None:
  """ Activeer een token 

  Args: jsessionid (str): De geldige sessie-ID
        pod (str): De pod-identificatie
        label (str): Het label voor het token
        token (str): Het te activeren token
  """
  url = f'https://{BASEURL}/enduser-mobile-web/enduserAPI/config/{pod}/local/tokens'
  headers = {'Content-Type': 'application/json',
             'Cookie': f'JSESSIONID={jsessionid}'}
  data = f'{{"label": "{label}", "token": "{token}", "scope": "devmode"}}'.encode('utf-8')
  with requests.post(url=url, headers=headers, data=data, timeout=10):
    pass


def deletetoken(uuid: str) -> int:
  """ Verwijder een token van de server 

  Args: uuid (str): De unieke identificatie van de token

  Returns: int: HTTP-statuscode van de verwijder-actie
  """
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

  Returns: Template: De instellingen-pagina of een redirect
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


def haalgegevensvansomfy(token: str, pod: str, path: str) -> dict:
  """ Ophalen van gegevens van het somfy kastje 

  Args: token (str): De geldige token
        pod (str): De pod-identificatie
        path (str): Het pad naar de op te vragen gegevens

  Returns: dict: De opgehaalde gegevens in JSON-formaat
  """
  url = f'https://{pod}.local:8443/enduser-mobile-web/1/enduserAPI/{path}'
  headers = {'Content-type': 'application/json', 'Authorization': f'Bearer {token}'}
  with requests.get(url=url,
                    headers=headers,
                    timeout=5,
                    verify='./cert/overkiz-root-ca-2048.crt') as response:
    return response.json()


def haalgegevensvanhue(hueip: str, hueuser: str, path: str) -> dict:
  """ Ophalen van gegevens van de hue bridge 

  Args: hueip (str): Het IP-adres van de Hue bridge
        hueuser (str): De geautoriseerde gebruiker
        path (str): Het pad naar de op te vragen gegevens

  Returns: dict: De opgehaalde gegevens in JSON -formaat
  """
  urllib3.disable_warnings()
  url = f'https://{hueip}/clip/v2/resource/{path}'
  headers = {'Content-type': 'application/json',
             'hue-application-key': hueuser}
  with requests.get(url=url,
                    headers=headers,
                    timeout=5,
                    verify=False) as response:
    return response.json()


def stuurgegevensnaarsomfy(token: str, pod: str, path: str, data: str) -> dict:
  """ Sturen van gegevens naar het somfy kastje 

  Args: token (str): De geldige token
        pod (str): De pod-identificatie
        path (str): Het pad voor de te versturen gegevens
        data (str): De te versturen gegevens

  Returns: dict: Het antwoord van de server in JSON-formaat
  """
  url = f'https://{pod}.local:8443/enduser-mobile-web/1/enduserAPI/{path}'
  headers = {'Content-type': 'application/json', 'Authorization': f'Bearer {token}'}
  with requests.post(url=url,
                     headers=headers,
                     timeout=5,
                     verify='./cert/overkiz-root-ca-2048.crt',
                     data=data) as response:
    return response.json()


def stuurgegevensnaarhue(hueip: str, hueuser: str, path: str, data: dict) -> dict:
  """ Sturen van gegevens naar de hue bridge 

  Args: hueip (str): Het IP-adres van de Hue bridge
        hueuser (str): De geautoriseerde gebruiker
        path (str): Het pad voor de te versturen gegevens
        data (dict): De te versturen gegevens

  Returns: dict: Het antwoord van de bridge in JSON-formaat
  """
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


def getschermen(pod: str, token: str) -> list:
  """ Ophalen van de schermen en in de db zetten 

  Args: pod (str): De pod-identificatie
        token (str): De geldige token

  Returns: list: Lijst met gevonden schermen
  """
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

  Returns: Template: De schermen-pagina of een redirect
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


def bepaalxyvanrgb(kleurwaarde: str) -> tuple[float, float, float]:
  """ Bepaal de xy waarde vanuit rgb 

  Args: kleurwaarde (str): De kleur in RGB hexadecimaal formaat

  Returns: tuple: h-waarde, s-waarde en brightness als decimale getallen
  """
  rood = float(int(kleurwaarde[1:3], 16)) / 255.0
  groen = float(int(kleurwaarde[3:5], 16)) / 255.0
  blauw = float(int(kleurwaarde[5:7], 16)) / 255.0
  hwaarde, swaarde, vwaarde = colorsys.rgb_to_hsv(rood, groen, blauw)
  hwaarde = round(hwaarde, 2)
  swaarde = round(swaarde, 2)
  brightness = round(vwaarde * 100, 2)
  return hwaarde, swaarde, brightness


def bepaalhexrgbvanxy(xwaarde: float, ywaarde: float, dimwaarde: int) -> str:
  """ Bepaal de rgb waarde vanuit de x/y/dim 

  Args: xwaarde (float): De x-coördinaat van de kleur
        ywaarde (float): De y-coördinaat van de kleur
        dimwaarde (int): De helderheid als percentage

  Returns: str: De kleur in RGB hexadecimaal formaat
  """
  vwaarde = float(dimwaarde / 100)
  rood, groen, blauw = colorsys.hsv_to_rgb(xwaarde, ywaarde, vwaarde)
  rwaarde = int(rood * 255.0)
  gwaarde = int(groen * 255.0)
  bwaarde = int(blauw * 255.0)
  retvalue = f'#{rwaarde:02x}{gwaarde:02x}{bwaarde:02x}'
  return retvalue


def zetlampenindb(lampen: list) -> None:
  """ Plaats de lampen in de envdb 

  Args: lampen (list): Lijst met lampen om op te slaan
  """
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

  Returns: Template: De lampen-pagina of een redirect
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
      rgbwaarde = bepaalhexrgbvanxy(xywaarde.get('x'), xywaarde.get('y'), dimwaarde)
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
    dblampen = leesenv('lampen')
  for lamp in dblampen:
    for lamp2 in lampen:
      if lamp.get('id') == lamp2.get('id'):
        lamp2['volgorde'] = lamp.get('volgorde')
        break
  return render_template('lampen.html',
                         lampen=sorted(lampen, key=lambda x: x['naam']),
                         gridbreedte=leesenv('gridbreedte'),
                         gridhoogte=leesenv('gridhoogte'),
                         zonnesterkte=haalzonnesterkte()
                         )


def verplaatsscherm(device: str, percentage: int) -> None:
  """ Verplaats een scherm 

  Args: device (str): De device-URL van het scherm
        percentage (int): Het gewenste openingspercentage
  """
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


def verplaatsalleschermen(percentage: int) -> None:
  """ Verplaats alle schermen naar zelfde percentage 

  Args: percentage (int): Het gewenste openingspercentage
  """
  schermen = leesenv('schermen')
  for scherm in schermen:
    deviceid = scherm.get('device')
    verplaatsscherm(deviceid, percentage)


def sluitalles() -> None:
  """ Sluiten van alle schermen 

  Zet alle schermen op 100% dicht
  """
  verplaatsalleschermen(100)


def openalles() -> None:
  """ Openen van alle schermen 

  Zet alle schermen op 0% dicht (volledig open)
  """
  verplaatsalleschermen(0)


def verversschermen() -> None:
  """ Ververs de opgeslagen schermen 

  Verwijdert de schermen uit de database zodat ze opnieuw worden opgehaald
  """
  deleteenv('schermen')


def doeactieoplamp(lampid: str, actie: dict) -> None:
  """ voer een actie uit op een lamp 

  Args: lampid (str): De ID van de lamp
        actie (dict): De uit te voeren actie
  """
  hueip = leesenv('hueip')
  hueuser = leesenv('hueuser')
  path = f'light/{lampid}'
  stuurgegevensnaarhue(hueip, hueuser, path, actie)


def zetlampaanuit(lampid: str, status: bool) -> None:
  """ zet een lamp aan of uit 

  Args: lampid (str): De ID van de lamp
        status (bool): True voor aan, False voor uit
  """
  actie = {'on': {'on': status}}
  doeactieoplamp(lampid, actie)


def zetlampaan(lampid: str) -> None:
  """ zet een lamp aan 

  Args: lampid (str): De ID van de lamp
  """
  zetlampaanuit(lampid, True)


def zetlampuit(lampid: str) -> None:
  """ zet een lamp uit 

  Args: lampid (str): De ID van de lamp
  """
  zetlampaanuit(lampid, False)


def dimlamp(lampid: str, dimwaarde: float) -> None:
  """ dim een lamp 

  Args: lampid (str): De ID van de lamp
        dimwaarde (float): De gewenste helderheid als percentage
  """
  zetlampaan(lampid)
  actie = {'dimming': {'brightness': dimwaarde}}
  doeactieoplamp(lampid, actie)


def kleurlamp(lampid: str, kleurwaarde: str) -> None:
  """ verander de kleur van een lamp 

  Args: lampid (str): De ID van de lamp
        kleurwaarde (str): De gewenste kleur in RGB hexadecimaal formaat
  """
  xwaarde, ywaarde, brightness = bepaalxyvanrgb(kleurwaarde)
  dimlamp(lampid, brightness)
  actie = {'color': {'xy': {'x': xwaarde, 'y': ywaarde}}}
  doeactieoplamp(lampid, actie)


def allelampenuit() -> None:
  """ Alle lampen uit 

  Zet alle bekende lampen uit
  """
  lampen = leesenv('lampen')
  for lamp in lampen:
    lampid = lamp.get('id')
    zetlampuit(lampid)


def ververslampen() -> None:
  """ Ververs de opgeslagen lampen 

  Verwijdert de lampen uit de database zodat ze opnieuw worden opgehaald
  """
  deleteenv('lampen')


@cached(cache=weercache)
def haalwindsnelheid() -> int:  # pragma: no cover
  """ Haal de informatie van het weer van Hattem op 

  Returns: int: De windsnelheid in Beaufort of 0 bij een fout
  """
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
def verstuurberichtmonitoring(bericht: str) -> None:
  """
    Verstuur bericht naar de monitoring,
    maar niet vaker dan eenmaal per dag

  Args: bericht (str): Het te versturen bericht
  """
  requests.post(url="https://ntfy.sh/vanderiethattemmonitoring",
                timeout=5,
                data=bericht)


def checkwindsnelheid() -> None:
  """ Check de windsnelheid 

  Controleert de windsnelheid en opent schermen bij te hoge wind
  """
  windbft = haalwindsnelheid()
  if windbft > 5:
    verstuurberichtmonitoring(f'Windsnelheid: {windbft}, schermen openen!')
    openalles()


def haalzonnesterkteuitdb() -> int:
  """ Haal de zonnesterkte uit de db 

  Returns: int: De laatst gemeten zonnesterkte of 0 als er geen meting is
  """
  records = zondb.getByQuery({'key': 'zonnesterkte'})
  if len(records) > 0:
    return records[0].get('value')
  zondb.add({'key': 'zonnesterkte', 'value': 0})
  return 0


def schakellampenaan(vorigesterkte: int, zonnesterkte: int):
  """ Schakel lampen aan bij donker worden 

  Args: vorigesterkte (int): De vorige gemeten zonnesterkte
        zonnesterkte (int): De huidige zonnesterkte
  """
  verstuurberichtmonitoring(f'Zonnesterkte van {vorigesterkte} naar {zonnesterkte}, lampen aan?')


def schakellampenuit(vorigesterkte: int, zonnesterkte: int):
  """ Schakel lampen uit bij licht worden 

  Args: vorigesterkte (int): De vorige gemeten zonnesterkte
        zonnesterkte (int): De huidige zonnesterkte
  """
  verstuurberichtmonitoring(f'Zonnesterkte van {vorigesterkte} naar {zonnesterkte}, lampen uit?')


def checkzonnesterkte() -> None:
  """ Check de zonnesterkte 

  Controleert of de zonnesterkte is veranderd en schakelt indien nodig lampen
  """
  vorigesterkte = haalzonnesterkteuitdb()
  zonnesterkte = haalzonnesterkte()
  tijd = datetime.now()
  if zonnesterkte < 400 < vorigesterkte and 9 <= tijd.hour < 23:
    schakellampenaan(vorigesterkte, zonnesterkte)
  if vorigesterkte < 400 < zonnesterkte and 9 <= tijd.hour < 23:
    schakellampenuit(vorigesterkte, zonnesterkte)
  zondb.updateByQuery({'key': 'zonnesterkte'},
                      {'key': 'zonnesterkte', 'value': zonnesterkte})


def haalzonnesensors(pod: str, token: str) -> list:
  """ Ophalen van de zonnesensors en in de db zetten 

  Args: pod (str): De pod-identificatie
        token (str): De geldige token

  Returns: list: Lijst met gevonden zonnesensors
  """
  sensorlijst = []
  path = f'setup/devices/controllables/{quote_plus("io:LightIOSystemSensor")}'
  sensorurls = haalgegevensvansomfy(token, pod, path)
  if not (isinstance(sensorurls, dict) and not sensorurls.get('error', None) is None):
    for sensorurl in sensorurls:
      sensorurlencoded = quote_plus(sensorurl)
      device = haalgegevensvansomfy(token, pod, f'setup/devices/{sensorurlencoded}')
      sensorlijst.append({'label': device['label'], 'device': sensorurl})
  envdb.add({'env': 'sensors', 'value': sensorlijst})
  return sensorlijst


@cached(cache=zonnesterktecache)
def haalzonnesterkte() -> int:
  """ Haal de zonnesterkte op 

  Returns: int: De gemeten zonnesterkte of een negatieve waarde bij een fout
  """
  token = leesenv('token')
  pod = leesenv('pod')
  if token is None or pod is None:
    return -1
  sensors = leesenv('sensors')
  if sensors is None:
    sensors = haalzonnesensors(pod, token)
  lichtsterkte = 'core:LuminanceState'
  for sensor in sensors:
    sensorurlencoded = quote_plus(sensor['device'])
    sensorwaarde = haalgegevensvansomfy(token,
                                        pod,
                                        f'setup/devices/{sensorurlencoded}/states/{lichtsterkte}')
    if isinstance(sensorwaarde, dict) and not sensorwaarde.get('error', None) is None:
      return -2
    return sensorwaarde.get('value', -3)
  return -4


@app.route('/thuis', methods=['GET'])
def thuispagina():
  """ Toon de hoofdpagina 

  Returns: Template: De hoofdpagina met instellingen
  """
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
  """ Verwerk de login 

  Verwerkt het inlogformulier en slaat de gegevens op

  Returns: Redirect: Terug naar de hoofdpagina
  """
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
  """ Verwerk het opvoeren van de pod 

  Verwerkt het pod-formulier en slaat de gegevens op

  Returns: Redirect: Terug naar de hoofdpagina
  """
  pod = request.form['pod']
  envdb.add({'env': 'pod', 'value': pod})
  return redirect('/thuis')


@app.route('/thuis/hueip', methods=['POST'])
def hueippagina():
  """ Verwerk het opvoeren van het ip van de hue 

  Verwerkt het Hue IP-formulier en slaat de gegevens op

  Returns: Redirect: Terug naar de hoofdpagina
  """
  hueip = request.form['hueip']
  deleteenv('hueip')
  envdb.add({'env': 'hueip', 'value': hueip})
  return redirect('/thuis')


@app.route('/thuis/hueuser', methods=['POST'])
def hueuserpagina():
  """ Verwerk het opvoeren van de hueuser 

  Verwerkt het Hue gebruiker-formulier en slaat de gegevens op

  Returns: Redirect: Terug naar de instellingenpagina
  """
  hueuser = request.form['hueuser']
  deleteenv('hueuser')
  envdb.add({'env': 'hueuser', 'value': hueuser})
  return redirect('/thuis/instellingen')


@app.route('/thuis/grid', methods=['POST'])
def gridpagina():
  """ Verwerk het aanpassen van de gridlayout 

  Verwerkt het grid-formulier en slaat de gegevens op

  Returns: Redirect: Terug naar de instellingenpagina
  """
  deleteenv('gridbreedte')
  envdb.add({'env': 'gridbreedte', 'value': int(request.form['gridbreedte'])})
  deleteenv('gridhoogte')
  envdb.add({'env': 'gridhoogte', 'value': int(request.form['gridhoogte'])})
  return redirect('/thuis/instellingen')


@app.route('/thuis/instellingen', methods=['GET'])
def instellingenpagina():
  """ Toon de pagina met alle instellingen 

  Returns: Template: De instellingenpagina
  """
  return haalinstellingenentoon()


@app.route('/thuis/instellingen', methods=['POST'])
def instellingenactiepagina():
  """ Verwerk een actie voor een token 

  Verwerkt acties voor tokens (aanmaken/verwijderen)

  Returns: Template/Redirect: De instellingenpagina of een redirect
  """
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
  """ Toon de pagina met de status van de schermen 

  Returns: Template: De schermenpagina
  """
  return haalschermenentoon()


@app.route('/thuis/lampen', methods=['GET'])
def lampenpagina():
  """ Toon de pagina met de lampen 

  Returns: Template: De lampenpagina
  """
  return haallampenentoon()


@app.route('/thuis/lampengrid', methods=['GET'])
def lampengridpagina():
  """ Toon de pagina met de lampengrid 

  Returns: Template: De lampengrid configuratiepagina
  """
  lampen = leesenv('lampen')
  return render_template('lampengrid.html',
                         lampen=sorted(lampen, key=lambda x: x['naam']),
                         gridbreedte=leesenv('gridbreedte'),
                         gridhoogte=leesenv('gridhoogte'),
                         )


@app.route('/thuis/schermen', methods=['POST'])
def schermenactiepagina():
  """ Verwerk het verplaatsen van een of meer schermen 

  Verwerkt acties voor schermen (open/dicht/verplaats)

  Returns: Redirect: Terug naar de schermenpagina
  """
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
def lampenactiepagina():
  """ Verwerk acties voor lampen 

  Verwerkt acties voor lampen (aan/uit/dim/kleur)

  Returns: Redirect: Terug naar de lampenpagina
  """
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


@app.route('/thuis/lampengrid', methods=['POST'])
def lampengridactiepagina():
  """ Verwerk de aanpassingen van de lampengrid 

  Verwerkt de nieuwe volgorde van lampen in het grid

  Returns: Redirect: Terug naar de lampengrid pagina
  """
  lampen = leesenv('lampen')
  for key in request.form.keys():
    val = request.form[key]
    for lamp in lampen:
      if lamp['id'] == key:
        lamp['volgorde'] = int(val)
        break
  deleteenv('lampen')
  envdb.add({'env': 'lampen', 'value': lampen})
  return redirect('/thuis/lampengrid')


def startwebserver() -> None:
  """ Start webserver 

  Start de waitress WSGI server op poort 8088
  """
  waitress.serve(app, host="0.0.0.0", port=8088)


if __name__ == '__main__':
  # Start webserver
  _thread.start_new_thread(startwebserver, ())

  checkwindsnelheid()
  # Elke kwartier check windsnelheid
  schedule.every(15).minutes.do(checkwindsnelheid)
  checkzonnesterkte()
  # Elke 2 minuten check zonnesterkte
  schedule.every(2).minutes.do(checkzonnesterkte)
  while True:
    waittime = max(schedule.idle_seconds(), 1.0)
    print(f'wacht {waittime} seconden')
    sleep(waittime)
    schedule.run_pending()
