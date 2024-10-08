#!/usr/bin/env python3
#-*- coding: utf-8 -*-



import os
import csv
import time
import logging
import mysql.connector
from datetime import datetime
import configparser

# Funktion zur Ausführung und Ausgabe der SQL-Queries
def search_contact(cursor, query, search_value, file_name, search_type):
    print (query)
    # Ersetzen der Platzhalter in der Query
    query = query.replace("@Number", "%s").replace("@Email", "%s").replace("@SearchText", "%s")

    # Zähle die Anzahl der Platzhalter (%s) in der Query
    num_params = query.count("%s")

    # Query ausführen, die benötigte Anzahl von Parametern angeben
    cursor.execute(query, tuple([search_value] * num_params))

    # Ergebnisse holen
    results = cursor.fetchall()

    # Spaltennamen holen
    columns = [desc[0] for desc in cursor.description]

    # Ausgabe formatieren und anzeigen
    print(f"\nErgebnisse für '{search_type}' Abfrage ({search_value}):")
    if results:
        print(f"{' | '.join(columns)}")
        for row in results:
            print(" | ".join(str(x) for x in row))

        # CSV-Datei schreiben (mit Überschreiben)
        with open(file_name, mode='w', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(columns)  # Spaltenüberschriften schreiben
            writer.writerows(results)  # Ergebnisse schreiben
        print(f"Ergebnisse wurden in {file_name} gespeichert.")
    else:
        print(f"Keine Ergebnisse für '{search_value}' gefunden.")
        # Leere CSV schreiben
        with open(file_name, mode='w', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(columns)

# Hauptfunktion
def main():
    import argparse

    # Argumente parsen
    parser = argparse.ArgumentParser()
    parser.add_argument('ini_file')
    args = parser.parse_args()

    # Config-Datei lesen
    config = configparser.RawConfigParser()
    config.read(args.ini_file)

    # Logger einrichten
    skript_name = os.path.splitext(os.path.basename(__file__))[0]
    datum = datetime.now().strftime('%Y-%m-%d')
    log_datei = f'{skript_name}_{datum}.txt'
    logging.basicConfig(filename=log_datei, level=logging.INFO)

    # Datenbankverbindung herstellen
    db = mysql.connector.connect(user=config['db']['user'], password=config['db']['password'],
                                 host=config['db']['host'], database=config['db']['database'])
    try:
        cursor = db.cursor()

        # Endlosschleife zur wiederholten Abfrage
        while True:
            callerNumber = input("Bitte geben Sie die Eingabe ein (oder 'exit' zum Beenden oder 'all' für alle): ")

            # Beenden der Schleife bei 'exit'
            if callerNumber.lower() == 'exit':
                break

            # Queries aus der INI-Datei laden
            lookupByNumber = config['query']['lookupByNumber']
            lookupByEmail = config['query']['lookupByEmail']
            searchContacts = config['query']['searchContacts']

            # Alle Kontakte anzeigen
            if callerNumber.lower() in ['all', 'alles']:
                # Alle Kontakte anzeigen
                search_contact(cursor, 'SELECT * FROM contacts', '', 'all_contacts.csv', 'Alle Kontakte')
            else:
                # Query 1: Suche nach Nummer
                search_contact(cursor, lookupByNumber, callerNumber, 'lookup_by_number.csv', 'Nummer')

                # Query 2: Suche nach E-Mail
                search_contact(cursor, lookupByEmail, callerNumber, 'lookup_by_email.csv', 'E-Mail')

                # Query 3: Suche nach allgemeinem Kontakttext
                search_contact(cursor, searchContacts, callerNumber, 'search_contacts.csv', 'Kontaktsuche')

            time.sleep(1)

    except KeyboardInterrupt:
        print("\nProgramm mit Strg+C beendet.")

    finally:
        if cursor is not None:
            cursor.close()
        if db is not None and db.is_connected():
            db.close()

if __name__ == "__main__":
    main()

