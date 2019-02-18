#!/usr/bin/env python
"""
EnVision User Management System (EUMS)
The EnVision Arts and Engineering Maker Studio
UC San Diego
Jacobs School of Engineering
Jesse DeWald
May 2016
All Rights Reserved
"""

version = "v227"
"""
-- 223 added laptop kiosk functionalities
--123 added printer kiosk functionalities
- 21 added CHECKID functionality to replace database copying to local machines
- 20 stopped using wiringPi and switched to echo bash commands for relay switching
- 19 Added machine status column to database
- 18 ADD_TIME was charging supervisor instead of user. Updated userID = packet[2] under the else statement
- 17 fixed issue with db connection closing on an EVT_END...added a seperate connection in the thread, probably not the prettiest solution
- 16 changed database name to envision_control, customer --> ledger
- 15 changed to mysql database.
- 14 added cashier functionality
# 12 added support for relayPi-3 & taz machines
# 11 fixed bug where relay was shut off but thread wasn't ended
# 10 added support for supervisor ending timer
#	cleaned up some superfluous code, added some comments

Todo:
cleanup classes...one day
check file on laptop machine....added some functionality for checking both MS db and envision DB...and cleaned up the classes

"""
#import calls
import SocketServer #ability to open a socket and listen
import csv, json, MySQLdb #use saved data 
import os, sys #standard OS functions
import threading, signal #thread spawning and killing
import datetime, time #time functions and handling
import paramiko #sftp / ssh capabilities
import logging #logs to a file for
from logging.handlers import TimedRotatingFileHandler
#separate (protected) file with a list of usernames and passwords for various hosts
passFile = '/home/e4ms/job_tracking/passList.txt'

#global varialbes for the logic level of the relays (changes depends on relay brand)
relayOn = "1"
relayOff = "0"
logger = logging.getLogger("EnVision Logger")
handler = logging.handlers.TimedRotatingFileHandler("/var/log/envision/socketServer.log",when='midnight',interval=1,backupCount=7)
formatter=logging.Formatter("%(levelname)s:%(asctime)s:%(threadName)s:%(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.DEBUG)
#logger.basicConfig(format="%(levelname)s:%(asctime)s:%(threadName)s:%(message)s", filename="/var/log/envision/socketServer.log", level=logging.INFO)


logger.info("SocketServer started")
logger.info("Version %s", version)

class MyTCPHandler(SocketServer.BaseRequestHandler):
	"""
	The RequestHandler class for our server.
	It is instantiated once per connection to the server, and must
	override the handle() method to implement communication to the
	client.
	"""
	def handle(self):
		# self.request is the TCP socket connected to the client
		now = datetime.datetime.now()
		self.incoming = (self.request.recv(1024)).split() #receive into a buffer
		recvFrom = "received packet from: {}".format(self.client_address[0])
		logger.info("%s",recvFrom)
		self.process(self.incoming,self.client_address[0])
	
	def CheckMachine(self, machine):
		availableMachines = envisionSS.envisionDB.getMachines()
		if machine in availableMachines:
		#make sure machine exists, getValues returns relay, startTime, threadName, printLength, userID and status
			machineValues = envisionSS.envisionDB.getValues(machine)
			logger.debug("%s has values - %s",machine,machineValues)
			return machineValues
		else:
			logger.debug("%s not found in availableMachines",machine)
			return False
			
	def CheckID(self,machine,user):
	#check if the ID is in the OEC DB, and return detailed info about the user
		userInfo = envisionSS.oecDB.checkID(machine,user)
		#return value is Waiver, Certification, Admin, Supervisor, Major, Class_level, Suspended
		major = userInfo[4]
		level = userInfo[5]
		returnInfo = []
		#replyInfo = '|'.join([userInfo[4],userInfo[5]]) #join  Major and Class level for logging purposes
		logger.debug("SUSPENDED = %s",userInfo[6])
		#print userInfo[6]
		if userInfo[6] == 1:
		#user is suspended
			logger.info("USER is suspended")
			returnInfo.append("DENY")
			returnInfo.append("SUSPENDED")
		elif userInfo[5].startswith("M") or userInfo[5].startswith("D"):
		#check if student is a grad student, only allowed use of machines if VIS or is an envision Supervisor
			if machine.startswith("FRONT"):
			#if the machine is the front desk, everyone is allowed to login
				returnInfo.append("OK")
				returnInfo.append("|".join(["GRAD", major, level, machine]))
			elif userInfo[1] == "False":
				returnInfo.append("DENY")
				returnInfo.append("CERT")
			elif not userInfo[4].startswith("VIS") and userInfo[3]=="False":
			#is not VIS and is not a supervisor
				returnInfo.append("DENY")
				returnInfo.append("GRAD")
			else:
				if userInfo[2]=="True":
					returnInfo.append("OK")
					returnInfo.append("|".join(["ADMIN",major, level, machine]))
				else:
					returnInfo.append("OK")
					returnInfo.append("|".join(["VISGRAD",major, level, machine]))
		elif userInfo[0]=="True":
		#waiver is signed and up to date
			if userInfo[1] == "True":
			#certification is complete and up to date
				if userInfo[2] == "True":
				#accepted user is an admin
					returnInfo.append("OK")
					returnInfo.append("|".join(["ADMIN",major, level, machine]))
				else:
				#accepted user is not an admin
					returnInfo.append("OK")
					returnInfo.append("|".join(["USER",major, level, machine]))
			else:
				returnInfo.append("DENY")
				returnInfo.append("CERT")
		elif userInfo[0]=="False":
		#waiver is not complete or expired
			returnInfo.append("DENY")
			returnInfo.append("WAIVER")
		elif userInfo[1]=="False":
		#certification is not complete or expired
			returnInfo.append("DENY")
			returnInfo.append("CERT")
		else:
		#catch all error
			returnInfo.append("DENY")
			returnInfo.append("|".join("UNKNOWN",userInfo))	
		return returnInfo

	def ConnectMachine(self,machine):
		returnInfo = []
		if machine.split("_")[0] == "PRINTER":
			printers = envisionSS.envisionDB.getPrinters()
			returnInfo.append("OK")
			returnInfo.append("|".join(printers))
		elif machine.split("_")[0] == "LAPTOP":
			laptops = envisionSS.envisionDB.getLaptops(int(machine[-1]))
			returnInfo.append("OK")
			returnInfo.append("|".join(laptops))			
		else:
			returnInfo.append("OK")
			returnInfo.append("NONE")
		return returnInfo
		
	def ChangeStatus(self,machine,info):
		returnInfo = []
		if (envisionSS.envisionDB.updateMachine(machine,"status",info)):
			if info == "FALSE":
				returnInfo.append("OK")
				returnInfo.append("|".join(["DISABLED",machine]))	
			elif info == "TRUE":
				returnInfo.append("OK")
				returnInfo.append("|".join(["ENABLED",machine]))	
		else:
		#catch all
			returnInfo.append("DENY")
			returnInfo.append("DBERROR")
		return returnInfo
	
	def EndThread(self,machine,threadName):
		returnInfo = []
		if threadName:
			#turn off machine, this also ends the thread, and releases the machine / user
			#don't call stop directly, or thread will keep running in the background...
			getattr(envisionSS,threadName).runFlag = False
			endCount = 0
			#make sure the thread ended and the relay shutdown
			#this only tries 5 times, while shutting off the relay tries indefinitely
			#but this isn't threaded and I don't want the main program to hang...
			while True:
			#break when thread is cleared or after 5 attempts
				machineValues = envisionSS.envisionDB.getValues(machine)
				threadName = machineValues[3]
				if not threadName or endCount >=5:
					break
				else:
					logger.warning("%s not ending. Attempt %s",threadName, endCount)
					endCount += 1
				time.sleep(2) #wait 1 second between tries....maybe increase this if errors are happening often
			if endCount >= 5:
			#if loop brook because of too many attempts, alert the user that the print has not stopped
				logger.error("%s can't terminate. Ceasing attempts", threadName)
				returnInfo.append("DENY")
				returnInfo.append("FAILED")
			else:
				returnInfo.append("OK")
				msg = "|".join(["ENDED",machine])
				returnInfo.append(msg)
		else:
		#catches a potential race condition
				returnInfo.append("OK")
				msg = "|".join(["ENDED",machine])
				returnInfo.append(msg)
		return returnInfo

	def StartMachine(self,machine,user,major,level):
		returnInfo = []
		if machine.startswith("FRONT"):
		#front desk logs user and returns
			logID = envisionSS.envisionDB.logStart(user, machine, major, level)
			# query = 'UPDATE log set endTime = "' +endTime+'" WHERE logID="'+logID+'"'
			# self.cur.execute(query)
			returnInfo.append("OK")
			returnInfo.append("FRONT")
		elif machine.startswith("CASHIER"):
			balance = envisionSS.envisionDB.userExists(user)
			if balance:
				returnInfo.append("OK")
				returnInfo.append(balance)
			else:
				returnInfo.append("OK")
				returnInfo.append("UNKNOWN")	
		else:
		#if machine is not in use, add the user to the log and the users ID to the machine list
			logID = envisionSS.envisionDB.logStart(user, machine, major, level)
			envisionSS.envisionDB.updateMachine(machine,"user",user)
			envisionSS.envisionDB.updateMachine(machine,"logID",logID)
			addMessage = ("|").join(["ADDED",machine])
			returnInfo.append("OK")
			returnInfo.append(addMessage)
		return returnInfo
	
	def CheckMultiple(self,machine,user):
		returnInfo = []
		idUsed = envisionSS.envisionDB.checkUser(user, machine)
		if idUsed:
		#if the user is using another machine...
			if idUsed == "SAME":
			#if it's the same machine, ok
				addMessage = "|".join(["SAME",machine])
				returnInfo.append("OK")
				returnInfo.append(addMessage)
			elif idUsed == "IDINUSE":
			#if using another printer, not ok
				returnInfo.append("DENY")
				returnInfo.append("IDINUSE")
			elif idUsed == "OCCUPIED":
			#if machine is in use and the user is not the same, not ok
				returnInfo.append("DENY")
				returnInfo.append("OCCUPIED")
		else:
			returnInfo.append("OK")
			returnInfo.append(machine)
		return returnInfo
	def ReleaseID(self,machine,userID):
		returnInfo = []
		if userID:
			envisionSS.envisionDB.logEnd(machine)
			envisionSS.envisionDB.release(machine)
			returnInfo.append("OK")
			returnInfo.append(machine)
		else:
			returnInfo.append("DENY")
			returnInfo.append("NOTFOUND")
		return returnInfo
	
	def FreeTime(self,machine,info,threadName,printLength):
		returnInfo = []
		currentTime = int(printLength)
		addedTime = datetime.timedelta(seconds=int(info))
		newTime = str(currentTime+int(info))
		getattr(envisionSS,threadName).printLength += addedTime #tricky method to access the thread...kind of like a pointer
		envisionSS.envisionDB.updateMachine(machine,"printLength",newTime)
		#newBalance = '{:,.2f}'.format(newBalance)
		addMessage = "|".join(["FREE",info,machine])
		returnInfo.append("OK")
		returnInfo.append(addMessage)
		return returnInfo
	def AddTime(self,machine,user,info,threadName,printLength):
		returnInfo = []
		if threadName:
		#check if the thread already exists, if it does this is an admin
			#change the user to the owner of the thread (rather than the admin)
			user = envisionSS.envisionDB.getValues(machine)[5]
			balance = envisionSS.envisionDB.userExists(user) #get the user's ledger balance
			printCost = '{:,.2f}'.format(float(info)/100/36) #calculate the cost at $1 / hour
			newBalance = float(balance) - float(printCost)
			if newBalance >= 0:
			#user can afford the change
				userPaid = envisionSS.envisionDB.useFunds(user,printCost)
				if userPaid:
				#ledger deduction was a success, calculate new time, and update the machine DB
					currentTime = int(printLength)
					addedTime = datetime.timedelta(seconds=int(info))
					requestedTime = str(currentTime+int(info))
					getattr(envisionSS,threadName).printLength += addedTime #tricky method to access the thread...kind of like a pointer
					envisionSS.envisionDB.updateMachine(machine,"printLength",requestedTime)
					newBalance = '{:,.2f}'.format(newBalance)
					addMessage = "|".join(["ADDED",info,newBalance,machine])
					returnInfo.append("OK")
					returnInfo.append(addMessage)
				else:
				#ledger didn't update, but add the time anyway
					returnInfo.append("OK")
					msg = "|".join(["STARTED","FREE",machine])
					returnInfo.append(msg)
			else:
			#user cannot afford the change
				returnInfo.append("DENY")
				msg = "|".join(["ADDED",str(balance),machine])
				returnInfo.append(msg)
		
		else:
		#if thread doesn't exist, then this is a new timer
			threadName = machine.replace('-','_')
			if info == "ADMIN":
				balance = 1
				newBalance = 1
				info = 1800
				user = "ADMIN"
			else:
				balance = envisionSS.envisionDB.userExists(user)
			if float(balance) > 0:
			#can user afford the print
				printCost = '{:,.2f}'.format((float(info)/100/36)-0.25)
				newBalance = float(balance) - float(printCost)
				if newBalance >= 0:
					timeStamp = (datetime.datetime.now()).strftime('%Y%m%d-%H:%M:%S')
					envisionSS.envisionDB.updateMachine(machine,"startTime",timeStamp)
					machineValues = envisionSS.envisionDB.updateMachine(machine,"printLength",info)
					#setattr will set the thread object equal to envisionSS."name of the machine"
					#this will let me use the db to develop a pointer to the thread object with getattr
					setattr(envisionSS,threadName,TimerThread(self,machine,machineValues))
					getattr(envisionSS,threadName).start() #start the threaded timer
					startSuccess = getattr(envisionSS,threadName).sshRelay(relayOn) #start the machine
					#startSuccess = True
					if startSuccess:
					#relay started successfully
						envisionSS.envisionDB.updateMachine(machine,"thread",threadName)
						envisionSS.envisionDB.updateMachine(machine,"user",user)
						if not user == "ADMIN":
							userPaid = envisionSS.envisionDB.useFunds(user,printCost) #use the ledger db to deduct funds, returns false if failed
							if userPaid:
							#let user know new balance
								returnInfo.append("OK")
								newBalance = '{:,.2f}'.format(newBalance)
								msg = "|".join(["STARTED",newBalance,machine])
								returnInfo.append(msg)
							else:
							#let user know print was free
								returnInfo.append("OK")
								msg = "|".join(["STARTED","FREE",machine])
								returnInfo.append(msg)
						else:
							returnInfo.append("OK")
							msg = "|".join(["STARTED","ADMIN",machine])
							returnInfo.append(msg)
						logger.info("%s has Started",machine)
					elif not startSuccess:
					#relay start failed, delete the thread from the machine db
						returnInfo.append("DENY")
						returnInfo.append("RELAYFAIL")
						getattr(envisionSS,threadName).stop()
						envisionSS.envisionDB.updateMachine(machine,"startTime","NULL")
						envisionSS.envisionDB.updateMachine(machine,"printLength","NULL")
						envisionSS.envisionDB.updateMachine(machine,"thread","NULL")
						logger.error("%s failed to start",machine)
				else:
				#User did not have the funds to add time to the print
					returnInfo.append("DENY")
					msg = "|".join(["FUNDS",str(balance),machine])
					returnInfo.append(msg)
			else:
			#user did not have funds to start the print
				returnInfo.append("DENY")
				msg = "|".join(["FUNDS","FALSE",machine])
				returnInfo.append(msg)
		return returnInfo
	
	# def Checkout(self,machine,info):
		# returnInfo = []
		# user = info[0]
		# major = info[1]
		# level= info[2]
		# logID = envisionSS.envisionDB.logStart(user, machine, major, level)
		# envisionSS.envisionDB.updateMachine(machine,"user",user)
		# envisionSS.envisionDB.updateMachine(machine,"logID",logID)
		# returnInfo.append("OK")
		# returnInfo.append("ADDED")
		
	
	def AddUser(self,user):
		returnInfo = []
		if envisionSS.envisionDB.addNewUser(user):
			returnInfo.append("OK")
			returnInfo.append("ADDED")
		else:
			returnInfo.append("DENY")
			returnInfo.append("DBERROR")	
		return returnInfo
	
	def AddFunds(self, user, info):
		returnInfo = []
		balance = envisionSS.envisionDB.userExists(user)
		if (float(balance) + float(info)) <= 100:
		#check that the new balance won't be more than 100
			newBalance = envisionSS.envisionDB.addFunds(user,info)
			if newBalance:
				returnInfo.append("OK")
				returnInfo.append(newBalance)
			else:
				returnInfo.append("DENY")
				returnInfo.append("DBERROR")
		else:
		#if new balance will be more than 100, adjust added funds
			adjustedAdd = str(("%0.2f") %(100 - float(balance)))
			newBalance = envisionSS.envisionDB.addFunds(user,adjustedAdd)
			if newBalance:
				returnInfo.append("DENY")
				returnInfo.append(adjustedAdd)
			else:
				returnInfo.append("DENY")
				returnInfo.append("DBERROR")
		return returnInfo
	
	def AddCode(self, user, info):
		returnInfo = []
		updated = envisionSS.envisionDB.addCode(user,info)
		if updated[0] is True:
			returnInfo.extend(("OK",updated[1]))
		else:
		#can be false because code doesn't exist, or because code has already been used by user
			returnInfo.extend(("DENY",updated[1]))
		return returnInfo
	
	def Setup(self, info):
		returnInfo = []
		machineValues = envisionSS.envisionDB.getValues(info)
		isLaptop = True if info.startswith("LAPTOP") else False
		if isLaptop:
			startTime = machineValues[1]
			user = machineValues[2]
			machineStatus = machineValues[3]
		else:
			startTime = machineValues [2]
			printLength = machineValues[4]
			user = machineValues[5]
			machineStatus = machineValues[6]
		if user is None:
			if machineStatus.upper() == "FALSE":
				errorInfo = "|".join([info,"OFFLINE"])
				returnInfo.append("DENY")
				returnInfo.append(errorInfo)
			else:
				returnInfo.append("OK")
				returnInfo.append(info)
		else:
			if isLaptop:
				errorMsg = "|".join([info,"USER","FALSE","FALSE"])
			else:
				errorMsg = "|".join([info,"USER",startTime,printLength])
			returnInfo.append("DENY")
			returnInfo.append(errorMsg)
		return returnInfo
	
	
	def updateClientDict(self,machine,clientIP):
		clientDict[machine]=clientIP
		logger.info("%s written to hosts file with IP %s",machine,clientIP)
		hostsFile = "/etc/hosts"
		#print machine, clientIP
		if os.path.isfile(hostsFile):
		#check that the password file exists
			with open(hostsFile,'wb') as writeFile:
				ipWriter = csv.writer(writeFile,delimiter="\t",lineterminator="\n")
				for key,value in clientDict.items():
					ipWriter.writerow([value,key])
			logger.info("hostFile saved successfully")
		else:
			try:
				raise OSError ('\"HOSTFILE\" File is Corrupt or Missing')
			except OSError as error:
				logger.critical("hostFile does not exist %s", error)
	
	#process the packet from handle()
	def process(self, packet, clientIP):
		#incoming packet structure: EVENT, MACHINE, USER, INFO
		#reply packet structure: EVENT, OK/DENY, INFO
		logger.info("Packet contains %s",packet)
		command = packet[0]
		machine = packet[1]
		user = packet[2]
		info = packet[3].split("|")
		if machine in clientDict and clientIP == clientDict[machine]:
			pass
		else:
			self.updateClientDict(machine,clientIP)
		#envisionSS.connectDB("envision") #connect to the envision db
		reply=[]
		reply.append(command)#add the event to the reply
		acceptedMachines = ["PRINTER","CASHIER","LAPTOP"]
		if len(packet) == 4:
		#verify packet integrity
			e4Connect = envisionSS.envisionDB.connectDB()
			oecConnect = envisionSS.oecDB.connectDB()
			if e4Connect and oecConnect:
				goodMachine = True if machine.split("_")[0] in acceptedMachines else False
				#laptopMachine = True if machine.split("_")[0] == "LAPTOP" else False
				loggedMachine = self.CheckMachine(machine)
				if loggedMachine:
					relayNum = loggedMachine[1]
					startTime = loggedMachine[2]
					threadName = loggedMachine[3]
					printLength = loggedMachine[4]
					userID = loggedMachine[5]
					machineStatus = loggedMachine[6]
					logger.debug("machine thread is %s", threadName)
				if not (loggedMachine or goodMachine):
					logger.debug("%s is not Logged or Good. Not proceeding", machine)
					reply.extend(("ERROR","DENY","BADMACHINE"))
				else:
					if command =="EVT_CHECKID":
						reply.extend(self.CheckID(machine, user))
					elif command == "EVT_CONNECT":
					#Event called when a machine first starts and connects to the socket
						if loggedMachine:
							if userID:
							#if the machine is in use, return an error to lock the machine and start the local timer
								if startTime:
									errorMsg = "|".join([userID,startTime,printLength])
									reply.append("DENY")
									reply.append(errorMsg)
								else:
								#if there is no starttime value, the machine didn't correctly release the ID, release it now
									envisionSS.envisionDB.release(machine)
									reply.append("OK")
									reply.append("NONE")
							else:
							#machine is available
								if machineStatus == "TRUE":
								#machine is not in maintenance mode
									reply.append("OK")
									reply.append("NONE")
								else:
								#machine is in maintenance mode
									reply.append("DENY")
									reply.append("OFFLINE")
						else:
							reply.extend(self.ConnectMachine(machine))

					elif command == "EVT_CHANGE_STATUS":
					#switch in and out of maintenance mode
						reply.extend(self.ChangeStatus(machine, info[0]))
						
					#this fires when an admin chooses to cancel a timer / print
					elif command == "EVT_END":
						#check that the thread is actually running on this machine
						reply.extend(self.EndThread(machine,threadName))
					
					#this fires when user successfully logs into the GUI (accepts the TOS disclaimer)
					elif command == "EVT_START":
						if machine.startswith("CASHIER"):
							balance = envisionSS.envisionDB.userExists(user)
							if balance:
								reply.append("OK")
								reply.append(balance)
							else:
								reply.append("OK")
								reply.append("UNKNOWN")
						else:
							major = info[1]
							level = info[2]
							reply.extend(self.StartMachine(machine,user,major,level))
						
					
					elif command == "EVT_SINGLE_CHECK":
						reply.extend(self.CheckMultiple(machine,user))
					
					#this fires on closing the program without turning on the printer
					elif command == "EVT_RELEASE":
					#poor programming on the client side sometimes causes this to be called more than once
						# if threadName:
							# reply.append("DENY")
							# reply.append("BADTIME|"+startTime+"|"+printLength)
						reply.extend(self.ReleaseID(machine,user))

					elif command == "EVT_CHECKOUT":
						reply.extend(self.Checkout(machine,user))
					
					#this fires when time is added to a machine
					elif command == "EVT_ADD_TIME":
						reply.extend(self.AddTime(machine, user, info[0], threadName, printLength))

					elif command == "EVT_FREE_TIME":
						reply.extend(self.FreeTime(machine, info[0], threadName, printLength))
						
					elif command == "EVT_ADD_USER":
					#Fired if user is not in ledger
						reply.extend(self.AddUser(user))
				
					elif command == "EVT_ADD_FUNDS":
					#fired after a user adds funds
						reply.extend(self.AddFunds(user, info[0]))

					elif command == "EVT_ADD_CODE":
					#fired if a user uses a class code
						reply.extend(self.AddCode(user,info[0]))

					elif command == "EVT_SETUP":
						reply.extend(self.Setup(info[0]))
					elif command == "EVT_RETURN":
						reply.extend(self.ReleaseID(machine,user))
						reply[-1] = ('|').join([reply[-1],machine])
			else:
				reply.extend(("ERROR","DENY","DBERROR"))
		else:
		#packet is not properly formed by client
			reply.extend(("ERROR","DENY","BADPACKET"))
		
		self.respond(reply)
		## Decided to keep the database open until the server is shut. Each new call will reopen the connection anyway, I think this will be okay
		#envisionSS.envisionDB.closeDB() #close the db after each socket
		#envisionSS.oecDB.closeDB()
	def respond (self, packet):
	#respond to client
		i = 0
		for str in packet:
		#replace all spaces with an underscore (helps with string managment on client side)
			#print str
			packet[i]=str.replace(" ","_")
			i+=1
		packetStr = (" ".join(packet)).upper() #convert everything to uppercase
		logger.info("Replied %s", packet)
		self.request.sendall(packetStr)

#class to create and control the threaded print timers
class TimerThread(threading.Thread):
	#initialize the thread
	def __init__(self,parent,machine,values):
	#accept machine and machien properties as args
		threading.Thread.__init__(self)
		self.parent = parent
		self.machineValues = values
		self.machine = machine
		self.runFlag = True #run Flag indicates the thread is still running. Can be called externally to end the thread
		self.killFlag = False #kill flag can be set externally and allows the thread to end, but not clear the timer...timer can be resumed at a later time
		self.printLength = 0
	#required function called by start()
	def run(self):
		timeStamp = datetime.datetime.strptime(self.machineValues[2],'%Y%m%d-%H:%M:%S')
		self.printLength = datetime.timedelta(seconds=int(self.machineValues[4])) #set the timer length in seconds
		while self.runFlag:
		#run until timer expires or kill flag is set
			now = datetime.datetime.now()
			if (timeStamp + self.printLength < now):
			#check if the timer has expired, and end the thread by setting the run flag...kills the while loop
				self.runFlag = False
			else:
				time.sleep(1)
		if self.killFlag is False:
		#the killflag is set if the theard is ended before the timer has expired (for restarting the server, etc)
		#allows the thread to be restarted later, with all of the timestamps in place
		#if still False, call stop() to turn off the relay
			self.stop()
	#a kill function, that does not shut off the relay but stops the thread
	#allows the program to exit cleanly without killing prints
	def kill(self):
	#pretty sure the order of these variables are important. Set the kill(ed) flag, and then end the thread.
		self.killFlag = True
		self.runFlag = False
	def stop(self):
	#stop is a function to turn the relay off after the timer has expired
	#This create a new db connection. It's not ideal but I'm being lazy
		success = self.sshRelay(relayOff) #open an SSH tunnel to the relay machine, and send the off signal
		if success:
		#if the tunnel was a success
			logger.info("%s STOPPED", self.machine)
			#if envisionSS.envisionDB.cur is None:
			e4Connect = envisionSS.envisionDB.connectDB()
			if e4Connect:
				#db = MySQLdb.connect(host="localhost",user=envisionSS.username,passwd=envisionSS.password,db="envision_control")
				#db.autocommit(True)
				#cur = db.cursor()
				#update the log
				envisionSS.envisionDB.logEnd(self.machine)
				#clear the machine properties to release the machine and the user
				envisionSS.envisionDB.release(self.machine)
				#envisionSS.envisionDB.closeDB()
			else:
				logger.warning("Failed to connect to local DB...retrying")
				time.sleep(5)
				self.stop()

		else:
		#if the tunnel failed, wait 10 seconds and try again. This will keep trying until the relay turns off successfully
			logger.warning("%s Failed to Stop", self.machine)
			time.sleep(10)
			self.stop()
	#tunnel to the relay machine, and change the GPIO pin of the relay
	def sshRelay(self,command):
		logger.debug("ATTEMPTING TO MODIFY THE RELAY")
		if 0 < int(self.machineValues[1][5:]) <= 8:
		#relays 1-8 live on relayPi 1
			socketPi = "relayPi"
			relayNum = 0
		elif 8 > int(self.machineValues[1][5:]) <= 16:
		#relays 9-16 live on relayPi 2
			socketPi = "relayPi-2"
			relayNum = 1
		else:
		#relays 17-24 live on relayPi 3
			socketPi = "relayPi-3"
			relayNum = 2
		ssh = paramiko.SSHClient() #open the tunnel
		ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy()) #accept the host key (security risk, but there aren't any untrusted clients on this LAN
		#cmd = 'gpio -g write $'+self.machineValues[1]+' '+ command + '\n' #modify the gpio pin
		cmd = 'echo ' + command + ' > /sys/class/gpio/gpio$' + self.machineValues[1] + '/value\n'
		logger.debug("Sending %s to %s",cmd,socketPi)
		try:
			ssh.connect(socketPi,username=envisionSS.envisionDB.username,password=envisionSS.envisionDB.password)
			term=ssh.invoke_shell() #open a new shell
			success = term.send(cmd) #returns true if the 2>&1 is zero
			time.sleep(1) #need a delay before closing the shell
			term.close()
			ssh.close()
			if success:
				return True
			else:
				raise Exception
		except Exception as e:
			logger.critical("Failed SSH tunnel. Received %s",e)
			return False

			
class DatabaseHandler():
	def __init__(self,parent,location):
		self.parent = parent
		self.db = None
		self.cur = None
		if location == "oec":
			self.username = self.parent.passDict["db-user"]
			self.password = self.parent.passDict["db-pass"]
			self.host = "db.eng.ucsd.edu"
			self.database = "makerspace"
		elif location == "envision":
			self.username = self.parent.passDict["envision-user"]
			self.password = self.parent.passDict["envision-pass"]
			self.host = "localhost"
			self.database = "envision_control"
		
		#function connects to the appropriate DB, and sets the cursor and auto-commit variables
	def connectDB(self):
		#do i need a lock??
		try:
			self.db.open
		except AttributeError:
		#Initial connection required
			logger.debug("AttributeError on first DB access")
			try:
				self.db = MySQLdb.connect(host=self.host,user=self.username,passwd=self.password,db=self.database)
			except Exception as e:
				#need to add some error handling here for when the connection fails
				logger.critical("Failed to connect to DB on first try, received %s", e)
				return False
			else:
				self.db.autocommit(True) #changes made are committed on execution
				self.cur = self.db.cursor() #set the cursor to the beginning of the DB
				logger.info("New Connection to %s",self.host)
		else:
			try:
				self.db.cursor().execute("SELECT VERSION()")
			except Exception as e:
				logger.warning("Failed to re-connect to DB, received %s", e)
				try:
					self.db = MySQLdb.connect(host=self.host,user=self.username,passwd=self.password,db=self.database)
				except Exception as e:
					logger.critical("Failed to re-connect to DB, received %s", e)
					return False
				else:
					self.db.autocommit(True) #changes made are committed on execution
					self.cur = self.db.cursor() #set the cursor to the beginning of the DB
					logger.info("Connection to %s restarted",self.host)
			else:
				#self.db.autocommit(True) #changes made are committed on execution
				self.cur = self.db.cursor() #set the cursor to the beginning of the DB
				logger.debug("Connection to %s still alive",self.host)
		return True
	#function to clean up the connection 
	def closeDB(self):
		self.db.close()
		self.db = None
		self.cur = None
		logger.debug("DB Closed")
	
	#check that the user ID exists, and that the appropriate training has been completed
	def checkID(self,machine,user):
		userID = user.lstrip('0') #strip leading zeros from the userID passed from the client
		#which crendential to check
		if machine.startswith("MAKER"):
			cred = "mb"
		elif machine.startswith("TAZ"):
			cred = "lb"
		elif machine.startswith("UP"):
			cred = "up"
		elif machine.startswith("LASER"):
			cred = "lc"
		elif machine.startswith("VAC"):
			cred = "vc"
		elif machine.startswith("DRILL"):
			cred = "dp"
		else:
			cred = "waiver"						
		#DB query pulls all relevant details from OEC DB
		query = 'SELECT waiver,'+cred+',role,supervisor,dept,class_level,suspended FROM makerspace.users LEFT JOIN makerspace.users_access USING (user_id) WHERE (uceno ="'+userID+'" OR pid ="'+userID+'");'
		self.cur.execute(query) #execute the query
		results = self.cur.fetchall()#fetch all of the results 
		returnMsg = ["False","False","False","False","False","False","False"]#prepopulate a return value with False
		#check each result
		for result in results:
			if result[0] is not None:
			#if the result is None, keep the returnMsg index False, otherwise: populate the result
				if result[0] >= datetime.datetime.now() - datetime.timedelta(days=90):
				#check that the waiver is current (90 days)
					returnMsg[0]="True"
					if result[1] is not None:
					#credential
						returnMsg[1]="True"
					if result[2] is not None:
					#admin or not
						returnMsg[2]="True"
					if result[3] is not None:
					#check that the supervisor status is current (90 days)
						if result[3] >= datetime.datetime.now() - datetime.timedelta(days=90):
							returnMsg[3] = "True"
					if result[4] is not None:
					#department
						returnMsg[4]=(result[4])
					if result[5] is not None:
					#class level
						returnMsg[5]=str(result[5])
					if result[6] is not None:
					#suspended
						returnMsg[6]=result[6]						
				break	
		return returnMsg
	#create a log entry for the user and machine
	def logStart(self, user, machine, major, level):
		startTime = datetime.datetime.now().strftime('%Y%m%d-%H:%M')
		userInfo = '","'.join([user, major, level, machine, startTime])
		userInfo = '"'+userInfo+'"'
		query = 'INSERT into log (user, major, level, machine, startTime) VALUES (' + userInfo + ')'
		self.cur.execute(query)
		query = 'SELECT LAST_INSERT_ID();'#keep the entry ID in a variable to use later
		self.cur.execute(query)
		logID = str(self.cur.fetchone()[0])
		if machine.startswith("FRONT"):
			query = 'UPDATE log set endTime = "' +startTime+'" WHERE logID="'+logID+'"'
			self.cur.execute(query)
		logger.info("LOG UPDATED %s STARTED WITH LOGID %s ",machine,logID) #debug info
		return logID #pass the entry ID around, to use later for logEnd()
	#append a log entry for user and machine and amount of time used	
	def logEnd(self, machine):
		#the logID was added to the machine table, fetch it from the machine, and update the log that has that ID
		table = "laptops" if machine.startswith("LAPTOP") else "machines"
		query = 'SELECT logID from ' + table + ' WHERE name = "' +machine+'"'
		self.cur.execute(query)
		logID = str(self.cur.fetchone()[0])
		endTime = (datetime.datetime.now()).strftime('%Y%m%d-%H:%M')
		query = 'UPDATE log set endTime = "' +endTime+'" WHERE logID="'+logID+'"'
		self.cur.execute(query)
		logger.info("LOG UPDATED %s ENDED WITH LOGID %s ",machine,logID) #debug info
	
	#update the machine table with a property and value				
	def updateMachine(self,machine,prop,value):
		machine = str(machine)
		prop = str(prop)
		value = str(value)
		table = "laptops" if machine.startswith("LAPTOP") else "machines"
		query = 'UPDATE ' + table + ' set '+prop+'="'+value+'" WHERE name="'+machine+'"'
		self.cur.execute(query)
		values = self.getValues(machine)
		return values
	#check whether or not a user is already in the machine table
	def checkUser(self,user, machine):
		isLaptop = True if machine.startswith("LAPTOP") else False
		if isLaptop:
			query = 'SELECT user, name FROM laptops WHERE name = "'+machine+'"'
			self.cur.execute(query)
			result = self.cur.fetchone()
		else:
			query = 'SELECT user, name, relay FROM machines WHERE name = "'+machine+'"'
			self.cur.execute(query)
			result = self.cur.fetchone()
			if result[2] == "False":
			#If this machine does not have a relay, it is not a printer, and user can use regardless of what other machines theyre using
				return False
		if result[0] is not None:
		#this machine is occupied by SOME user
			if result[0] == user:
			#this machine occupied by the current user, access is okay
				return "SAME"
			else:
			#this machine is occupied by a different user, access is denied
				return "OCCUPIED"

		else:
		#machine is free but need to check if id is in use on other machines
			if isLaptop:
				query = 'SELECT user, name FROM laptops'
			else:
				query = 'SELECT user, name, relay FROM machines'
			self.cur.execute(query)
			results = self.cur.fetchall()
			for result in results:
				if user in result:
				#user exists in the machine table...are they using another 3d printer?
					if not isLaptop and result[2] == "False":
					#if there is no relay on this machine, it is a not a printer, so it doesn't matter if user is using it
						continue #keep checking
					else:
					#user exists in the table, and are using another 3d printer...not allowed
						return "IDINUSE"
		return False
	#get the list of machines from the machine tables
	def getMachines(self):
		query = "SELECT name FROM machines"
		self.cur.execute(query)
		result = self.cur.fetchall()
		machines = []
		for machine in result:
			machines.append(machine[0])
		return(machines)#return the list of machines
	def getPrinters(self):
		query = "SELECT name FROM machines where relay !='False'"
		self.cur.execute(query)
		result = self.cur.fetchall()
		machines = []
		for machine in result:
			machines.append(machine[0])
		return(machines)#return the list of machines
	def getLaptops(self,cabinet):
		endNum = str(16 * cabinet - 1)
		startNum = str(16 * cabinet - 15)
		query = "SELECT name FROM laptops WHERE RIGHT(name,2) BETWEEN " + startNum + " AND " + endNum
		self.cur.execute(query)
		result = self.cur.fetchall()
		machines = []
		for machine in result:
			machines.append(machine[0])
		return(machines)#return the list of machines	
	
	#release the current user from the machine table, and reset all values  to DEFAULT (None)
	def release(self,machine):
		if machine.startswith("LAPTOP"):
			query = 'UPDATE laptops set user=DEFAULT, starttime=DEFAULT, logID=DEFAULT WHERE name="'+machine+'"'
		else:
			query = 'UPDATE machines set user=DEFAULT, starttime=DEFAULT, thread=DEFAULT, printlength=DEFAULT, logID=DEFAULT WHERE name="'+machine+'"'
		self.cur.execute(query)
	#if a thread is currently running, stop it
	def stopThreads(self):
		query = "SELECT name,thread FROM machines WHERE thread IS NOT NULL"
		self.cur.execute(query)
		machines = self.cur.fetchall()
		for machine in machines:
			logger.info("Stopping Thread on %s",machine[0])
			getattr(envisionSS,machine[1]).kill()
	#get all of the relevant values for the given machine
	def getValues(self, machine):
		if machine.startswith("LAPTOP"):
			query = 'SELECT name,starttime,user,status FROM laptops WHERE name="'+machine+'"'
		else:
			query = 'SELECT name,relay,starttime,thread,printlength,user,status FROM machines WHERE name="'+machine+'"'
		logger.debug("Execute query %s",query)
		self.cur.execute(query)
		values = self.cur.fetchall()
		#logger.debug("Receieved db values %s",values)
		if len(values) > 0:
			return values[0]
		else:
			return False
	#check the machine table...if a thread was shutdown prematurely, restart it		
	def restartThreads(self):
		query = "SELECT name,thread FROM machines WHERE thread IS NOT NULL"
		self.cur.execute(query)
		machines = self.cur.fetchall()
		for machine in machines:
			logger.info("Restarting Thread on %s",machine[0])
			machineValues = self.getValues(machine[0])
			threadName = machine[0].replace('-','_') #minus signs cause problems with the getattr call, replace with underscore
			setattr(envisionSS,threadName,TimerThread(self,machine[0],machineValues))
			getattr(envisionSS,threadName).start()#start a thread
			query = 'UPDATE machines set thread="'+threadName+'" WHERE name="'+machine[0]+'"'#update the table
			self.cur.execute(query)	
	"""
	-----------------------------------------------------------------------------------------------
	"""
	##LEDGER FUNCTIONS
	#Check if the user exists in the ledger db
	def userExists(self,user):
		query = 'SELECT balance FROM ledger WHERE user ="' + user +'"'
		result = self.cur.execute(query)
		if bool(result):
		#if the user already has a balance (has registered for the ledger) than return the balance
			balance = self.cur.fetchone()[0]
			return str(balance)
		else:
		#else return False to indicate the user needs to agree to the terms of use
			return False
	#add a user to the ledger
	def addNewUser(self,user):
		query = 'INSERT INTO ledger (user,balance,owed) VALUES ("'+user+'","5","0")'
		try:
			self.cur.execute(query)
		except Exception as e:
			logger.error("DB error, %s",e)
			return False
		else:
			return True
	#subtract funds from the users ledger balance, return the new balance
	def useFunds(self, user, funds):
		query = 'UPDATE ledger SET balance=balance - '+ funds + ' WHERE user="' + user+'"'
		self.cur.execute(query)
		newBalance = self.userExists(user)
		if bool(newBalance):
			return str(newBalance)
		else:
			return False
	#add funds to the users ledger balance and return the new balance
	def addFunds(self, user, funds):
		query = 'UPDATE ledger SET balance=balance + '+ funds + ' WHERE user="' + user+'"'
		self.cur.execute(query)
		newBalance = self.userExists(user)
		if bool(newBalance):
			query = 'UPDATE ledger SET owed=owed + '+ funds + ' WHERE user="' + user+'"'
			self.cur.execute(query)
			query = 'UPDATE ledger SET timestamp=NOW() WHERE user="' + user+'"'
			self.cur.execute(query)
			return str(newBalance)
		else:
			return False
	#users can also use a predefiend code (stored in a seperate table) to add funds to their ledger balance
	def addCode(self,user,code):
		errorFlag = False
		query = 'SELECT id,stipend FROM classes WHERE code="'+code+'"'
		result = self.cur.execute(query)
		if bool(result):
			data = self.cur.fetchall()
			codeID = str(data[0][0]) #what is the ID of the code (stored in the users ledger, to indicate they have used this code)
			funds = data[0][1] #how much does the code add?
			if funds > 0:
				funds = str(funds)
				query = 'SELECT balance FROM ledger WHERE user ="' + user +'"'
				result=self.cur.execute(query)
				if bool(result):
				#if the balance exists, this is redundant to make sure user is registered
					balance = str(self.cur.fetchone()[0])
					if float(balance) + float(funds) <= 100:
					#make sure adding the code won't set balance to more than 100
						query = 'SELECT codes FROM ledger WHERE user ="' + user +'"'
						result=self.cur.execute(query)
						if bool(result):
						#check if the user has used any codes this quarter
							usedCodes = self.cur.fetchall()[0][0].split(',')
							if codeID not in usedCodes:
							#check if this particular code has been used
								usedCodes.append(codeID)
								if bool(int(usedCodes[0])) is False:
								#add a new code
									newCodes = codeID
								else:
								#append to existing list of used codes
									newCodes = ','.join(usedCodes)
								query = 'UPDATE ledger SET codes ="'+newCodes+'" WHERE user="' + user+'"'
								result=self.cur.execute(query)
								if bool(result):
								#catch all for updating the ledger
									query = 'UPDATE classes SET users = users + 1 WHERE id="' + codeID +'"'
									result=self.cur.execute(query)
									if bool(result) is False:
										errorFlag = True
										error = "DBERROR"							
								else:
									errorFlag = True
									error = "DBERROR"
							else:
							#already used the code
								errorFlag = True
								error = "USED"									
						else:
							errorFlag = True
							error = "DBERROR"
					else:
					#funds are too high
						errorFlag = True
						error = "MAX"
			else:
			#user is not in the ledger
				errorFlag = True
				error = "ZERO"
		else:
		#code doesn't exist
			errorFlag = True
			error = "NOCODE"
		if errorFlag:
			return (False,error)
		else:
			query = 'UPDATE ledger SET balance=balance + '+ funds + ' WHERE user="' + user+'"'
			self.cur.execute(query)
			newBalance = self.userExists(user)
			return(True, str(newBalance))

class ThreadedTCPServer (SocketServer.ThreadingMixIn, SocketServer.TCPServer):
	pass
			
#main class that contains the DB functionalities
class EnvisionServer():
	def __init__(self):
		if os.path.isfile(passFile):
		#check that the password file exists
			with open(passFile,'r') as dataFile:
			#load the json file into a dict
				self.passDict = json.load(dataFile) # load json info into a list of dicts
		else:
			try:
				raise OSError ('\"PassList\" File is Corrupt or Missing')
			except OSError as error:
				logger.critical("Passlist does not exist %s", error)
				sys.exit(1)
		#user and pass will differ depending on which DB is being accessed
		self.username = None
		self.password = None
		now = datetime.datetime.now()
		#print str(now)#debug info
		#seperate variables for each database. This isn't necessary but makes it explicit which DB operation is being performed
		self.oecDB = DatabaseHandler(self,"oec") #OECs DB
		self.envisionDB = DatabaseHandler(self,"envision")#EnVision DB related to machines, classes, and users

def closeUp(msg,event):
#function to close the socket and terminate all active threads
#threads terminate without turning off the relays
	envisionSS.envisionDB.connectDB()
	#envisionSS.envisionDB.stopThreads() #stop the threads but keep the relays on
	envisionSS.envisionDB.closeDB()
	server.shutdown()
	
	#print debug info
	logger.info("Server shutdown with %s message",msg)
	now = datetime.datetime.now()
	event.set() #helpful for shutting down the socket with a ctrl-c command
	return

def terminate(signal,frame):
	t = threading.Thread(target = shutdownHandler,args = ('Shut down successfully by systemd',doneEvent))
	t.start()	


if __name__ == "__main__":
#not sure what this does, was helpful to get ctrl-c to work properly
#termination will still sometimes hang on shutting down the port
#restarting requires killing the python process that has the port open
	doneEvent = threading.Event()
	signal.signal(signal.SIGTERM, terminate)
	envisionSS=EnvisionServer()
	clientDict = {}
	with open("/etc/hosts",'r') as hostsFile:
		ipReader = csv.reader(hostsFile,delimiter='\t')
		for hosts in ipReader:
			clientDict[hosts[1]]=hosts[0]
	#print clientDict
	HOST, PORT = "192.168.111.111", 6969
	#HOST, PORT = "192.168.111.111", 9000
	SocketServer.TCPServer.allow_reuse_address = True #just in case the port wasn't closed properly...doesn't always work
	
	#Threaded server
	#I think there is a potential for catastrophic race conditions using threads
	#but the benefit of not waiting for longer runs is high
	server = ThreadedTCPServer((HOST, PORT), MyTCPHandler)
	
	#Synchronous server
	#server = SocketServer.TCPServer((HOST, PORT), MyTCPHandler)
	
	server.allow_reuse_address = True
	server.daemon = True
	
	envisionSS.envisionDB.connectDB()
	#envisionSS.envisionDB.restartThreads() #restart any threads that were shutdown on last termination
	envisionSS.envisionDB.closeDB()
	try:
		server.serve_forever()
		doneEvent.wait()
	except KeyboardInterrupt:
		closeUp("Shut down successfully with KeyboardInterrupt",doneEvent)
		sys.exit(0)
	except:
		closeUp("Shut down successfully with unknown error",doneEvent)
		sys.exit(0)
