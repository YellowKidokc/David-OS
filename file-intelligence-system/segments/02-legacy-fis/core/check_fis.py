import psycopg2
conn = psycopg2.connect(host='192.168.1.97',port=5432,dbname='fis_db',user='postgres',password='Moss9pep28$')
cur = conn.cursor()

cur.execute('SELECT COUNT(*) FROM files')
print('Total files:', cur.fetchone()[0])

cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='public' ORDER BY table_name")
print('Tables:', [r[0] for r in cur.fetchall()])

cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name='files' ORDER BY ordinal_position")
print('Files columns:', [r[0] for r in cur.fetchall()])

conn.close()
