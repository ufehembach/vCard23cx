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
#import vcard
import mysql.connector
import base64
import os
import shutil



# Funktion zur Normalisierung von Telefonnummern
def normalizeTel(telefonnummer):
    # Entfernt unerwünschte Zeichen und normalisiert die Telefonnummer
    nummer = re.sub(r'[()\s-]', '', telefonnummer)
    if nummer.startswith('0'):
        nummer = re.sub(r'^0', '+49', nummer)  # Beispiel für Deutschland
    return nummer

# Funktion zur Generierung eines Primary Keys aus Name, normalisierter Telefonnummer und Typ
def generiere_primary_key(name, telefonnummer, tel_typ):
    daten = name + telefonnummer + tel_typ
    return hashlib.sha256(daten.encode('utf-8')).hexdigest()

def mapTelFields(vcardTelEntries):
    
    # Mapping der vcard-Typen zu den Datenbankfeldern
    typeToFieldMap = {
        'CELL': 'phoneMobile',
        'IPHONE': 'phoneMobile',
        'VOICE': 'phoneMobile',  # Manche 'VOICE' Typen könnten auch mobil sein

        'HOME': 'phoneHome',
        'home': 'phoneHome',

        'WORK': 'phoneBusiness',
        'work': 'phoneBusiness',
    
        'FAX': 'faxBusiness',  # Wir nehmen an, dass es ein geschäftliches Fax ist

        'pager': 'pager',

        'OTHER': 'phoneOther',
        'MAIN': 'phoneBusiness',  # Wenn MAIN, dann nehmen wir 'phoneBusiness' an
    
        'PREF': None,  # PREF ist keine Nummer, sondern ein Prioritätsindikator
        'pref': None   # PREF ignorieren wir in der Zuweisung
    }

    # Die Datenbankfelder initialisieren
    dbFields = {
        'phoneMobile': None,
        'phoneMobile2': None,
        'phoneHome': None,
        'phoneHome2': None,
        'phoneBusiness': None,
        'phoneBusiness2': None,
        'phoneOther': None,
        'faxBusiness': None,
        'faxHome': None,
        'pager': None
    }

# Beispiel vcard-Daten, die du parst (als Liste von Typen und Nummern)
#vcardTelEntries = [
#    {'type': ['CELL'], 'number': '+123456789'},
#    {'type': ['HOME'], 'number': '+987654321'},
#    {'type': ['WORK', 'FAX'], 'number': '+111222333'},
#    {'type': ['WORK'], 'number': '+444555666'}
#]

    # Zuweisung der Telefonnummern
    for entry in vcardTelEntries:
        types = entry['type']
        number = entry['number']
        number = normalizeTel(number)
        print(f"{types}: {number}; ",end='', flush=True)
        logging.info(f"{type}: {number}; ")
        for telType in types:
            dbField = typeToFieldMap.get(telType.upper())
            
            if dbField:
                # Wenn das Feld schon belegt ist, auf das zweite Feld gehen
                if dbFields[dbField] is None:
                    dbFields[dbField] = number
                else:
                    # Zweites Feld benutzen, z.B. phoneMobile2, phoneHome2 usw.
                    secondField = dbField + '2'
                    if secondField in dbFields and dbFields[secondField] is None:
                        dbFields[secondField] = number

    # Ergebnis anzeigen
    #for field, number in dbFields.items():
    #    print(f"{field}: {number}; ",end='', flush=True)
    return dbFields

def extractPhoneNumbers(vcard):
    vcardTelEntries = []

    # Alle Telefonnummern durchlaufen
    for telKey in vcard.contents.keys():
        if telKey.startswith('tel'):
            # Telefonnummern und Parameter aus der vcard extrahieren
            tel_feld = vcard.contents[telKey][0]  # Das erste Element in der Liste
            number = tel_feld.value
            #telType = tel_feld.params.get('type', [])  # Die Typen-Parameter auslesen
            telType = tel_feld.params['TYPE']  # Typen hinzufügen
            # Typen in eine Liste umwandeln, falls vorhanden
            if isinstance(telType, list):
                telTypeList = telType
            else:
                telTypeList = [telType]  # In eine Liste umwandeln, wenn es kein List ist

            # Eintrag zur Liste hinzufügen
            vcardTelEntries.append({'type': telTypeList, 'number': number})

    return vcardTelEntries

def extract_photo_from_vcard(vcard, photo_path):
    # Überprüfen, ob die vCard ein Foto enthält
    if hasattr(vcard, 'photo'):
        photo = vcard.photo

        # Überprüfen, ob das Foto die erwarteten Daten enthält
        if hasattr(photo, 'value'):
            # Extrahiere die Base64-codierten Fotodaten
            photo_data_base64 = photo.value

            # Decodiere die Base64-Daten
            try:
                photo_data = base64.b64decode(photo_data_base64)

                # Sicherstellen, dass das Zielverzeichnis existiert
                os.makedirs(os.path.dirname(photo_path), exist_ok=True)

                # Schreibe die decodierten Daten in die Datei
                with open(photo_path, 'wb') as photo_file:
                    photo_file.write(photo_data)
                print(f"Foto wurde erfolgreich extrahiert und in {photo_path} gespeichert.")
            except (TypeError, ValueError) as e:
                print(f"Fehler beim Decodieren der Base64-Daten: {e}")
        else:
            print("Die vCard enthält kein gültiges Foto.")
    else:
        print("Die vCard enthält kein Foto.")

def extended_extract_photo_from_vcard(vcard, photo_path):
    if hasattr(vcard, 'photo'):
        photo = vcard.photo

        # Überprüfen, ob es sich um ein embedded photo handelt
        if 'BASE64' in photo.encoding:
            photo_data_base64 = photo.value
            try:
                photo_data = base64.b64decode(photo_data_base64)
                with open(photo_path, 'wb') as photo_file:
                    photo_file.write(photo_data)
                print(f"Foto gespeichert unter: {photo_path}")

        # Überprüfen, ob es sich um einen URI handelt
        elif 'URI' in photo.encoding:
            # Hier könntest du eine Funktion hinzufügen, um das Bild von der URL herunterzuladen
            print(f"Foto-URL gefunden: {photo.value}")

        else:
            print("Unbekanntes Encoding oder kein Foto verfügbar.")
    else:
        print("Die vCard enthält kein Foto.")


# Funktion zur Verarbeitung einer vcard
def verarbeite_vcard(vcard,db,photoFolder):
        cursor = db.cursor()
    # vcard abrufen und in MySQL einfügen
    #try:
        contactid = vcard.contents['uid'][0].value if 'uid' in vcard.contents else ''
        firstname = vcard.contents['fn'][0].value.split()[0] if 'fn' in vcard.contents else ''
        lastname =  vcard.contents['fn'][0].value.split()[-1] if 'fn' in vcard.contents else ''
        print(f"\rvcard {firstname} {lastname}                    ",end='', flush=True)
        logging.info (f"vcard {firstname} {lastname}")

        companyname = ', '.join(vcard.contents['org'][0].value) if 'org' in vcard.contents else ''

        email = vcard.contents['email'][0].value if 'email' in vcard.contents else ''

        # ... type felder
        #['work', 'WORK', 'VOICE', 'PREF', 'pref', 'pager', 'OTHER', 'MAIN', 'IPHONE', 'home', 'HOME', 'FAX', 'CELL', 'cell']

        vcardTelEntries = extractPhoneNumbers(vcard)
        dbFields=mapTelFields(vcardTelEntries)

        phonemobile = dbFields['phoneMobile']
        phonemobile2 = dbFields ['phoneMobile2']
        phonehome = dbFields ['phoneHome']
        phonehome2 = dbFields [ 'phoneHome2']
        phonebusiness = dbFields ['phoneBusiness']
        phonebusiness2 = dbFields [ 'phoneBusiness2']
        phoneother = dbFields [ 'phoneOther']
        faxbusiness = dbFields ['faxBusiness']
        faxhome = dbFields ['faxHome']
        pager = dbFields ['pager']

        #photourl= vcard.contents['photo'][0].value if 'photo' in vcard.contents else ''
        photourl = photoFolder + '/' + contactid + '.jpg'

        lastupdate = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        extract_photo_from_vcard(vcard, photoFolder + '/' + contactid + '.jpg')

        # SQL-Insert oder Update
        sql = """
        INSERT INTO contacts (contactid, firstname, lastname, companyname, email, phonemobile, phonemobile2, phonehome, phonehome2, phonebusiness, phonebusiness2, phoneother, faxbusiness, faxhome, pager, photourl, lastupdate)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        ON DUPLICATE KEY UPDATE
            contactid=VALUES(contactid),
            firstname=VALUES(firstname),
            lastname=VALUES(lastname),
            companyname=VALUES(companyname),
            email=VALUES(email),
            phonemobile=VALUES(phonemobile),
            phonemobile2=VALUES(phonemobile2),
            phonehome=VALUES(phonehome),
            phonehome2=VALUES(phonehome2),
            phonebusiness=VALUES(phonebusiness),
            phonebusiness2=VALUES(phonebusiness2),
            phoneother=VALUES(phoneother),
            faxbusiness=VALUES(faxbusiness),
            faxhome=VALUES(faxhome),
            pager=VALUES(pager),
            photourl=VALUES(photourl),
            lastupdate=VALUES(lastupdate)

        """
        cursor.execute(sql, (contactid, firstname, lastname, companyname, email, phonemobile, phonemobile2, phonehome, phonehome2, phonebusiness, phonebusiness2, phoneother, faxbusiness, faxhome, pager, photourl, lastupdate))
       # db.commit()
        print(f"Done", flush=True)
    #except Exception as e:
        # Protokolliere den Fehler in eine Datei
    #    logging.error(f"Fehler bei Verarbeitung des Eintrags {vcard}: {str(e)}")


def getOneCard(config,vcardLink):

    #vcard-Daten von der URL abrufen mit Basic Authentication
    auth = HTTPBasicAuth(config['carddav']['user'], config['carddav']['pass'])
    response = requests.get(vcardLink, auth=(config['carddav']['user'], config['carddav']['pass']))

    # Prüfen, ob der Abruf erfolgreich war
    if response.status_code == 200:
    # Wenn der Statuscode 200 ist, versuche, die VCard auszulesen
        try:
            vcard = vobject.readOne(response.text)
            feldTypAdd(vcard)
        except Exception as e:
            # Wenn es ein Problem beim Lesen der VCard gibt, setze vcard auf None
            print(f"Fehler beim Auslesen der VCard: {e}")
            vcard = None
    else:
        # Wenn der Statuscode nicht 200 ist, gib ein leeres Ergebnis zurück
        vcard = None
    return vcard

def updateDB(config,db,vcardLinks,photoFolder):
    # Beispiel vcard-Daten (dies wäre das Laden aus einem CardDAV-Server)
    cursor = db.cursor()

    # vcard parsen
    #vcard = vobject.readOne(vcardLink)
    for vcardLink in vcardLinks:
        #vcard holen
        vcard = getOneCard(config,vcardLink)
        # vcard verarbeiten
        verarbeite_vcard(vcard,db,photoFolder)
    # Änderungen an der Datenbank übernehmen
    db.commit()
    # Alte Einträge entfernen
    delObsoleteEntries(db)

    # Schließe die Verbindung zur Datenbank
    cursor.close()
    db.close()


# Alte Einträge mit älterem Eintragsdatum löschen
def delObsoleteEntries(db):
    cursor = db.cursor()
    # Definiere die Löschkriterien basierend auf einem älteren Datum
    sql = """
    DELETE FROM contacts WHERE lastupdate < %s
    """
    oldDate = datetime.now().strftime('%Y-%m-%d 00:00:00')  # Beispiel: Entferne Einträge von vor Mitternacht
    cursor.execute(sql, (oldDate,))
    db.commit()

def createTableIfNotExists(db_cursor):
    # SQL-Abfrage, um die Existenz der Tabelle zu prüfen und nur zu erstellen, wenn sie nicht existiert
    sql_create_table = """
    CREATE TABLE contacts (
    contactid VARCHAR(255) PRIMARY KEY,
    firstname VARCHAR(255),
    lastname VARCHAR(255),
    companyname VARCHAR(255),
    email VARCHAR(255),
    phonemobile VARCHAR(50),
    phonemobile2 VARCHAR(50),
    phonehome VARCHAR(50),
    phonehome2 VARCHAR(50),
    phonebusiness VARCHAR(50),
    phonebusiness2 VARCHAR(50),
    phoneother VARCHAR(50),
    faxbusiness VARCHAR(50),
    faxhome VARCHAR(50),
    pager VARCHAR(50),
    photourl VARCHAR(255),
    lastupdate DATETIME
    );
"""
    
    try:
        # Ausführen der Abfrage zur Tabellenerstellung
        db_cursor.execute(sql_create_table)
        print("Tabelle 'contacts' erfolgreich erstellt oder existiert bereits.")
        logging.info("Tabelle 'contacts' erfolgreich erstellt oder existiert bereits.")
    except mysql.connector.Error as err:
        print(f"Fehler bei der Tabellenerstellung: {err}")
        logging.info(f"Fehler bei der Tabellenerstellung: {err}")


def extract_host(url):
    parsed_url = urlparse(url)
    return parsed_url.hostname

def getAllVcardLinks(config):
    auth = HTTPBasicAuth(config['carddav']['user'], config['carddav']['pass'])
    url = config['carddav']['url']
    print(auth)
    print(url)
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
    try:
        response = requests.request("PROPFIND", url, headers=headers, data=body, auth=auth)
        if response.status_code == 207:
            tree = ElementTree.fromstring(response.content)
            myVcardLinks = []
            for response in tree.findall("{DAV:}response"):
                href = response.find("{DAV:}href").text
                host = extract_host(url)
                content_type = response.find(".//{DAV:}getcontenttype")
                print(f"\rvcard {len(myVcardLinks)}", end='', flush=True) 

                # Verwende urljoin, um Basis-URL und relative URL korrekt zu kombinieren
                full_url = urllib.parse.urljoin(url, href)
                if content_type is not None:
                    if 'text/x-vcard' in content_type.text:
                        myVcardLinks.append("https://"+host + href)
                   #     logging.info ("https://"+host + href)
                else:
                    print("Content-Type ist None")

            print(f"\rfound {len(myVcardLinks)}")
            logging.info (f"found {len(myVcardLinks)} vcards")
            return myVcardLinks
        else:
            print(f"Fehler beim Abrufen der VCard-Links: {response.status_code}")
            logging.error(f"Fehler beim Abrufen der VCard-Links: {response.status_code}")
            return []
    except response.error as err:   
        print(f"Fehler bei vcard abruf {err}")
        logging.info(f"Fehler bei vcard abruf {err}")
            
def feldTypeInit():
#  Set für alle benutzten Feldtypen
    global alleFeldTypes 
    alleFeldTypes = set()
    return alleFeldTypes

def feldTypAdd(vcard):
# Durchlaufen aller vcards und Sammeln der Feldtypen
# Über alle Felder in der vcard iterieren
    for feldname, feldobjekte in vcard.contents.items():
        # Feldname zur Sammlung hinzufügen
        # alleFeldTypes.add(feldname)
        # Falls das Feld "TEL" ist, nach den Typen schauen
        if feldname == 'tel':
            for tel_feld in feldobjekte:
                # Überprüfe die Parameter (wie TYPE=HOME, WORK, etc.)
                if 'TYPE' in tel_feld.params:
                    alleFeldTypes.update(tel_feld.params['TYPE'])  # Typen hinzufügen

def feldTypeDump():
# Ergebnis als Liste ausgeben
    feldTypeList = list(alleFeldTypes)
    feldTypeListS = sorted(feldTypeList, reverse=True, key=str.lower)
    print(feldTypeListS)

def createPhotoFolder(folder_path):
# Erstelle den Ordner, wenn er noch nicht existiert
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)

# Ändere die Gruppe des Ordners auf 'www-data'
    shutil.chown(folder_path, user=None, group='www-data')

# Setze die Berechtigungen (rwx für den Besitzer, rwx für die Gruppe, rx für andere)
# Berechtigung 770: Besitzer und Gruppe haben volle Rechte, andere keine.
    os.chmod(folder_path, 0o770)

    print(f"Ordner {folder_path} erstellt und Berechtigungen gesetzt.")


def main():
    import argparse
    import configparser

    parser = argparse.ArgumentParser()
    parser.add_argument('ini_file')
    parser.add_argument("--no-update", help="Don't write to db ", action='store_true', default=False)
    args = parser.parse_args()

    config = configparser.RawConfigParser()
    config.read(args.ini_file)

    # Aktueller Dateiname des Python-Skripts ohne Pfad und Erweiterungyp
    skript_name = os.path.splitext(os.path.basename(__file__))[0]

    # Aktuelles Datum im Format "YYYY-MM-DD" holen
    datum = datetime.now().strftime('%Y-%m-%d')

    # Logdatei-Pfad mit dem Skript-Namen und Datum
    #log_datei = f'/var/log/{skript_name}_{datum}.txt'   
    log_datei = f'{skript_name}_{datum}.txt'   
    #logging.basicConfig(filename=log_datei, level=logging.ERROR)
    logging.basicConfig(filename=log_datei, level=logging.INFO)


    db = mysql.connector.connect(user=config['db']['user'], password=config['db']['password'],
        host=config['db']['host'], database=config['db']['database'])
    # Tabelle erstellen (falls nicht vorhanden)
    createTableIfNotExists(db.cursor())
    vcardLinks = getAllVcardLinks(config)
    feldTypeInit()
    photoFolder= config['photo']['photoFolder']
    createPhotoFolder(photoFolder)
    updateDB(config, db, vcardLinks,photoFolder)
    feldTypeDump()

if __name__ == "__main__":
    logger = logging.getLogger(__name__)
    main()

    
