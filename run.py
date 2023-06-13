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
import multiprocessing
from bs4 import BeautifulSoup
multiprocessing.set_start_method('spawn', True)

load_dotenv()
API_KEY = os.getenv('API_KEY')
PG_USER = os.getenv('PG_USER')
PG_PASS = os.getenv('PG_PASS')
PG_HOST = os.getenv('PG_HOST')
PG_PORT = os.getenv('PG_PORT')
PG_DB = os.getenv('PG_DB')


def create_connection():
    conn = psycopg2.connect(
        "dbname='{}' user='{}' host='{}' port='{}' password='{}'".format(PG_DB, PG_USER, PG_HOST, PG_PORT, PG_PASS)
    )
    conn.autocommit = True
    conn.set_isolation_level(0)
    return conn


def fetch_activity_documents():
    conn = create_connection()
    cur = conn.cursor()
    sql = '''
        INSERT INTO docs(iati_identifier, created, source)
        VALUES(%s, %s, %s);
    '''
    paginate = True
    rows = 100
    start = 0
    # while paginate:
    url = (
        'https://api.iatistandard.org/datastore/activity/select'
        '?q=(recipient_country_code:SO OR transaction_recipient_country_code:SO)'
        'AND (document_link_url: [* TO *])'
        '&wt=json&fl=iati_identifier,document_link_url&rows={}&start={}'
    ).format(rows, start)
    api_json_str = requests.get(url, headers={'Ocp-Apim-Subscription-Key': API_KEY}).content
    api_content = json.loads(api_json_str)
    activities = api_content['response']['docs']
    for activity in activities:
        if type(activity['document_link_url']) is str:
            try:
                cur.execute(sql, (activity['iati_identifier'], datetime.now(), activity['document_link_url'],))
            except psycopg2.errors.UniqueViolation:
                pass
        else:
            for document in activity['document_link_url']:
                try:
                    cur.execute(sql, (activity['iati_identifier'], datetime.now(), document,))
                except psycopg2.errors.UniqueViolation:
                    pass
    start += rows
    # if len(activities) < rows:
    #     paginate = False
    cur.close()
    conn.close()


def split(lst, n):
    k, m = divmod(len(lst), n)
    return (lst[i * k + min(i, m):(i + 1) * k + min(i + 1, m)] for i in range(n))


def queue_extraction(processes):
    conn = create_connection()
    cur = conn.cursor()
    read_sql = '''
        SELECT id, source FROM docs
        WHERE full_text IS NULL;
    '''
    cur.execute(read_sql)
    rows = cur.fetchall()
    cur.close()
    conn.close()

    row_batches = list(
        split(rows, processes)
    )

    processes = []

    for batch in row_batches:
        if len(batch) == 0:
            continue
        process = multiprocessing.Process(
            target=fetch_documents, args=(batch, )
        )
        process.start()
        processes.append(process)

    running = True
    while running:
        time.sleep(2)
        running = False
        for process in processes:
            process.join(timeout=0)
            if process.is_alive():
                running = True


def fetch_documents(rows):
    conn = create_connection()
    write_sql = '''
        UPDATE docs
        SET content_type = %s,
        full_text = %s
        WHERE id = %s
    '''
    cur = conn.cursor()
    for id, url in rows:
        head = requests.get(url, allow_redirects=True)
        if head.ok:
            content_type = head.headers['Content-Type']
            if content_type.startswith('text'):
                soup = BeautifulSoup(head.content, features="html.parser")
                for script in soup(["script", "style"]):
                    script.extract()
                text = soup.get_text()
                cur.execute(write_sql, (content_type, text, id, ))
            elif content_type.startswith('application/pdf'):
                try:
                    text_content = []
                    bytes_content = requests.get(head.url).content
                    pdf_content = io.BytesIO(bytes_content)
                    pdf_reader = PdfReader(pdf_content)
                    for page in pdf_reader.pages:
                        text_content.append(page.extract_text())
                    cur.execute(write_sql, (content_type, '\n'.join(text_content).replace('\x00',''), id, ))
                except Exception as e:
                    content = str(e)
                    content_type = "pdf/corrupt"
                    cur.execute(write_sql, (content_type, content, id, ))
            elif content_type == 'application/msword':
                try:
                    text_content = ""
                    bytes_content = requests.get(head.url).content
                    doc_content = io.BytesIO(bytes_content)
                    with olefile.OleFileIO(doc_content) as ole:
                        stream = ole.openstream('WordDocument')
                        text_content = stream.read().decode('utf-8', errors='ignore')
                    cur.execute(write_sql, (content_type, text_content.replace('\x00',''), id, ))
                except Exception as e:
                    content = str(e)
                    content_type = "doc/corrupt"
                    cur.execute(write_sql, (content_type, content, id, ))
            elif content_type == 'application/vnd.openxmlformats-officedocument.wordprocessingml.document':
                try:
                    text_content = []
                    bytes_content = requests.get(head.url).content
                    doc_content = io.BytesIO(bytes_content)
                    doc = docx.Document(doc_content)
                    for para in doc.paragraphs:
                        text_content.append(para.text)
                    cur.execute(write_sql, (content_type, '\n'.join(text_content).replace('\x00',''), id, ))
                except Exception as e:
                    content = str(e)
                    content_type = "docx/corrupt"
                    cur.execute(write_sql, (content_type, content, id, ))
            else:
                content = 'Unsupported format'
                cur.execute(write_sql, (content_type, content, id, ))
        else:
            content = 'Error fetching document: {}'.format(head.status_code)
            content_type = 'error/unknown'
            cur.execute(write_sql, (content_type, content, id, ))
    cur.close()
    conn.close()


if __name__ == '__main__':
    fetch_activity_documents()
    queue_extraction(16)
