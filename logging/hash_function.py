#!/usr/bin/env python

import MySQLdb, hashlib

classList = []

db = MySQLdb.connect(host="localhost",user='e4ms',passwd='thinkmakebreak',db="envision_control")
db.autocommit(True)
cur = db.cursor()

query = "SELECT * FROM classes"
cur.execute(query)
result = cur.fetchall()
#print result
for cls in result:
	classList.append([])
	classList[-1].extend((str(cls[1]),str(cls[2]),str(cls[3])))

#print classList
for cls in classList:
	codeString = cls[0]+cls[1]+'-'+'SQ18'
	code = str(int(hashlib.md5(codeString.upper()).hexdigest(),16) % (10 ** 6)).zfill(6)
	cls[2]=code
	query = 'UPDATE classes SET code="'+code+'" WHERE department="'+cls[0]+'" AND number="'+cls[1]+'"'
	cur.execute(query)



db.close()

#str(int(hashlib.md5(cls.upper()).hexdigest(),16) % (10 ** 6)).zfill(6)
