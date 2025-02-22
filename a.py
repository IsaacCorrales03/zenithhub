import mysql.connector
from mysql.connector import Error
import os
from dotenv import load_dotenv
load_dotenv()
conn = mysql.connector.connect(
    user=os.getenv('DB_USER'),
    password=os.getenv('DB_PASSWORD'),
    host=os.getenv('DB_HOST'),
    port=os.getenv('DB_PORT'),
    database=os.getenv('DB_NAME')
)
cur = conn.cursor()
cur.execute('DROP')