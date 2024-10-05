#!/usr/bin/env python3
#-*- coding: utf-8 -*-

import mysql.connector
import logging
import argparse
import configparser
import logging
import os
import time
from datetime import datetime


# Funktion zur Ausführung des SQL-Queries
def search_contact_by_number(cursor, callerNumber):
    if callerNumber != "all":
        query = """
SELECT contactid, firstname, lastname, companyname, email, phonemobile, phonemobile2, phonehome,
       phonehome2, phonebusiness, phonebusiness2, phoneother, faxbusiness, faxhome, pager, photourl
FROM contacts
WHERE phonemobile LIKE CONCAT('%', %s, '%')
    OR phonemobile2 LIKE CONCAT('%', %s, '%')
    OR phonehome LIKE CONCAT('%', %s, '%')
    OR phonehome2 LIKE CONCAT('%', %s, '%')
    OR phonebusiness LIKE CONCAT('%', %s, '%')
    OR phonebusiness2 LIKE CONCAT('%', %s, '%')
    OR phoneother LIKE CONCAT('%', %s, '%');
"""
    # Ausführen des Queries mit der CallerNumber
        cursor.execute(query, (callerNumber, callerNumber, callerNumber, callerNumber, callerNumber, callerNumber, callerNumber))
    else:
        query = """
    select * from contacts;
"""
        cursor.execute(query, ())

    # Ergebnisse ausgeben
    results = cursor.fetchall()
    if results:
        for row in results:
            print("Gefundener Kontakt:", row)
    else:
        print("Kein Kontakt gefunden für die Nummer:", callerNumber)


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
    print ( config)

    db = mysql.connector.connect(user=config['db']['user'], password=config['db']['password'], host=config['db']['host'], database=config['db']['database'])
    try:
        cursor = db.cursor()

        # Endlosschleife zur wiederholten Abfrage
        while True:
            # Telefonnummer von der Tastatur einlesen
            callerNumber = input("Bitte geben Sie die CallerNumber ein (oder 'exit' zum Beenden oder 'all' fuer alle): ")

            # Beenden der Schleife bei 'exit'
            if callerNumber.lower() == 'exit':
                break

            # SQL-Abfrage ausführen
            search_contact_by_number(cursor, callerNumber)

            # Kurze Pause zwischen den Abfragen (optional)
            time.sleep(1)

    except KeyboardInterrupt:
        print("\nProgramm mit Strg+C beendet.")

    finally:
         # Datenbankverbindung schließen, falls sie erfolgreich hergestellt wurde
        if cursor is not None:
            cursor.close()
        if db is not None and db.is_connected():
            db.close()

if __name__ == "__main__":
    logger = logging.getLogger(__name__)
    main()

    
