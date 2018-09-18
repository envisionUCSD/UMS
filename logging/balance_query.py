#! /usr/bin/env python

import MySQLdb, csv, datetime,sys
username = 'reports'
password = 'envisionLogs'
host = "envision-local.dynamic.ucsd.edu"
port = 3306
database = "envision_control"
parent = parent
try:
	db = MySQLdb.connect(host=host,port=port,user=username,passwd=password,db=database)
except Exception as e:
#if you can't connect, end the program
	print e
	print "unable to connect to DB...Shutting down."
	sys.exit(1)
else:
	print "Successful Connection to DB"
db.autocommit(True) #changes made are committed on execution
cur = db.cursor() #set the cursor to the beginning of the DB

users=[]
query="select user,owed,timestamp from ledger"
cur.execute(query)

results=cur.fetchall()
users=[]
for result in results:
	if result[1]>0:
		users.append({})
		users[-1]['user']=result[0]
		users[-1]['amount']=str(result[1])
		users[-1]['date']=str(result[2])
today=datetime.datetime.now().strftime('%Y%m%d')
fName = 'envision_ledger_'+today+'.csv'
fields = ['user','amount','date']
try:
	with open (fName,'wb+') as csvFile:
		writer = csv.DictWriter(csvFile,fieldnames=fields)
		for user in users:
			writer.writerow(user)
except:
	print "CSV creation failed. DB not updated"
	sys.exit(2)
else:
	for user in users:
		print user
	while True:
		selection = raw_input("User Extraction Complete. Reset owed amount to $0.00?")
		if selection=="YES":
			try:
				for user in users:
					query = 'update ledger set owed=owed-'+user['amount']+' where user="'+user['user']+'"'
					#print query
					cur.execute(query)
			except:
				print "DB ERROR"
				sys.exit(3)
			else:
				print "DB updated"
				break
		elif selection.upper() == 'NO':
			break
		else:
			print ("Invalid Selection: ", selection)
	
	


