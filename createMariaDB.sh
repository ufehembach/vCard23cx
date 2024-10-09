#!/bin/bash

# Variablen
DB_HOST="localhost"
DB_NAME="3cxAddressBook"
DB_USER="3cx"
DB_PASS=$(openssl rand -base64 12)  # Erzeugt ein zufälliges Passwort
HOSTNAME=`hostname`
HOST_3CX="192.168.200.198"

# Verbindung zu MariaDB und Ausführung der Befehle
mysql  -h "$DB_HOST" -u root -p <<MYSQL_SCRIPT
SELECT user, host FROM mysql.user;
Show databases;

CREATE DATABASE $DB_NAME;
CREATE USER '$DB_USER'@'localhost' IDENTIFIED BY '$DB_PASS';
CREATE USER '$DB_USER'@'$HOSTNAME' IDENTIFIED BY '$DB_PASS';
CREATE USER '$DB_USER'@'$HOST_3CX' IDENTIFIED BY '$DB_PASS';
GRANT ALL PRIVILEGES ON $DB_NAME.* TO '$DB_USER'@'localhost';
GRANT ALL PRIVILEGES ON $DB_NAME.* TO '$DB_USER'@'$HOSTNAME';
GRANT ALL PRIVILEGES ON $DB_NAME.* TO '$DB_USER'@'$HOST_3CX';
FLUSH PRIVILEGES;

SELECT user, host FROM mysql.user;
Show databases;

MYSQL_SCRIPT
if [ $? -ne 0 ]; then
    echo "MySQL query failed with error code: $?"
# Passwort-Ausgabe
else
	echo "Datenbank $DB_NAME und Benutzer $DB_USER mit Passwort $DB_PASS wurde auf $HOSTNAME  erfolgreich erstellt."
	cat > vCard23cx.ini <<INI_FILE
############################
#`date --iso-8601=seconds` 

[carddav]
url = https://hosted.server.sample/SOGo/dav/user@email.liam/Contacts/whatever
user = user@email.liam
pass = supersecretcarddavPW


[db] 
user = $DB_USER
password = $DB_PASS
host = $DB_HOST 
# $HOSTNAME
database = $DB_NAME

#this are the querys you need to put in the crm settings of 3cx, each part as given
[query]
#Lookup By Number SQL Statement:
lookupByNumber = SELECT contactid, firstname, lastname, companyname, email, phonemobile, phonemobile2, phonehome,        phonehome2, phonebusiness, phonebusiness2, phoneother, faxbusiness, faxhome, pager, photourl FROM contacts WHERE phonemobile LIKE CONCAT('%', @Number, '%')     OR phonemobile2 LIKE CONCAT('%', @Number, '%')     OR phonehome LIKE CONCAT('%', @Number, '%')     OR phonehome2 LIKE CONCAT('%', @Number, '%')     OR phonebusiness LIKE CONCAT('%', @Number, '%')     OR phonebusiness2 LIKE CONCAT('%', @Number, '%')     OR phoneother LIKE CONCAT('%', @Number, '%');

#Lookup By Email SQL Statement:
lookupByEmail = SELECT contactid, firstname, lastname, email, phonebusiness, phonemobile, faxbusiness FROM contacts WHERE email = @Email

#Search Contacts SQL Statement:
searchContacts = SELECT contactid, firstname, lastname, companyname, email, phonemobile, phonemobile2, phonehome, phonehome2, phonebusiness, phonebusiness2, phoneother, faxbusiness, faxhome, pager FROM contacts WHERE firstname LIKE CONCAT('%',@SearchText,'%') or lastname LIKE CONCAT('%',@SearchText,'%') or companyname LIKE CONCAT('%',@SearchText,'%') or email LIKE CONCAT('%',@SearchText,'%') or phonemobile LIKE CONCAT('%',@SearchText,'%') or phonemobile2 LIKE CONCAT('%',@SearchText,'%') or phonehome LIKE CONCAT('%',@SearchText,'%') or phonehome2 LIKE CONCAT('%',@SearchText,'%') or phonebusiness LIKE CONCAT('%',@SearchText,'%') or phonebusiness2 LIKE CONCAT('%',@SearchText,'%') or phoneother LIKE CONCAT('%',@SearchText,'%') or faxbusiness LIKE CONCAT('%',@SearchText,'%') or faxhome LIKE CONCAT('%',@SearchText,'%') or pager LIKE CONCAT('%',@SearchText,'%');

INI_FILE

fi
