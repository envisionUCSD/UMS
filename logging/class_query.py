#! /usr/bin/env python

import MySQLdb, csv, datetime
db = MySQLdb.connect(host='localhost',user='e4ms',passwd='thinkmakebreak',db='envision_control')
db.autocommit(True)

cur = db.cursor()
query="select * from classes"
cur.execute(query)
results=cur.fetchall()
avail = []
for result in results:
	if int(result[5])>0:
		avail.append(str(result[0]))
		print result

selected=[]
while True:
	selection = raw_input("Input id of interest or END to complete\n")
	if selection in avail:
		selected.append(selection)
		print "added"
		for result in results:
			if selection == str(result[0]):
				courseName = result[1]+'_'+result[3]
		break
	elif selection.upper() == 'END':
		break
	else:
		print ("Invalid Selection: ", selection)
cur = db.cursor()
query="select user,codes from ledger"
cur.execute(query)

results=cur.fetchall()
users=[]
for result in results:
	codes = None
	if len(result[1])>2:
		codes = result[1].split(',')
	elif int(result[1])!=0:
		codes = []
		codes.append(result[1])
	if codes is not None:
		users.append({})
		users[-1]['user']=result[0]
		users[-1]['codes']=codes

cur = db.cursor()
query="select id,code,stipend from classes"
cur.execute(query)

results=cur.fetchall()		
classes=[]
for result in results:
	classes.append({})
	classes[-1]['id']=result[0]
	classes[-1]['code']=result[1]
	classes[-1]['amount']=result[2]


for user in users:
	user['amount']=0
	for code in user['codes']:
		for course in classes:
			if int(code) == course['id']:
				if str(course['id']) in selected:
					user['codes'][user['codes'].index(code)]=course['code']
					user['amount']+=course['amount']
				else:
					user['codes'][user['codes'].index(code)]=0
departUsers = []
for user in users:
	if user['amount']!=0:
		departUsers.append({})
		departUsers[-1]['user']=user['user']
		for code in user['codes']:
			if code!=0:
				departUsers[-1]['code']=code
		departUsers[-1]['amount']=user['amount']
today=datetime.datetime.now().strftime('%Y%m%d')
fName = courseName+'.csv'
fields = ['user','code','amount']
try:
	with open (fName,'wb+') as csvFile:
		writer = csv.DictWriter(csvFile,fieldnames=fields)
		for user in departUsers:
			writer.writerow(user)
except Exception, e:
	print "CSV creation failed. DB not updated"
	print e
else:
	query = 'update classes set code=DEFAULT, stipend=DEFAULT,users=DEFAULT where id="'+selected[0]+'"'
	cur.execute(query)
db.close()
# else:
	# try:
		# for user in users:
			# query = 'update ledger set owed=owed-'+user['amount']+' where user="'+user['user']+'"'
			# #print query
			# cur.execute(query)
	# except:
		# print "DB ERROR"
	# else:
		# print "DB updated"

