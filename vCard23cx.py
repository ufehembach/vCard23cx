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
import mysql.connector
import base64
import os
import shutil
import hashlib
from PIL import Image, ImageDraw, ImageFont
#import vcard


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

def extractPhotoFromVcard(vcard, photoFolder, photoUrlIni, contactid, first_name, last_name):
    # Überprüfen, ob die vCard ein Foto enthält
    myRet = ''
    if hasattr(vcard, 'photo'):
        photo = vcard.photo

        # Überprüfen, ob das Foto die erwarteten Daten enthält
        if hasattr(photo, 'value'):
            # Holen Sie sich die ENCODING-Parameter
            encodings = photo.params.get('ENCODING', [])

            # Überprüfen, ob eine der Encodings auf Base64 hinweist
            if any(e.lower() in ['base64', 'b'] for e in encodings):
                # Extrahiere die Base64-kodierten Fotodaten
                photo_data_base64 = photo.value

                # Wenn die Daten bereits im Byte-Format vorliegen, überspringe die Decodierung
                if isinstance(photo_data_base64, str):
                    # Bereinige die Base64-Daten von Zeilenumbrüchen
                    photo_data_base64 = photo_data_base64.replace('\n', '').replace('\r', '')

                    # Decodiere die Base64-Daten
                    try:
                        photo_data = base64.b64decode(photo_data_base64)
                    except (TypeError, ValueError) as e:
                        print(f"Fehler beim Decodieren der Base64-Daten: {e}")
                        print(vcard.serialize())  # VCard-Daten im VCard-Format ausgeben
                        return
                else:
                    # Die Daten sind bereits als Bytes vorhanden
                    photo_data = photo_data_base64

                # Sicherstellen, dass das Zielverzeichnis existiert
                os.makedirs(os.path.dirname(photoFolder), exist_ok=True)

                # Schreibe die dekodierten Daten in die Datei
                photo_path = os.path.join(photoFolder, f"{contactid}.jpg")
                with open(photo_path, 'wb') as photoFile:
                    photoFile.write(photo_data)
                myRet = f"{photoUrlIni}/{contactid}.jpg"
                #print(f"1Foto wurde erfolgreich extrahiert und in {photo_path} gespeichert.")
                #print(f"2{photoUrlIni} {contactid}.jpg")
                #print(f"3URL: {myRet}")
            else:
                print("Das Foto ist nicht Base64-kodiert oder verwendet eine unbekannte Kodierung.")
                print(vcard.serialize())  # VCard-Daten im VCard-Format ausgeben
        else:
            print("Die vCard enthält kein gültiges Foto.")
    else:
        print("Die vCard enthält kein Foto.")
        # Wenn kein Foto vorhanden ist, generiere ein Platzhalterbild
        print("Generiere ein Platzhalterbild für den Kontakt.")
        generate_placeholder_image(photoFolder, contactid, first_name, last_name)
        myRet = f"{photoUrlIni}/{contactid}.jpg"
    return myRet
    
import os
import hashlib
import random
from PIL import Image, ImageDraw, ImageFont
import matplotlib.font_manager as fm  # Um alle installierten Schriftarten zu laden

import os
import hashlib
import random
from PIL import Image, ImageDraw, ImageFont
import matplotlib.font_manager as fm  # Um alle installierten Schriftarten zu laden

ASCII_CHARS = "@%#*+=-:. "  # Zeichen für verschiedene Helligkeitsstufen

def resize_image(image, new_width=30):
    width, height = image.size
    aspect_ratio = height / width
    new_height = int(aspect_ratio * new_width)
    resized_image = image.resize((new_width, new_height))
    return resized_image

def grayscale_image(image):
    return image.convert("L")

def map_pixels_to_ascii(image, range_width=25):
    pixels = list(image.getdata())
    ascii_str = ""
    for pixel_value in pixels:
        ascii_str += ASCII_CHARS[pixel_value // range_width]
    return ascii_str

def convert_image_to_ascii(image, new_width=30):
    image = resize_image(image, new_width)
    image = grayscale_image(image)
    
    ascii_str = map_pixels_to_ascii(image)
    img_width = image.width
    
    ascii_image = ""
    for i in range(0, len(ascii_str), img_width):
        ascii_image += ascii_str[i:i+img_width] + "\n"
    
    return ascii_image

def generate_placeholder_image(photoFolder, contactid, first_name, last_name, image_size=200):
    """
    Generiert ein Platzhalterbild mit den Initialen des Kontakts und gibt es als ASCII aus.

    :param photoFolder: Der Ordner, in dem die Fotos gespeichert werden sollen
    :param contactid: Eindeutige ID für den Kontakt
    :param first_name: Vorname des Kontakts
    :param last_name: Nachname des Kontakts
    :param image_size: Größe des generierten Bildes (Pixel)
    """
    initials = ''.join([name[0].upper() for name in [first_name, last_name] if name]).strip()
    if not initials:
        initials = "?"  # Fallback, falls keine Namen vorhanden sind

    # Erstelle einen Hash aus der contactid, um eine konsistente Farbe zu erhalten
    hash_object = hashlib.md5(contactid.encode())
    hash_digest = hash_object.hexdigest()

    # Verwende Teile des Hashes, um RGB-Farben zu generieren
    r = int(hash_digest[0:2], 16)
    g = int(hash_digest[2:4], 16)
    b = int(hash_digest[4:6], 16)

    # Helle Farbe
    r = (r + 128) % 256
    g = (g + 128) % 256
    b = (b + 128) % 256

    # Erstelle das Bild
    image = Image.new('RGB', (image_size, image_size), color=(r, g, b))
    draw = ImageDraw.Draw(image)

    # Liste aller installierten Schriftarten abrufen und zufällig auswählen
    available_fonts = fm.findSystemFonts(fontpaths=None, fontext='ttf')
    random_font_path = random.choice(available_fonts)

    try:
        # Zufällige Schriftart laden
        font = ImageFont.truetype(random_font_path, int(image_size / 3))
    except IOError:
        # Fallback auf eine Standard-Schriftart
        font = ImageFont.load_default()

    # Berechne die Position, um den Text zu zentrieren
    text_width, text_height = draw.textsize(initials, font=font)
    position = ((image_size - text_width) / 2, (image_size - text_height) / 2)

    # Wähle eine kontrastreiche Farbe für den Text (weiß oder schwarz)
    luminance = (0.299 * r + 0.587 * g + 0.114 * b)
    text_color = (255, 255, 255) if luminance < 128 else (0, 0, 0)

    # Zeichne die Initialen auf das Bild
    draw.text(position, initials, fill=text_color, font=font)

    # Speichere das Bild
    os.makedirs(photoFolder, exist_ok=True)
    image_path = os.path.join(photoFolder, f"{contactid}.jpg")
    image.save(image_path, format='JPEG')
    print(f"Platzhalterbild wurde erfolgreich in {image_path} gespeichert.")

    # ASCII-Image Ausgabe im Log
    ascii_image = convert_image_to_ascii(image)
    print("ASCII-Bild:")
    print(ascii_image)



def createVcardHtml(vcard, photoUrl, vCardFolder, contactid):
    # Prepare details from vCard
    fields = {
        "Name": vcard.fn.value if hasattr(vcard, 'fn') else "Unknown",
        "Organization": vcard.org.value[0] if hasattr(vcard, 'org') else "No organization",
        "Title": vcard.title.value if hasattr(vcard, 'title') else "No title",
        "Emails": [],
        "Phones": [],
        "Addresses": []
    }

    # Extract phone numbers dynamically
    if hasattr(vcard, 'tel_list'):
        for tel in vcard.tel_list:
            tel_type = ', '.join(tel.params.get('TYPE', [])).title() if 'TYPE' in tel.params else "Other"
            fields["Phones"].append((tel_type, tel.value))

    # Extract email addresses dynamically
    if hasattr(vcard, 'email_list'):
        for email in vcard.email_list:
            email_type = ', '.join(email.params.get('TYPE', [])).title() if 'TYPE' in email.params else "Other"
            fields["Emails"].append((email_type, email.value))

    # Initialize address as "Unknown"
    address = "Unknown"


    # HTML structure
    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{fields['Name']} - vCard</title>
        <style>
            body {{
                font-family: Arial, sans-serif;
                margin: 20px;
                padding: 0;
                background-color: #f9f9f9;
                color: #333;
            }}
            .container {{
                display: flex;
                flex-direction: row;
                align-items: flex-start;
            }}
            .photo {{
                margin-right: 20px;
            }}
            .details {{
                display: grid;
                grid-template-columns: auto auto;
                gap: 10px 20px;
            }}
            .label {{
                color: grey;
                font-weight: normal;
            }}
            .value {{
                font-weight: bold;
                color: black;
            }}
            img {{
                max-width: 150px;
                border-radius: 8px;
            }}
        </style>
    </head>
    <body>
        <h1>{fields['Name']}</h1>
        <div class="container">
            <div class="photo">
                <img src="{photoUrl}" alt="{fields['Name']}'s Photo">
            </div>
            <div class="details">
    """

    # Add Organization and Title
    html_content += f"""
        <div class="label">Organization:</div>
        <div class="value">{fields['Organization']}</div>
        <div class="label">Title:</div>
        <div class="value">{fields['Title']}</div>
    """

    # Add Phones
    for phone_type, phone_number in fields["Phones"]:
        html_content += f"""
        <div class="label">Phone ({phone_type}):</div>
        <div class="value">{phone_number}</div>
        """

    # Add Emails
    for email_type, email_address in fields["Emails"]:
        html_content += f"""
        <div class="label">Email ({email_type}):</div>
        <div class="value">{email_address}</div>
        """

    html_content += f"""
        <div>
             <div class="label">Address:</div>
            <div class="content">{address}</div>
            <!-- Add other details as needed -->
        </div>
        """

    # Close HTML tags
    html_content += """
            </div>
        </div>
    </body>
    </html>
    """

    # Write HTML to the output file
    os.makedirs(os.path.dirname(vCardFolder), exist_ok=True)
    with open(vCardFolder + '/' + contactid + '.html', 'w', encoding='utf-8') as f:
        f.write(html_content)

    #print(f"HTML page created at: {vCardFolder}")

# Funktion zur Verarbeitung einer vcard
def verarbeite_vcard(vcard,db,config):
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

        photoUrlIni= config['html']['photoUrl']
        photoFolder = config['html']['photofolder']
        photourl = extractPhotoFromVcard(vcard, photoFolder, photoUrlIni, contactid, firstname, lastname)
    
        vCardFolder = config['html']['vCardFolder']
        vCardUrl = createVcardHtml(vcard, photourl, vCardFolder, contactid)

        lastupdate = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        info = config['info']['description']


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
            lastupdate=VALUES(lastupdate),
            info=VALUES(info)

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
        verarbeite_vcard(vcard,db,config)
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
    info VARCHAR(255),
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
    #print(auth)
    #print(url)
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
import os
import time
from datetime import datetime, timedelta

def cleanup_files(program_directory, photo_directory):
    # Aktuelles Datum und Zeit
    now = time.time()
    
    # Alter der Dateien in Sekunden berechnen (5 Tage und 1 Tag in Sekunden)
    five_days_ago = now - (5 * 86400)  # 5 Tage * 86400 Sekunden pro Tag
    one_day_ago = now - (1 * 86400)    # 1 Tag * 86400 Sekunden pro Tag
    
    # Aufräumen im Programmverzeichnis (.txt und .log Dateien älter als 5 Tage)
    for file_name in os.listdir(program_directory):
        file_path = os.path.join(program_directory, file_name)
        # Prüfen, ob es sich um eine Datei handelt und ob sie älter als 5 Tage ist
        if os.path.isfile(file_path) and file_name.endswith(('.txt', '.log')):
            file_mtime = os.path.getmtime(file_path)
            if file_mtime < five_days_ago:
                os.remove(file_path)
                print(f"{file_name} (älter als 5 Tage) wurde gelöscht.")

    # Aufräumen im Fotoverzeichnis (Fotos älter als 1 Tag)
    for file_name in os.listdir(photo_directory):
        file_path = os.path.join(photo_directory, file_name)
        # Prüfen, ob es sich um eine Datei handelt und ob sie älter als 1 Tag ist
        if os.path.isfile(file_path) and file_name.endswith(('.jpg', '.jpeg', '.png')):
            file_mtime = os.path.getmtime(file_path)
            if file_mtime < one_day_ago:
                os.remove(file_path)
                print(f"{file_name} (älter als 1 Tag) wurde gelöscht.")


def main():
    import argparse
    import configparser

    parser = argparse.ArgumentParser()
    parser.add_argument('ini_file')
#    parser.add_argument("--no-update", help="Don't write to db ", action='store_true', default=False)
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
    photoFolder= config['html']['photoFolder']
    createPhotoFolder(photoFolder)
    vCardFolder = config['html']['vCardFolder']
    createPhotoFolder(vCardFolder)
    updateDB(config, db, vcardLinks,config)
    feldTypeDump()
    # Aufräumfunktion aufrufen
    program_directory = os.path.dirname(os.path.abspath(__file__))
    cleanup_files(program_directory, photoFolder)
    cleanup_files(program_directory, vCardFolder)

if __name__ == "__main__":
    logger = logging.getLogger(__name__)
    main()

    
