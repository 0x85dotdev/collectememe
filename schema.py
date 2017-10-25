import mysql.connector
from mysql.connector import errorcode
from config import mysql_op

DB_NAME = 'collectememe'

TABLES = {}
TABLES['objects_grabbed'] = (
    "CREATE TABLE `objects_grabbed` ("
    "  `object_id` int(11) NOT NULL AUTO_INCREMENT,"
    "  `object_title` text DEFAULT NULL,"
    "  `object_reference` text NOT NULL,"
    "  `object_type` tinyint NOT NULL,"
    "  `object_status` tinyint DEFAULT 0,"
    "  `site_tag` varchar(140) NOT NULL,"
    "  `created_date` datetime NOT NULL,"
    "  PRIMARY KEY (`object_id`)"
    ") ENGINE=InnoDB")

TABLES['hash_storage'] = (
    "CREATE TABLE `hash_storage` ("
    "  `md5` char(32) NOT NULL,"
    "  PRIMARY KEY (`md5`)"
    ") ENGINE=InnoDB")

# Connect with the MySQL Server
cnx = mysql.connector.connect(user=mysql_op['user'], password=mysql_op['password'],
                              host=mysql_op['host'],
                              port=mysql_op['port'])
cursor = cnx.cursor()

def create_database(cursor):
    try:
        cursor.execute(
            "CREATE DATABASE {} DEFAULT CHARACTER SET 'utf8'".format(DB_NAME))
    except mysql.connector.Error as err:
        print("Failed creating database: {}".format(err))
        exit(1)

try:
    cnx.database = DB_NAME  
except mysql.connector.Error as err:
    if err.errno == errorcode.ER_BAD_DB_ERROR:
        create_database(cursor)
        cnx.database = DB_NAME
    else:
        print(err)
        exit(1)

for name, ddl in TABLES.items():
    try:
        print("Creating table {}: ".format(name), end='')
        cursor.execute(ddl)
    except mysql.connector.Error as err:
        if err.errno == errorcode.ER_TABLE_EXISTS_ERROR:
            print("already exists.")
        else:
            print(err.msg)
    else:
        print("OK")

cursor.close()
cnx.close()