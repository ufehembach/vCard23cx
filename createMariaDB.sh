#!/bin/bash

# Variablen
DB_HOST="h1ds"
DB_NAME="3cxAddressBook"
DB_USER="3cx"
DB_PASS=$(openssl rand -base64 12)  # Erzeugt ein zufälliges Passwort
ROOT_PASS="Pekase111!"  # Passwort des MariaDB root users
HOSTNAME=`hostname`

# Verbindung zu MariaDB und Ausführung der Befehle
mysql  -h "$DB_HOST" -u root -p"$ROOT_PASS" <<MYSQL_SCRIPT
CREATE DATABASE $DB_NAME;
CREATE USER '$DB_USER'@'localhost' IDENTIFIED BY '$DB_PASS';
CREATE USER '$DB_USER'@'$HOSTNAME' IDENTIFIED BY '$DB_PASS';
GRANT ALL PRIVILEGES ON $DB_NAME.* TO '$DB_USER'@'localhost';
GRANT ALL PRIVILEGES ON $DB_NAME.* TO '$DB_USER'@'$HOSTNAME';
FLUSH PRIVILEGES;
MYSQL_SCRIPT

# Passwort-Ausgabe
echo "Datenbank $DB_NAME und Benutzer $DB_USER mit Passwort $DB_PASS wurden erfolgreich erstellt."

