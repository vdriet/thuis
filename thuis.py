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
import waitress
from cachetools import cached, TTLCache
from flask import Flask, render_template, request, redirect
from requests import ReadTimeout, JSONDecodeError

from gegevens import Gegevens
from hue import Hue
from somfy import Somfy

app = Flask(__name__,
            static_url_path='/static',
            template_folder='templates')
envdb = Gegevens('envdb.json')
zondb = Gegevens('zonnesterkte.json')
weercache = TTLCache(maxsize=1, ttl=900)
zonnesterktecache = TTLCache(maxsize=1, ttl=60)
monitoringcache = TTLCache(maxsize=1, ttl=86400)


def gethue() -> Hue | None:
  """ Maak een verbinding met de hue
  :returns: object naar hue
  """
  hueip = envdb.lees('hueip')
  hueuser = envdb.lees('hueuser')
  if not hueip or not hueuser:
    return None
  return Hue(hueip, hueuser)


def haalinstellingenentoon():
  """ Haal de instellingen van de server en toon deze
      Wanneer er gegevens missen, redirect naar hoofdpagina
  Returns: Template: De instellingen-pagina of een redirect
  """
  pod = envdb.lees('pod')
  jsessionid = envdb.lees('jsessionid')
  hueip = envdb.lees('hueip')
  hueuser = envdb.lees('hueuser')
  userid = envdb.lees('userid')
  password = envdb.lees('password')
  zonsterktelampen = envdb.leesint('zonsterktelampen', 400)
  starttijd = envdb.leesint('starttijd', 9)
  eindtijd = envdb.leesint('eindtijd', 23)
  if not jsessionid and userid and password:
    jsessionid = Somfy.login(userid, password)
    envdb.wijzig('jsessionid', jsessionid)
  tokens = []
  if pod and jsessionid:
    servertokens = Somfy.getavailabletokens(jsessionid, pod)
    if isinstance(servertokens, dict) and not servertokens.get('error', None) is None:
      envdb.verwijder('jsessionid')
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
                         jsessionid=jsessionid,
                         gridbreedte=envdb.lees('gridbreedte'),
                         gridhoogte=envdb.lees('gridhoogte'),
                         zonsterktelampen=zonsterktelampen,
                         starttijd=starttijd,
                         eindtijd=eindtijd,
                         )


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
  envdb.schrijf('schermen', schermlijst)
  return schermlijst


def haalschermenentoon():
  """ Haal de status van de schermen toon deze
      Wanneer er gegevens missen, redirect naar hoofdpagina
  Returns: Template: De schermen-pagina of een redirect
  """
  pod = envdb.lees('pod')
  token = envdb.lees('token')
  if not pod or not token:
    return redirect('/thuis')
  envschermen = envdb.lees('schermen')
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
  """ Plaats de lampen in de gegevens
  Args: lampen (list): Lijst met lampen om op te slaan
  """
  dblampen = []
  gridbreedte = envdb.lees('gridbreedte')
  if not gridbreedte:
    gridbreedte = 3
    envdb.schrijf('gridbreedte', gridbreedte)
  gridhoogte = envdb.lees('gridhoogte')
  if not gridhoogte:
    gridhoogte = 4
    envdb.schrijf('gridhoogte', gridhoogte)
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
  envdb.schrijf('lampen', dblampen)


def haallampen() -> list:
  """ Haal de status van de lampen
      Wanneer er gegevens missen, geef een lege lijst terug
  Returns: Template: De lampen-pagina of een redirect
  """
  bridge = gethue()
  if bridge is None:
    return []
  dblampen = envdb.lees('lampen')
  lampen = []
  lampdata = bridge.haalgegevens('light')

  if len(lampdata.get('errors', [])) != 0:
    return []

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
    dblampen = envdb.lees('lampen')
  for lamp in dblampen:
    for lamp2 in lampen:
      if lamp.get('id') == lamp2.get('id'):
        lamp2['volgorde'] = lamp.get('volgorde')
        break
  return lampen


def verplaatsscherm(device: str, percentage: int) -> None:
  """ Verplaats een scherm
  Args: device (str): De device-URL van het scherm
        percentage (int): Het gewenste openingspercentage
  """
  token = envdb.lees('token')
  pod = envdb.lees('pod')
  data = json.dumps({
    "label": "verplaats scherm",
    "actions": [
      {"commands": [
        {"name": "setClosure",
         "parameters": [percentage]
         }],
        "deviceURL": device
      }
    ]
  })
  stuurgegevensnaarsomfy(token=token, pod=pod, path='exec/apply', data=data)


def verplaatsalleschermen(percentage: int) -> None:
  """ Verplaats alle schermen naar zelfde percentage
  Args: percentage (int): Het gewenste openingspercentage
  """
  schermen = envdb.lees('schermen')
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
  envdb.verwijder('schermen')


def doeactieoplamp(lampid: str, actie: dict) -> None:
  """ voer een actie uit op een lamp
  Args: lampid (str): Het ID van de lamp
        actie (dict): De uit te voeren actie
  """
  bridge = gethue()
  path = f'light/{lampid}'
  bridge.stuurgegevens(path, actie)


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
  lampen = envdb.lees('lampen')
  for lamp in lampen:
    lampid = lamp.get('id')
    zetlampuit(lampid)


def ververslampen() -> None:
  """ Ververs de opgeslagen lampen 

  Verwijdert de lampen uit de database zodat ze opnieuw worden opgehaald
  """
  envdb.verwijder('lampen')


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
    Verstuur bericht naar de monitoring, maar niet vaker dan eenmaal per dag
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
  waarde = zondb.lees('zonnesterkte')
  if waarde:
    return waarde
  zondb.schrijf('zonnesterkte', 0)
  return 0


def schakellampenaan(vorigesterkte: int, zonnesterkte: int):
  """ Schakel lampen aan bij donker worden
  Args: vorigesterkte (int): De vorige gemeten zonnesterkte
        zonnesterkte (int): De huidige zonnesterkte
  """
  verstuurberichtmonitoring(f'Zonnesterkte van {vorigesterkte} naar {zonnesterkte}, lampen aan!')
  for lamp in envdb.lees('lampen'):
    if lamp.get('automatisch', False):
      zetlampaan(lamp.get('id'))


def schakellampenuit(vorigesterkte: int, zonnesterkte: int):
  """ Schakel lampen uit bij licht worden
  Args: vorigesterkte (int): De vorige gemeten zonnesterkte
        zonnesterkte (int): De huidige zonnesterkte
  """
  verstuurberichtmonitoring(f'Zonnesterkte van {vorigesterkte} naar {zonnesterkte}, lampen uit!')
  for lamp in envdb.lees('lampen'):
    if lamp.get('automatisch', False):
      zetlampuit(lamp.get('id'))


def checkzonnesterkte() -> None:
  """ Check de zonnesterkte
  Controleert of de zonnesterkte is veranderd en schakelt indien nodig lampen
  """
  vorigesterkte = haalzonnesterkteuitdb()
  zonnesterkte = haalzonnesterkte()
  zonsterktelampen = envdb.leesint('zonsterktelampen', 400)
  starttijd = envdb.leesint('starttijd', 9)
  eindtijd = envdb.leesint('eindtijd', 23)
  tijd = datetime.now()
  if zonnesterkte < zonsterktelampen < vorigesterkte and starttijd <= tijd.hour < eindtijd:
    schakellampenaan(vorigesterkte, zonnesterkte)
  if vorigesterkte < zonsterktelampen < zonnesterkte and starttijd <= tijd.hour < eindtijd:
    schakellampenuit(vorigesterkte, zonnesterkte)
  zondb.wijzig('zonnesterkte', zonnesterkte)


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
  envdb.schrijf('sensors', sensorlijst)
  return sensorlijst


@cached(cache=zonnesterktecache)
def haalzonnesterkte() -> int:
  """ Haal de zonnesterkte op
  Returns: int: De gemeten zonnesterkte of een negatieve waarde bij een fout
  """
  token = envdb.lees('token')
  pod = envdb.lees('pod')
  if not token or not pod:
    return -1
  sensors = envdb.lees('sensors')
  if not sensors:
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
  Returns: Template: De hoofdpagina met knoppen voor lampen en schermen.
  """
  lampen = haallampen()
  return render_template('hoofdpagina.html',
                         lampen=sorted(lampen, key=lambda x: x['naam']),
                         gridbreedte=envdb.lees('gridbreedte'),
                         gridhoogte=envdb.lees('gridhoogte'),
                         zonnesterkte=haalzonnesterkte(),
                         )


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
    Somfy.deletetoken(envdb.lees('jsessionid'), envdb.lees('pod'), uuid)
    sleep(1)
  elif actie == 'create':
    label = request.form['label']
    token = Somfy.createtoken(envdb.lees('jsessionid'), envdb.lees('pod'), label)
    envdb.wijzig('token', token)
    sleep(1)
  elif actie == 'updateautolampen':
    zonsterkte = request.form.get('zonsterkte', '')
    envdb.wijzig('zonsterktelampen', int(zonsterkte))
    starttijd = request.form.get('starttijd', '')
    envdb.wijzig('starttijd', int(starttijd))
    eindtijd = request.form.get('eindtijd', '')
    envdb.wijzig('eindtijd', int(eindtijd))
  elif actie == 'updatepod':
    pod = request.form['pod']
    envdb.wijzig('pod', pod)
    return redirect('/thuis')
  elif actie == 'login':
    userid = request.form['userid']
    password = request.form['password']
    bewaargegevens = request.form['savelogin']
    if bewaargegevens == 'on':
      envdb.wijzig('userid', userid)
      envdb.wijzig('password', password)
    jsessionid = Somfy.login(userid, password)
    envdb.wijzig('jsessionid', jsessionid)
  elif actie == 'updatehueuser':
    hueuser = request.form['hueuser']
    envdb.wijzig('hueuser', hueuser)
  elif actie == 'updatehueip':
    hueip = request.form['hueip']
    envdb.wijzig('hueip', hueip)
  elif actie == 'updategrid':
    envdb.wijzig('gridbreedte', int(request.form['gridbreedte']))
    envdb.wijzig('gridhoogte', int(request.form['gridhoogte']))
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
  lampen = haallampen()
  if not lampen:
    return redirect('/thuis')
  return render_template('lampen.html',
                         lampen=sorted(lampen, key=lambda x: x['naam']),
                         gridbreedte=envdb.lees('gridbreedte'),
                         gridhoogte=envdb.lees('gridhoogte'),
                         zonnesterkte=haalzonnesterkte()
                         )


@app.route('/thuis/lampengrid', methods=['GET'])
def lampengridpagina():
  """ Toon de pagina met de lampengrid
  Returns: Template: De lampengrid configuratiepagina
  """
  lampen = envdb.lees('lampen')
  for lamp in lampen:
    if not lamp.get('automatisch'):
      lamp['checked'] = False
  return render_template('lampengrid.html',
                         lampen=sorted(lampen, key=lambda x: x['naam']),
                         gridbreedte=envdb.lees('gridbreedte'),
                         gridhoogte=envdb.lees('gridhoogte'),
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
      verplaatsscherm(device, int(percentage))
  elif actie == 'sluitalles':
    sluitalles()
  elif actie == 'openalles':
    openalles()
  elif actie == 'ververs':
    verversschermen()
  if request.referrer and request.referrer.endswith('/thuis'):
    return redirect('/thuis')
  return redirect('/thuis/schermen')


@app.route('/thuis/lampen', methods=['POST'])
def lampenactiepagina():
  """ Verwerkt acties voor lampen (aan/uit/dim/kleur)
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
  if request.referrer and request.referrer.endswith('/thuis'):
    return redirect('/thuis')
  return redirect('/thuis/lampen')


@app.route('/thuis/lampengrid', methods=['POST'])
def lampengridactiepagina():
  """ Verwerkt de nieuwe volgorde van lampen in het grid
  Returns: Redirect: Terug naar de lampengrid pagina
  """
  lampen = envdb.lees('lampen')
  for lamp in lampen:
    lamp['automatisch'] = False
  for key in request.form.keys():
    val = request.form[key]
    lampid = key[:-5]
    if key.endswith('plek'):
      for lamp in lampen:
        if lamp['id'] == lampid:
          lamp['volgorde'] = int(val)
          break
    elif key.endswith('auto'):
      for lamp in lampen:
        if lamp['id'] == lampid:
          lamp['automatisch'] = True
          break
  envdb.wijzig('lampen', lampen)
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
