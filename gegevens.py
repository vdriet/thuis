""" Beheer van gegevens in een bestand """
from typing import Any

from pysondb import db


class Gegevens:
  """
    Beheer van gegevens
  """

  def __init__(self, bestand: str):
    """
    Maken of openen van een bestand
      Args: bestand(str): naam van het bestand
    """
    self.gegevens = db.getDb(bestand)

  def schrijf(self, sleutel: str, waarde: Any):
    """
      Schrijf gegevens naar het bestand
      Args: sleutel (str): De naam van het gegeven
            waarde (Any): De waarde
    """
    self.gegevens.add({'env': sleutel, 'value': waarde})

  def lees(self, sleutel: str):
    """
      Lees een gegeven uit het bestand
      Args: sleutel (str): De naam van het op te halen gegeven
      Returns: De waarde van het gegeven of None als het niet bestaat
    """
    rijen = self.gegevens.getByQuery({'env': sleutel})
    if len(rijen) != 1:
      return None
    return rijen[0].get('value')

  def leesint(self, sleutel: str, waarde: int):
    """
      Lees een gegeven uit het bestand, wanneer niet gevonden geef dan standaard waarde
      :param sleutel (str): De naam van het gegeven
      :param waarde: De standaard waarde van het gegeven als het niet in het bestand staat
      :return: De waarde van het gegeven uit het bestand of de standaard waarde
    """
    dbwaarde = self.lees(sleutel)
    if dbwaarde:
      return dbwaarde
    return waarde

  def wijzig(self, sleutel: str, waarde: Any):
    """
      Wijzig gegevens in het bestand
      Args: sleutel (str): De naam van het gegeven
            waarde (Any): De waarde
    """
    self.verwijder(sleutel)
    self.schrijf(sleutel, waarde)

  def verwijder(self, sleutel: str):
    """
      Verwijder gegevens uit het bestand
      Args: sleutel (str): De naam van het te verwijderen gegeven
    """
    rows = self.gegevens.getByQuery({'env': sleutel})
    for row in rows:
      self.gegevens.deleteById(row.get('id'))
