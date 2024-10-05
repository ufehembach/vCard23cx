# vCard23cx
extract vCards from an CardDav account and import into a mariadb, so you can reference it from 3cx crm integration for mariadb

## THIS IS A VERY EARLY VERSION
logging and error handling not implemented properly
working on vCard Images

Steps to setup:

* update your designated linux system to current verions/update
* install python
* install mariadb-server
* install apache2

* run createMariaDB.sh  this creates a database and setups a user (root password for mariaDB needed)
* this will create a vCard23cx.ini file, in this ini file the vCard server details have to be updated
* run vCard23cx.py <inifilename>  watch output, please ensure vCard data is ok and mysql is working

* if this is ok
** tun test3cxQuery.py <inifilename> to check if you can access the database in a proper way
** if ok setup the crm mysql part in 3cx
  *** use the database part rom <inifilenam> (on v20 please use the 2nd mysql and give 3306 for the port)
  *** add queries from "thisAreTheQueries.txt" to 
    
