""" Aansturing van hue """
import json

import requests
import urllib3


class Hue:
  """ Aansturing van hue """

  def __init__(self, hueip: str, hueuser: str):
    """ Verbinding met de hue bridge
    Args: hueip (str): Het IP-adres van de Hue bridge
          hueuser (str): De geautoriseerde gebruiker
    """
    self.hueip = hueip
    self.hueuser = hueuser

  def haalgegevens(self, path: str) -> dict:
    """
    Ophalen van gegevens van de hue bridge
    Args: hueip (str): Het IP-adres van de Hue bridge
          hueuser (str): De geautoriseerde gebruiker
          path (str): Het pad naar de op te vragen gegevens
    Returns: dict: De opgehaalde gegevens in JSON -formaat
    """
    urllib3.disable_warnings()
    url = f'https://{self.hueip}/clip/v2/resource/{path}'
    headers = {'Content-type': 'application/json',
               'hue-application-key': self.hueuser}
    with requests.get(url=url,
                      headers=headers,
                      timeout=5,
                      verify=False) as response:
      return response.json()

  def stuurgegevens(self, path: str, data: dict) -> dict:
    """
    Sturen van gegevens naar de hue bridge
    Args: hueip (str): Het IP-adres van de Hue bridge
          hueuser (str): De geautoriseerde gebruiker
          path (str): Het pad voor de te versturen gegevens
          data (dict): De te versturen gegevens
    Returns: dict: Het antwoord van de bridge in JSON-formaat
    """
    urllib3.disable_warnings()
    url = f'https://{self.hueip}/clip/v2/resource/{path}'
    headers = {'Content-type': 'application/json',
               'hue-application-key': self.hueuser}
    with requests.put(url=url,
                      headers=headers,
                      timeout=5,
                      verify=False,
                      data=json.dumps(data)) as response:
      return response.json()
