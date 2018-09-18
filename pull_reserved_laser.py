#! /usr/bin/env python
import MySQLdb,json, os, sys

if os.path.isfile('/home/e4ms/job_tracking/passList.txt'):
	with open('/home/e4ms/job_tracking/passList.txt','r') as passFile:
		try:
			passDict = json.load(passFile) # load json info into a list of dicts
		except: 
			print 'Problem with password file'
			sys.exit(1)
else:
	print 'password file does not exist'
	sys.exit(1)

reservedDict = {}

db = MySQLdb.connect(host="db.eng.ucsd.edu",user=passDict['db-user'],passwd=passDict['db-pass'],db="makerspace")
cur = db.cursor()
db.autocommit(True)
#clear out old reservation dates
query = "DELETE FROM laser_reserve WHERE reserve_date < CURDATE()"
cur.execute(query)
#grab all the remaining reservations 
query = "SELECT reserve_date,starttime,endtime,student_id FROM laser_reserve"
cur.execute(query)
results = cur.fetchall()
# Create an object to append to data array
for result in results:
	day = str(result[0])
	if day not in reservedDict:
		reservedDict[day]=[]
	reservedDict[day].append([])
	startTime = str(result[1])
	endTime = str(result[2])
	student = str(result[3])
	reservedDict[day][-1].extend((startTime,endTime,student))

#copy remote to table to local copy	
db = MySQLdb.connect(host='envision-local.dynamic.ucsd.edu',user=passDict['envision-user'],passwd=passDict['envision-pass'],db="envision_control")
cur = db.cursor()
db.autocommit(True)
#clean the local table
query = "DELETE FROM laser_reserve"
cur.execute(query)
for day in reservedDict:
	for time in reservedDict[day]:
		query = 'INSERT INTO laser_reserve (reserve_date,starttime,endtime,student_id) VALUE ("'+day+'","'+time[0]+'","'+time[1]+'","'+time[2]+'")'
		#print query
		cur.execute(query)
db.close()
