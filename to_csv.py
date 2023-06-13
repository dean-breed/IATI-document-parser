import os
import io
import time
from datetime import datetime
import psycopg2
import requests
import json
from dotenv import load_dotenv
from PyPDF2 import PdfReader
import olefile
import docx
import pandas as pd

load_dotenv()
API_KEY = os.getenv('API_KEY')
PG_USER = os.getenv('PG_USER')
PG_PASS = os.getenv('PG_PASS')
PG_HOST = os.getenv('PG_HOST')
PG_PORT = os.getenv('PG_PORT')
PG_DB = os.getenv('PG_DB')

conn = psycopg2.connect(
    "dbname='{}' user='{}' host='{}' port='{}' password='{}'".format(PG_DB, PG_USER, PG_HOST, PG_PORT, PG_PASS)
)

sql_query = pd.read_sql_query('''
                              select * from docs
                              '''
                              ,conn)

df = pd.DataFrame(sql_query)
df.to_csv (r'C:/git/IATI-document-parser/test.csv', index = False)
