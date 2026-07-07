import psycopg2
conn = psycopg2.connect(host='192.168.1.97',port=5432,dbname='fis_db',user='postgres',password='Moss9pep28$')
conn.autocommit = True
cur = conn.cursor()
cur.execute("""
    ALTER TABLE folder_triage ADD COLUMN IF NOT EXISTS confidence FLOAT DEFAULT NULL;
    ALTER TABLE folder_triage ADD COLUMN IF NOT EXISTS ai_raw TEXT DEFAULT NULL;
""")
print('columns added OK')
conn.close()
