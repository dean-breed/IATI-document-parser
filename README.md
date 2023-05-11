# IATI-document-parser
A PDF scraper for project documents linked in IATI

## Setup

```
pip3 install virtualenv
python3 -m virtualenv venv
source venv/bin/activate
pip3 install -r requirements.txt

cp .env-example .env # Fill out variables

psql < setup.sql
```

## Run

```
python3 run.py
```

## Analyze

```
select content_type, count(*) from docs group by content_type order by count desc;
                               content_type                                | count 
---------------------------------------------------------------------------+-------
 text/html; charset=utf-8                                                  |   844
 application/pdf                                                           |   588
 error/unknown                                                             |   512
 text/html;charset=UTF-8                                                   |   205
 text/html; charset=UTF-8                                                  |   166
 text/html;charset=utf-8                                                   |    39
 application/vnd.openxmlformats-officedocument.wordprocessingml.document   |    27
 application/x-zip-compressed                                              |    22
 application/vnd.openxmlformats-officedocument.spreadsheetml.sheet         |     8
 text/html                                                                 |     7
 image/jpeg                                                                |     7
 application/msword                                                        |     5
 application/vnd.ms-excel                                                  |     4
 image/png                                                                 |     4
 application/octet-stream, text/html                                       |     2
 pdf/corrupt                                                               |     2
 application/pdf; charset=utf-8                                            |     1
 docx/corrupt                                                              |     1
 application/vnd.ms-powerpoint                                             |     1
 application/vnd.oasis.opendocument.text                                   |     1
 application/vnd.openxmlformats-officedocument.presentationml.presentation |     1
(21 rows)

select full_text, count(*) from docs where content_type = 'error/unknown' group by full_text order by count desc;
          full_text           | count 
------------------------------+-------
 Error fetching document: 403 |   446
 Error fetching document: 404 |    66
(2 rows)

select count(*) from docs where full_text ilike '%famine%';
 count 
-------
    69
(1 row)

select pg_size_pretty( pg_total_relation_size('docs') );
 pg_size_pretty 
----------------
 54 MB
(1 row)
```

## Benchmark (first 1,000 activities, 2,447 documents)
```
time python3 run.py 

real	9m16.889s
user	10m46.939s
sys	0m6.647s
```