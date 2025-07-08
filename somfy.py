""" Aansturing van somfy """
from urllib.parse import quote_plus

import requests

BASEURL = 'ha101-1.overkiz.com'


class Somfy:
  """ Aansturing van somfy """

  @staticmethod
  def login(userid: str, password: str) -> str:
    """
    Inloggen bij somfy voor ophalen key
    Args: userid (str): De gebruikersnaam voor Somfy
          password (str): Het wachtwoord voor Somfy
    Returns: Het verkregen sessie-ID
    :rtype: str
    """
    url = f'https://{BASEURL}/enduser-mobile-web/enduserAPI/login'

    data = f'userId={quote_plus(userid)}&userPassword={quote_plus(password)}'
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}
    with requests.post(url=url, timeout=10, headers=headers, data=data) as response:
      jsessionid = response.cookies.get('JSESSIONID')
    return jsessionid

  @staticmethod
  def getavailabletokens(jsessionid: str, pod: str) -> list:
    """
    Haal beschikbare tokens van de server
    Args: jsessionid (str): De geldige sessie-ID
          pod (str): De pod-identificatie
    Returns: Lijst met beschikbare tokens
    :rtype: list
    """
    url = f'https://{BASEURL}/enduser-mobile-web/enduserAPI/config/{pod}/local/tokens/devmode'
    headers = {'Accept': 'application/json',
               'Cookie': f'JSESSIONID={jsessionid}'}
    with requests.get(url=url, headers=headers, timeout=10) as response:
      contentjson = response.json()
    return contentjson

  @staticmethod
  def createtoken(jsessionid: str, pod: str, label: str) -> str:
    """
    Voeg een token toe op de server
    Args: jsessionid (str): De geldige sessie-ID
          pod (str): De pod-identificatie
          label (str): Het label voor de nieuwe token
    Returns: token
    :rtype: str
    """
    url = f'https://{BASEURL}/enduser-mobile-web/enduserAPI/config/{pod}/local/tokens/generate'
    headers = {'Content-Type': 'application/json'
      , 'Cookie': f'JSESSIONID={jsessionid}'}
    with requests.get(url=url, headers=headers, timeout=10) as response:
      contentjson = response.json()
      rettoken = contentjson['token']
      Somfy.activatetoken(jsessionid, pod, label, rettoken)
      return rettoken

  @staticmethod
  def activatetoken(jsessionid: str, pod: str, label: str, token: str) -> None:
    """
    Activeer een token
    Args: jsessionid (str): De geldige sessie-ID
          pod (str): De pod-identificatie
          label (str): Het label voor het token
          token (str): Het te activeren token
    :rtype: None
    """
    url = f'https://{BASEURL}/enduser-mobile-web/enduserAPI/config/{pod}/local/tokens'
    headers = {'Content-Type': 'application/json',
               'Cookie': f'JSESSIONID={jsessionid}'}
    data = f'{{"label": "{label}", "token": "{token}", "scope": "devmode"}}'.encode('utf-8')
    with requests.post(url=url, headers=headers, data=data, timeout=10):
      pass

  @staticmethod
  def deletetoken(jsessionid: str, pod: str, uuid: str) -> int:
    """
    Verwijder een token van de server
    Args: jsessionid (str): De geldige sessie-ID
          pod (str): De pod-identificatie
          token (str): Het te activeren token
    Returns: HTTP-statuscode van de verwijder-actie
    :rtype: int
    """
    url = f'https://{BASEURL}/enduser-mobile-web/enduserAPI/config/{pod}/local/tokens/{uuid}'
    headers = {'Content-Type': 'application/json'
      , 'Cookie': f'JSESSIONID={jsessionid}'}
    with requests.delete(url=url, headers=headers, timeout=10) as response:
      return response.status_code

  @staticmethod
  def haalgegevens(token: str, pod: str, path: str) -> dict:
    """ Ophalen van gegevens van het somfy kastje
    Args: token (str): De geldige token
          pod (str): De pod-identificatie
          path (str): Het pad naar de op te vragen gegevens
    Returns: De opgehaalde gegevens in JSON-formaat
    :rtype: dict
    """
    url = f'https://{pod}.local:8443/enduser-mobile-web/1/enduserAPI/{path}'
    headers = {'Content-type': 'application/json', 'Authorization': f'Bearer {token}'}
    with requests.get(url=url,
                      headers=headers,
                      timeout=5,
                      verify='./cert/overkiz-root-ca-2048.crt') as response:
      return response.json()

  @staticmethod
  def stuurgegevens(token: str, pod: str, path: str, data: str) -> dict:
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

  @staticmethod
  def haaldevices(pod: str, token: str, path: str) -> list:
    """
    Ophalen van devices
    Args: pod (str): De pod-identificatie
          token (str): De geldige token
          path(str): Het pad van de devices
    Returns: list: Lijst met gevonden devices
    """
    devicelijst = []
    deviceurls = Somfy.haalgegevens(token, pod, path)
    if not (isinstance(deviceurls, dict) and not deviceurls.get('error', None) is None):
      for schermurl in deviceurls:
        scherurlencoded = quote_plus(schermurl)
        device = Somfy.haalgegevens(token, pod, f'setup/devices/{scherurlencoded}')
        devicelijst.append({'label': device['label'], 'device': schermurl})
    return devicelijst

  @staticmethod
  def haalschermen(pod: str, token: str) -> list:
    """
    Ophalen van de schermen
    Args: pod (str): De pod-identificatie
          token (str): Een geldig token
    Returns: list: Lijst met gevonden schermen
    """
    path = f'setup/devices/controllables/{quote_plus("io:VerticalExteriorAwningIOComponent")}'
    return Somfy.haaldevices(pod, token, path)

  @staticmethod
  def haalzonnesensors(pod: str, token: str) -> list:
    """
    Ophalen van de zonnesensors
    Args: pod (str): De pod-identificatie
          token (str): Een geldig token
    Returns: list: Lijst met gevonden zonnesensors
    """
    path = f'setup/devices/controllables/{quote_plus("io:LightIOSystemSensor")}'
    return Somfy.haaldevices(pod, token, path)
