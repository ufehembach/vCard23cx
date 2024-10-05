#!/usr/bin/env python3
#-*- coding: utf-8 -*-

import vobject
import hashlib
import re
import mysql.connector
from mysql.connector import errorcode
from datetime import datetime
import logging
import requests
from xml.etree import ElementTree
import urllib.parse
from urllib.parse import urlparse
from requests.auth import HTTPBasicAuth
from xml.etree import ElementTree
import argparse
import configparser
import logging
import os


# Funktion zur Normalisierung von Telefonnummern
def normalisiere_telefonnummer(telefonnummer):
    # Entfernt unerwünschte Zeichen und normalisiert die Telefonnummer
    nummer = re.sub(r'[()\s-]', '', telefonnummer)
    if nummer.startswith('0'):
        nummer = re.sub(r'^0', '+49', nummer)  # Beispiel für Deutschland
    return nummer

# Funktion zur Generierung eines Primary Keys aus Name, normalisierter Telefonnummer und Typ
def generiere_primary_key(name, telefonnummer, tel_typ):
    daten = name + telefonnummer + tel_typ
    return hashlib.sha256(daten.encode('utf-8')).hexdigest()

# Funktion zur Verarbeitung einer vCard
def verarbeite_vcard(vcard,cursor):
    # Extrahiere den vollständigen Namen
    name = vcard.contents['fn'][0].value if 'fn' in vcard.contents else ''

    # Extrahiere alle Telefonnummern und deren Typen
    telefonnummern = vcard.contents.get('tel', [])

    # Verarbeite jede Telefonnummer einzeln
    for tel in telefonnummern:
        telefonnummer = tel.value
        tel_typ = ','.join(tel.params['TYPE']) if 'TYPE' in tel.params else 'UNKNOWN'

        # Normalisiere die Telefonnummer
        normalisierte_nummer = normalisiere_telefonnummer(telefonnummer)

        # Generiere einen Primary Key
        primary_key = generiere_primary_key(name, normalisierte_nummer, tel_typ)

        # Aktuelles Datum als Eintragsdatum
        eintragsdatum = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        print(f"\rEntry: {name} {normalisierte_nummer} {tel_typ}                   ",end='', flush=True)
        # SQL-Abfrage: Einfügen oder Aktualisieren
        sql = """
        INSERT INTO contacts (id, FullName, PhoneNumber, PhoneType, EntryDate)
        VALUES (%s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            FullName = VALUES(FullName),
            PhoneNumber = VALUES(PhoneNumber),
            PhoneType = VALUES(PhoneType),
            EntryDate = VALUES(EntryDate)
        """
        values = (primary_key, name, normalisierte_nummer, tel_typ, eintragsdatum)
        
        cursor.execute(sql, values)
    print(f"Done", flush=True)

def getOneCard(config,vCardLink):

    #vCard-Daten von der URL abrufen mit Basic Authentication
    auth = HTTPBasicAuth(config['carddav']['user'], config['carddav']['pass'])
    response = requests.get(vCardLink, auth=(config['carddav']['user'], config['carddav']['pass']))

    # Prüfen, ob der Abruf erfolgreich war
    if response.status_code == 200:
    # Wenn der Statuscode 200 ist, versuche, die VCard auszulesen
        try:
            vcard = vobject.readOne(response.text)
        except Exception as e:
            # Wenn es ein Problem beim Lesen der VCard gibt, setze vcard auf None
            print(f"Fehler beim Auslesen der VCard: {e}")
            vcard = None
    else:
        # Wenn der Statuscode nicht 200 ist, gib ein leeres Ergebnis zurück
        vcard = None
    return vcard

def updateDB(config,db,vCardLinks):
    # Beispiel vCard-Daten (dies wäre das Laden aus einem CardDAV-Server)
    cursor = db.cursor()

    vCardLink = '''
BEGIN:VCARD
VERSION:3.0
FN:John Doe
TEL;TYPE=CELL:(0221) 987-654
TEL;TYPE=WORK:+49123456789
END:VCARD
'''

    # vCard parsen
    #vcard = vobject.readOne(vCardLink)
    for vCardLink in vCardLinks:
        #vcard holen
        vCard = getOneCard(config,vCardLink)
        print(f"\rvCard {vCard.contents['fn'][0].value}                   ",end='', flush=True)
        # vCard verarbeiten
        verarbeite_vcard(vCard,cursor)

    # Änderungen an der Datenbank übernehmen
    db.commit()
    # Alte Einträge entfernen
    loesche_alte_eintraege(db)

    # Schließe die Verbindung zur Datenbank
    cursor.close()
    db.close()


# Alte Einträge mit älterem Eintragsdatum löschen
def loesche_alte_eintraege(db):
    cursor = db.cursor()
    # Definiere die Löschkriterien basierend auf einem älteren Datum
    sql = """
    DELETE FROM contacts WHERE EntryDate < %s
    """
    alte_datum = datetime.now().strftime('%Y-%m-%d 00:00:00')  # Beispiel: Entferne Einträge von vor Mitternacht
    cursor.execute(sql, (alte_datum,))
    db.commit()

def erstelle_tabelle_wenn_nicht_existiert(db_cursor):
    # SQL-Abfrage, um die Existenz der Tabelle zu prüfen und nur zu erstellen, wenn sie nicht existiert
    sql_create_table = """
    CREATE TABLE IF NOT EXISTS contacts (
        id CHAR(64) PRIMARY KEY,  -- SHA-256 Hash
        FullName VARCHAR(255),
        PhoneNumber VARCHAR(50),
        PhoneType VARCHAR(50),
        EntryDate DATETIME
    );
    """
    
    try:
        # Ausführen der Abfrage zur Tabellenerstellung
        db_cursor.execute(sql_create_table)
        print("Tabelle 'contacts' erfolgreich erstellt oder existiert bereits.")
    except mysql.connector.Error as err:
        print(f"Fehler bei der Tabellenerstellung: {err}")


def extract_host(url):
    parsed_url = urlparse(url)
    return parsed_url.hostname

def getAllVcardLinks(config):
    auth = HTTPBasicAuth(config['carddav']['user'], config['carddav']['pass'])
    url = config['carddav']['url']

    headers = {
        "Depth": "1",
        "Content-Type": "application/xml; charset=utf-8"
    }
    body = '''<?xml version="1.0" encoding="UTF-8" ?>
    <d:propfind xmlns:d="DAV:" xmlns:cs="http://calendarserver.org/ns/">
      <d:prop>
        <d:getetag />
        <d:displayname />
        <d:getcontenttype />
      </d:prop>
    </d:propfind>'''

    response = requests.request("PROPFIND", url, headers=headers, data=body, auth=auth)

    if response.status_code == 207:
        tree = ElementTree.fromstring(response.content)
        myVcardLinks = []
        for response in tree.findall("{DAV:}response"):
            href = response.find("{DAV:}href").text
            host = extract_host(url)
            content_type = response.find(".//{DAV:}getcontenttype")
            print(f"\rvCard {len(myVcardLinks)}", end='', flush=True) 

            # Verwende urljoin, um Basis-URL und relative URL korrekt zu kombinieren
            full_url = urllib.parse.urljoin(url, href)
            if content_type is not None:
                if 'text/x-vcard' in content_type.text:
                    myVcardLinks.append("https://"+host + href)
            else:
                print("Content-Type ist None")

        print(f"\rfound {len(myVcardLinks)}")
        return myVcardLinks
    else:
        print(f"Fehler beim Abrufen der VCard-Links: {response.status_code}")
        return []


def main():
    import argparse
    import configparser

    parser = argparse.ArgumentParser()
    parser.add_argument('ini_file')
    parser.add_argument("--no-update", help="Don't write to db ", action='store_true', default=False)
    args = parser.parse_args()

    config = configparser.RawConfigParser()
    config.read(args.ini_file)
    print (config)
    db = mysql.connector.connect(user=config['db']['user'], password=config['db']['password'],
        host=config['db']['host'], database=config['db']['database'])
    # Tabelle erstellen (falls nicht vorhanden)
    erstelle_tabelle_wenn_nicht_existiert(db.cursor())
    vCardLinks = getAllVcardLinks(config)
    updateDB(config, db, vCardLinks)

if __name__ == "__main__":
    logger = logging.getLogger(__name__)
    main()

    
