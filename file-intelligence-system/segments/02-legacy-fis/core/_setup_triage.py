import psycopg2
conn = psycopg2.connect(host='192.168.1.97', port=5432, dbname='fis_db', user='postgres', password='Moss9pep28$')
cur = conn.cursor()
sql = open(r'D:\GitHub\file-intelligence-system\sql\08_folder_triage.sql').read()
cur.execute(sql)
conn.commit()
print('Table created OK')
conn.close()
