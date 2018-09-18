#!/usr/bin/env python
"""
EnVision User Management System (EUMS)
The EnVision Arts and Engineering Maker Studio
UC San Diego
Jacobs School of Engineering
Jesse DeWald
May 2017
All Rights Reserved
"""

#imported functions
import os, time, sys #basic OS functions
import wx #wxpython, used to build the GUI
import datetime #timestamp functions
from wx.lib.pubsub import pub #used to "listen" for messages sent by spawned GUI windows
import threading, subprocess, signal #used for threading external programs
import socket #communicate, via a socket, to external (or local!) server
import wx.lib.agw.pybusyinfo as PBI

#Version Tracking
version = "v181"
"""
##TODO for 75:
- add logger
-- "Are you sure you want want to spend money" to balance info
- Add admin extra time....admins can add time to be deducted from users account, or from EnVisions Account
- Add/ modify timer dialog cancels print when exited....fix this.
- !!!! countdown counts by 2s when another instance of cura is opened...make sure this doesn't also happen with MB / UP
- fix wx.panel in main GUI (like change made for v69)
- add lockOut (see VacForm version)---not sure this is possible now
- add 'cancel / add time' for same user swipe in
- add ADMIN abilities (use more than one machine)
- Full kill for threaded group in MSW....this is online somewhere -> otherwise there's a bug if a dialog is open when countdown expires

#CHANGELOG
--- 180: changed line 1200 to stop the expireTimer when popupwindow is called (thread started or restarted)
		hopefully this prevent double counting and timer freezing?
--- 179: contacting server busy box, added redlight for front desk DENY responses
-- 178: migrated to db check for checking id, instead of using a json file
-- 		threaded lights on front desk
--		added machine logging (including front desk) to envision DB
-- 74 changed cert expiration to only apply to responsibility contract, added UP! training requirements in machineStart()
-- 73 fixed isAdmin issue in idEnter
-- 72: added self.setfocus on threadended...hopefully this works

-- 71: skipped 70, added cashier and ledger support. also changed seconds2Expire=False after EVT_ADD_TIME is denied...this may cause some hiccups. Added popups for confirmations. Added popup for "ARE YOU SURE YOU WANT TO SPEND MONEY"
-- 69: finally fixed the discoloration on MSW machines by successfully using a wx.panel 
-- 68 fixed issue with idstrings being out of range in idcheck (changed >= to > in onkeypress)
-- fixed lockfile checking to use a 'continue' statement instead of a 'pass'
#67 open access json file -- will build GUI for this 
#66 added relay box to taz machines
#65 fixed refresh bug for machine offline
#64 added admin-role instead of supervisor...only admins can add/cancel time. Supervisors include TAs etc, but not volunteers / staff
#	supervisor expiration of 90 days (one quarter). Right now, isSupervisor allows grad students to use machines...but more benefits can be added if necessary
#63 added end timer and add time abilitiy for supervisor
#62	add error handling for a relayFail event, only turn on timer if EVT_ADD_TIME was accepted
#61 added a workaround for releaseID event not found dialog. Need to fix this.
#attempt to correct releaseID event issue...not sure if working yet...
#add a lock-file check in update users.
#bug fix update users was resetting the userIDnumber and causing a NONE arguement to be sent in socket sendEvent
#some bug on the redraw with updateusers and countDown2Expire
#only kill thread (and popup frame) when countdown ends, otherwise just hide
#fixed an error message on evt_release
#Taz machines end the threaded program (cura) to timeout...don't need relay
#Yield after timeframe.destory to prevent except/try from not catching
#user job tracking complete 
#envision-local controls relay pi
#machine lock-down, countdown updater
#one machine per user
#Reconfigured mainWindow function layout
#Add popup countdown timer (dead man)
#Add socketed connections
#limits grad student usage, add LB training requirement
#updated PID / EID search to eliminate possible mismatches
#add supervisor disable (made better from v39)
"""

#check OS platform, MSW and GTK (Linux) behave differntly with wxPython
if wx.Platform == "__WXMSW__":
	MSW = True
	GTK = False
else:
	GTK = True
	MSW = False

#haven't implemented a debug mode yet, so this is a useless variable
debug = False

#machine name is passed in command line to identify which equipment is being controlled
#this name is used to communicate to the socket-server who is passing commands
if len(sys.argv) > 1:
	machineName = sys.argv[1]
	#enables debug features (actually disables obnnoxious features while debugging)
	if machineName == "debug":
		debug = True
	else:
		debug = False
else:
	#this clause should never be needed
	machineName = 'no_machine_name'

#front desk has control of wireless xbees, pyserial provides the control
if machineName.startswith('front') and not debug:
	import serial
	#xbee behaves like a keyboard on the listed port and the listed baudrate
	xbee = serial.Serial(port = '/dev/ttyUSB0', baudrate=9600, parity = serial.PARITY_NONE, stopbits = serial.STOPBITS_ONE, bytesize=serial.EIGHTBITS)
else:
	xbee=None

		
#these global variables need to be moved inside of MainWindow init

#will the panel accept keyboard input?
acceptString = False 
#stores keyboard characters as they come in
inputList = []
now = datetime.datetime.now()
#time limit for the waivers...in days
timeLimit = 90


#standard UCSD id length, including leading and trailing '$' from mag-reader
idLength = 11

#version string for GUI 
envisionVersion = "EnVision Maker Studio (" +version + ")\n< " +machineName+ " >"
#how many hours are prints limited to?
maxPrintLength = 5

#address to communicate to the server on
#serverAddress = 'localhost'
serverAddress = 'envision-local'
#if machine is in maintenace mode, disabled = True
disabled = False

#this frame is used as a countdown timer for more time in timeFrame. If the user is idle for too long, the threaded program is minimized
#and the main GUI is un-hidden
class idleFrame(wx.Frame):
	def __init__(self,parent):
		"""Constructor"""
		wx.Frame.__init__(self, parent, style= wx.STAY_ON_TOP | wx.NO_BORDER | wx.FRAME_NO_TASKBAR, title="More Time?",size=(220,160))
		panel = wx.Panel(self,style=wx.SUNKEN_BORDER,size=(220,160))
		
		self.idleMessage = "Do you need more time?\nProgram will exit in"
		self.idleText = wx.StaticText(panel,label=self.idleMessage)
		#how many seconds to give the user to decide if they need more time
		self.idleMessageTime = 15
		self.timeText = wx.StaticText(panel,label=str(self.idleMessageTime)+" seconds")
		self.timeFont = wx.Font(12,wx.FONTFAMILY_SWISS,wx.FONTSTYLE_NORMAL,wx.FONTWEIGHT_BOLD)
		self.timeText.SetFont(self.timeFont)
		self.timeText.SetForegroundColour((255,0,0))
		
		#set the timer as a wx Timer
		self.idleTimer = wx.Timer(self)
		#and bind it to idleUpdate function
		self.Bind(wx.EVT_TIMER,self.idleUpdate,self.idleTimer)
		
		#buttons for the idleFrame
		yesBtn = wx.Button(panel, label="YES")
		exitBtn = wx.Button(panel, label="EXIT")
		yesBtn.Bind(wx.EVT_BUTTON, self.onYes)
		exitBtn.Bind(wx.EVT_BUTTON, self.onExit)
		
		#sizer layout
		sizer = wx.BoxSizer(wx.VERTICAL)
		buttonSizer = wx.BoxSizer(wx.HORIZONTAL)
		flags = wx.ALL|wx.CENTER
		buttonSizer.Add(yesBtn,1,flags|wx.EXPAND,5)
		buttonSizer.Add(exitBtn,1,flags|wx.EXPAND,5)
		sizer.Add(self.idleText,1,flags|wx.ALIGN_CENTRE_HORIZONTAL,10)
		sizer.Add(self.timeText,1,flags|wx.ALIGN_CENTRE_HORIZONTAL,10)
		sizer.Add(buttonSizer,1,flags|wx.EXPAND,10)
		self.SetSizer(sizer)
		self.alignToCenter(self)
		self.Layout()
		#start the timer to fire every second
		self.idleTimer.Start(1000)
	
	def alignToCenter(self,window):
	#set the window dead-center of the screen
		dw, dh = wx.DisplaySize()
		w, h = window.GetSize()
		x = dw/2 - w/2
		y = dh/2 - h/2
		window.SetPosition((x,y))
		#print dw, dh, w, h, x, y	
		
	def idleUpdate(self,event):
	#functions that fires with the wxTimer, updates the window text to reflect how many seconds are left
		if self.idleMessageTime > 0:
		#if there is still time in the timer, decrease by one second
			self.idleMessageTime -= 1
			self.timeText.SetLabel(str(self.idleMessageTime)+" seconds")
		else:
		#else if timer has expired, call the onExit function
			self.onExit(wx.EVT_BUTTON)
	def onExit(self,event):
	#when the timer has ended (by user or countdown), stop the timer; destroy the frame; "stop" the thread using the stop function
		self.idleTimer.Stop()
		self.Destroy()
		app.frame.programWorker.stop()
		
	def onYes(self,event):
	#is user needs more time, restart the timer in timeFrame
		app.frame.timeFrame.inactiveCount = 0
		app.frame.timeFrame.timer.Start(5000)
		self.idleTimer.Stop()
		self.Destroy()

#this frame allows the user to select the length of print they want, and communicates with the timeListener function in the MainWindow
class popupFrame(wx.Frame):
	def __init__(self,parent):
		"""Constructor"""
		wx.Frame.__init__(self, parent, style=wx.STAY_ON_TOP | wx.NO_BORDER | wx.FRAME_NO_TASKBAR, title="Popup Frame",size=(400,200))
		panel = wx.Panel(self,style=wx.SUNKEN_BORDER,size=(400,200))
		
		msg = "* Enter the Length of Your Print Below *"
		msg2 = "Printer Will Turn ON After Submission"
		msg3 = "TIMER WILL START AFTER 15 MINUTES"
		instructions = wx.StaticText(panel, label=msg)
		instructions.SetForegroundColour((255,0,0))
		information = wx.StaticText(panel, label=msg2, style=wx.ALIGN_CENTRE_HORIZONTAL)
		self.warning = wx.StaticText(panel, label=msg3, style=wx.ALIGN_CENTRE_HORIZONTAL)
		self.warningFont = wx.Font(12,wx.FONTFAMILY_SWISS,wx.FONTSTYLE_NORMAL,wx.FONTWEIGHT_BOLD)
		self.warning.SetFont(self.warningFont)
		#control the number of hours allowed with a global variable
		self.maxTime = maxPrintLength
		
		hours = wx.StaticText(panel,label="HOURS")
		minutes = wx.StaticText(panel, label="MINUTES")
		self.hourTxt = wx.Choice(panel, choices=[str(x) for x in range(0,self.maxTime + 1)])
		#15 minute increments
		self.minTxt = wx.Choice(panel, choices=['00','15','30','45'])
		self.submitBtn = wx.Button(panel, label="SUBMIT")
		
		#available buttons to the user
		self.submitBtn.Bind(wx.EVT_BUTTON, self.onEnter)
		self.hourTxt.Bind(wx.EVT_CHOICE, self.onChoice)
		self.minTxt.Bind(wx.EVT_CHOICE, self.onChoice)
		
		#bind a wxTimer to UpdateEvent, this timer deterimines if the windows is inactive
		#it does this by checking if the popupFrame has focus for a set amount of time (it shouldn't if the user is using the system)
		self.timer = wx.Timer(self)
		self.Bind(wx.EVT_TIMER,self.UpdateEvent,self.timer)
		
		#bind a second timer to UpdateCountdown
		#this timer is started when the user submits a print time successfully, and is the timer for the print itself
		#it updates the variable seconds2Expire which is also shared with the mainWindow
		self.timer2 = wx.Timer(self)
		self.Bind(wx.EVT_TIMER, self.UpdateCountdown, self.timer2)
		
		#sizer layout
		sizerVert = wx.BoxSizer(wx.VERTICAL)
		sizerHor = wx.BoxSizer(wx.HORIZONTAL)
		flags = wx.ALL|wx.CENTER
		sizerHor.Add(self.hourTxt, 0, flags, 5)
		sizerHor.Add(hours,0,flags,5)
		sizerHor.Add(self.minTxt, 0, flags, 5)
		sizerHor.Add(minutes,0,flags,5)
		sizerVert.Add(instructions, 0, flags, 10)
		sizerVert.Add(sizerHor,0,flags,5)
		sizerVert.Add(self.submitBtn, 0, flags, 5)
		sizerVert.Add(information, 0, flags, 10)
		sizerVert.Add(self.warning, 0, flags, 10)
		
		self.minTxt.Enable(False)
		self.submitBtn.Enable(False)
		
		self.SetSizer(sizerVert)
		self.alignToBottomRight(self)
		self.Layout()
		#start the inactivity timer at zero timeouts...on two inactive counts, it triggers the idleFrame
		#the first instance fires 10 seconds after the thread is opened
		app.frame.expireTimer.Stop() #added this to prevent double counting
		self.timer.Start(10000)
		self.inactiveCount = 0
	
	#align the print time frame to the bottom right of the screen...this seems to be the least obstrusive
	def alignToBottomRight(self,window):
		dw, dh = wx.DisplaySize()
		w, h = window.GetSize()
		x = dw - w
		y = dh - h
		window.SetPosition((x,y))
	
	#checks if the user is inactive by seeing if the popupFrame has had focus for a period of time
	#if if has for 2 straight cycles, user is determined to be inactive
	def UpdateEvent(self,event):
		#if inactive is at zero, it means the timer fired on opening, it restarts the timer to a specified time 
		if self.inactiveCount == 0:
			self.timer.Stop()
			self.timer.Start(1000*60*2) #set the idle time to be 2 minutes
			#self.timer.Start(1000*5)
		if not popupFrame.IsActive(self):
		#if the popupFrame is not active, make it active, restart the inactive count (because the user was using the system)
		#this takes the users' focus away from their task, it's not ideal, but it works
			self.SetFocus()
			self.Raise()
			self.inactiveCount = 0
		else:
		#else if the popupFrame was active, increase the inactive count, because the user hasn't been using the system
			self.inactiveCount +=1
		if self.inactiveCount >= 2:
		#if the user hasn't used the system for two cylces, stop the timer, and call the idleframe message to ask if user
		#wants more time
			self.timer.Stop()
			self.messageFrame = idleFrame(self)
			self.messageFrame.Show()
	
	#update the print length timer and display accordingly
	def UpdateCountdown(self,event):
		if app.frame.seconds2Expire  > 0:
			app.frame.seconds2Expire -= 1
			self.warning.SetLabel(str(datetime.timedelta(seconds=app.frame.seconds2Expire)))
		else:
			app.frame.programWorker.stop()
	#makes sure all timers are cancelled on close and set the GUI to lock if a user has started a print
	def onClose(self):
		self.timer.Stop()
		self.timer2.Stop()
		if app.frame.seconds2Expire:
			app.frame.branding.SetLabel("MACHINE IN USE: " + str(datetime.timedelta(seconds=app.frame.seconds2Expire))+'\n')
			#app.frame.branding.SetFont(app.frame.countDownFont)
			app.frame.Layout()
			app.frame.expireTimer.Start(1000)
	
	#action to take on button press
	def onChoice(self, event):
		#pull the user selections
		hours = self.hourTxt.GetStringSelection()
		mins = self.minTxt.GetStringSelection()
		if hours:
		#if the user has selected a choice for hours
			if int(hours) < self.maxTime:
			#prevent user from selecting the maximum hours, and then adding some more minutes
				self.minTxt.Enable(True)
				if hours == "0" and mins == "00":
				#make sure user can't submit a time of zero
					self.submitBtn.Enable(False)
				else:
					if mins:
					#if hour and minute have been selected, enable the submit button
						self.submitBtn.Enable(True)
			else:
			#if hours are greater than max time, set minutes to zero automatically
				self.minTxt.Enable(False)
				self.minTxt.SetSelection(0)
				self.submitBtn.Enable(True)
	#action to take on submit button
	def onEnter(self, event):
		#should probably change this to reflect how much the print is going to cost
		agreeDlg = wx.MessageDialog(self, "THIS IS REAL MONEY\n\nAre you sure?", "PROCEED?", wx.OK | wx.CANCEL)
		result = agreeDlg.ShowModal()
		agreeDlg.Close()
		agreeDlg.Destroy()
		if result == wx.ID_CANCEL:
			return
		elif result == wx.ID_OK:
		#if user agress, get the time choosen and send it to the pub listener "timelistener"
			hours = self.hourTxt.GetStringSelection()
			mins = self.minTxt.GetStringSelection()
			#print hours, mins
			pub.sendMessage("timeListener", timeHour=hours, timeMinute=mins)
			#pub.sendMessage("timeListener", timeHour=hours, timeMinute="1")
#thread for the socket communicator
class SocketThread(threading.Thread):
	#initializer, takes parent and a message as inputs
	def __init__(self,parent,message):
		threading.Thread.__init__(self)
		self.parent=parent
		self.message=message
	#called automatically by the start() function (implicitly defined by the threading class)... required
	def run(self):
		pass
	#use this function to send message through the socket to the server. Function expects a packet length of 3
	def sendEvent(self,eventPacket):
		#display a waiting message
		message = "Contacting Server..."
		busyMsg = PBI.PyBusyInfo(message, parent=None, title=" ")
		wx.Yield()
		# convert all messages to uppercase
		packet = [x.upper() for x in eventPacket]
		#form the list into a string delineated by a SPACE 
		packetStr = ' '.join(packet)
		try:

			#connect to the server on the port specified
			client = socket.create_connection((serverAddress, 6969))
			#send the packet string
			client.send(packetStr)
			#receive a response in a buffer, and split string into a list
			reply=(client.recv(1024)).split()
		except Exception, msg:
			#call this function if the connection was a failure
			del busyMsg
			wx.CallAfter(self.parent.socketClosed,wx.EVT_CLOSE,msg)
		else:
			del busyMsg
			if len(reply) == 3:
			#make sure the reply packet is properly formed
				if reply[0] == packet[0] and reply[1]:
				#make sure the correct packet was received by comparing the outgoing and the incoming EVENT (EVT)
					#send the reply to the pub listener "socketListener"
					pub.sendMessage("socketListener", sent=packet, reply=reply)
			else:
				#alert the GUI that the packet was incorrect
				wx.CallAfter(self.parent.socketClosed,wx.EVT_CLOSE,"BAD-FORMED REPLY")
	#action to take on closing the socket 
	def closeSocket(self):
		try:
			client.shutdown(socket.SHUT_RDWR)
			client.close()
		except Exception, msg:
			#force close on an exception
			wx.CallAfter(self.parent.socketClosed,wx.EVT_CLOSE,msg)
#thread to run an external program			
class ProgramThread(threading.Thread):
	#initializer that takes parent and program name (and kw/args) as input
	def __init__(self,parent,value):
		threading.Thread.__init__(self)
		self.parent = parent
		self.program=value.split()
	#function to end the program before stopping the thread
	def stop(self):
		#I think I'm doing dome double-duty with this funciton and onthreadended...I still think this is true
		
		if GTK:
		#the GTK machines require a different KILL process than the MSW
			if app.frame.seconds2Expire is not False:
			#if there is still time on the timer, then don't close the external program, just hide it and resurface the GUI
				app.frame.timeFrame.Hide()
				app.frame.timeFrame.onClose()
				app.frame.Show()
				app.frame.Raise()
			else:
			#if it is false, that means the timer has expired. Shut down the program, release the user ID from the DB
				app.frame.socketWorker.sendEvent(["EVT_RELEASE",machineName,app.frame.userIDnumber,"False"])
				#complicated way to kill the program and any subthreads it may have spawned. It's not clean but it's the best I found
				p = subprocess.Popen(['ps','-A'],stdout=subprocess.PIPE)
				out, err = p.communicate()
				for line in out.splitlines():
				#need to kill all instances of python (except the main GUI thread which is app.pid)
				#and all instances of makerware or cura (depending on the machine)
					if "python" in line:
						pid = int(line.split(None,1)[0])
						if pid != app.pid:
							os.kill(pid,signal.SIGKILL)
					elif "cura" in line:
						pid = int(line.split(None,1)[0])
						os.kill(pid,signal.SIGKILL)
					elif "makerware" in line:
						pid = int(line.split(None,1)[0])
						os.kill(pid,signal.SIGKILL)
		else:
		#MSW is more straightforward (for a change) though I'm having an issue with an MSW error returned on force kill
			if app.frame.seconds2Expire is not False:
				app.frame.timeFrame.Hide()
				app.frame.timeFrame.onClose()
				app.frame.Show()
				app.frame.Raise()
			else:
				app.frame.socketWorker.sendEvent(["EVT_RELEASE",machineName,app.frame.userIDnumber,"False"])
				wx.Kill(self.process.pid,wx.SIGKILL)

	def run(self):
	#required function that is called by threading.start() 
		self.process = subprocess.Popen(self.program)
		#this command will wait for the thread to terminate, when it does it proceeds to callAfter
		self.process.wait()
		wx.CallAfter(self.parent.OnThreadEnded,wx.EVT_CLOSE)

#thread to run the xbee light towers
class LightThread(threading.Thread):
	#initializer function that takes a parent and user selection value as input
	def __init__(self,parent,value):
		threading.Thread.__init__(self)
		self.parent = parent
		self.response=value
	#not needed but may add functionality in the future
	def stop(self):
		pass
	#required function by threading.start(), light() is redundant but kept it anyway
	def run(self):
		self.light()
	#function to turn the specified light on and off 
	def light(self):
		if self.response == wx.ID_YES:
			#blink the light five times, with a one second delay
			#50 msec delay is for the latency in the xbees, multiple calls is for redundancy (radio misses sometimes)
			xbee.write("<OK>")
			# for indx in xrange(3):
				# for i in xrange(5):
					# xbee.write("<green on>")
					# time.sleep(0.05)
				# time.sleep(1)
				# for i in xrange(5):
					# xbee.write("<green off>")
					# time.sleep(0.05)
				# time.sleep(1)
		elif self.response == wx.ID_NO:
			xbee.write("<DENY>")
			# for indx in xrange(3):
				# for i in xrange(5):
					# if indx == 0:
						# xbee.write("<buzz on>")
						# time.sleep(0.05)
					# xbee.write("<red on>")
					# time.sleep(0.05)
				# time.sleep(1)
				# for i in xrange(5):
					# xbee.write("<buzz off>")
					# time.sleep(0.05)
					# xbee.write("<red off>")
					# time.sleep(0.05)
				# time.sleep(1)
	
#create the frame, inside the app, that holds the panel, and all of the functionality
#this is the main body of the GUI...everything originates from here
class MainWindow(wx.Frame):
	def __init__(self, parent, title):
		#i don't know what this does...still
		self.dirname = ' '
		
		#styling for the main frame...see wxpython documentation for further info
		styleFlags = wx.STAY_ON_TOP | wx.NO_BORDER | wx.FRAME_NO_TASKBAR
		if GTK:
			styleFlags = wx.DEFAULT_FRAME_STYLE #| wx.FRAME_NO_TASKBAR
		wx.Frame.__init__(self, parent, title = title, style=styleFlags)
		
		#initialized variables
		self.isPrinter = False #is the machine a 3d printer?
		self.isOpenAccess = False #is it open access hours?
		self.programWorker = False #has a threaded program been started? Is it still running?
		self.userIDnumber = None #user ID string
		
		#bind EVENTS to functions allow the GUI to behave interactively. In this case, closing the window call onClose()
		self.Bind(wx.EVT_CLOSE, self.OnClose)
		
		#sizers for centering the static text 
		self.mainSizer = wx.BoxSizer(wx.HORIZONTAL)
		self.layoutSizer = wx.BoxSizer(wx.VERTICAL)
		self.brandingLabel = envisionVersion
		
		#static text of the branding and version number
		self.branding = wx.StaticText(self, label = self.brandingLabel, style = wx.ALIGN_CENTRE_HORIZONTAL)
		
		#change the background based on the system...The logic here could be cleaned up
		if disabled:
		#is the machine in maintenance mode?
			if machineName.startswith('laser') or machineName.startswith("vacuum") or machineName.startswith("drill"):
				self.bmp = wx.Bitmap("maintenance.jpg")
				
			else:
				self.bmp = wx.Bitmap("maintenanceLarge.jpg")
				self.isPrinter = True
			self.brandingLabel = machineName + " is currently not working\nThank you for your patience"
			self.brandingFont = wx.Font(20, wx.DECORATIVE, wx.ITALIC, wx.LIGHT)
		elif machineName.startswith('front'):
			self.bmp = wx.Bitmap("front-desk.jpg")
			self.brandingFont = wx.Font(20, wx.DECORATIVE, wx.ITALIC, wx.BOLD)
		elif machineName.startswith('laser') or machineName.startswith("vacuum") or machineName.startswith("drill"):
			self.bmp = wx.Bitmap("touch_screen.jpg")
			self.brandingFont = wx.Font(12, wx.DECORATIVE, wx.ITALIC, wx.LIGHT)
		else:
			self.bmp = wx.Bitmap("kiosk.jpg")
			self.brandingFont = wx.Font(24, wx.DECORATIVE, wx.ITALIC, wx.LIGHT)
			self.isPrinter = True
		
		#set the GUI font after the system-type is identified 
		self.branding.SetFont(self.brandingFont)
		
		#set the branding dead-center, with some padding
		dw, dh = wx.DisplaySize()
		w, h = self.branding.GetSize()
		y = dh/2 - h/2
		borderWidth = 20
		
		if not machineName.startswith('front'):
		#front machine graphic doesn't like the padding
			self.layoutSizer.AddSpacer(y-borderWidth)
		
		#bind a function to a thread ending
		self.Bind(wx.EVT_END_PROCESS, self.OnThreadEnded)
		
		#layout stuff
		self.layoutSizer.Add(self.branding, 1, wx.ALIGN_CENTER | wx.ALL, borderWidth)
		#self.layoutSizer.AddSpacer(y-borderWidth)
		self.mainSizer.Add(self.layoutSizer, 1)
		#more layout stuff...maybe not needed now that everything is fullscreen
		self.SetSizer(self.mainSizer)
		self.Centre()
		self.Layout()
		
		#allows the background image to be set (and redrawn)
		self.SetBackgroundStyle(wx.BG_STYLE_ERASE)
		self.Bind(wx.EVT_ERASE_BACKGROUND, self.OnEraseBackground)
		

		
		#timer stuff used for 3d print charging
		self.seconds2Expire = False
		self.threadRunning = False
		if self.isPrinter:
			self.expireTimer = wx.Timer(self)
			self.Bind(wx.EVT_TIMER,self.countDown2Expire,self.expireTimer)
			pub.subscribe(self.timeListener, "timeListener")
		
		#establish a listener thread. This allows the GUI to respond to spawned processes. In this case the socket process
		pub.subscribe(self.socketListener, "socketListener")
		#create a socket instance and start it
		self.socketWorker = SocketThread(self,None)
		self.socketWorker.start()
			
		self.ShowFullScreen(True)
		#self.Show()
		
		#this is the binding that captures the key events
		#setting a panel lets me set focus inside of the app (for gtk only)
		#I need focus in the panel in order to capture the events
		#if panel ever loses focus, the program will be trapped
		#there's a bug in the MSW package that doesn't allow panels to capture keystrokes...this can be fixed by adding a frame to the panel
		#and rewriting all of the logic for the frame
		if GTK:
			self.panel = wx.Panel(self, wx.ID_ANY)
			self.panel.Bind(wx.EVT_CHAR, self.onKeyPress)
			self.panel.SetFocus()
		#MSW doesn't like key capture in panels
		elif MSW:
			self.Bind(wx.EVT_CHAR, self.onKeyPress)
			self.SetFocus()
		else:
		#Not interested in seeing how this fails on other platforms
			print "Platform not supported"
			self.Destroy()
	
	#function to listen to published messages from the timeFrame process
	def timeListener(self, timeHour=None, timeMinute=None):
		#the listener expects two strings, these are sent from the choice boxes in timeFrame
		if timeHour=="False":
		#the only way timehour can publish False is if the program was exited without the user entering a time
		#in this instance the ID should be released from the DB
			self.socketWorker.sendEvent(["EVT_RELEASE",machineName,self.userIDnumber,"False"])
		elif timeHour is not None and timeMinute is not None:
		#if both hour and minute are set, add the time (in seconds) to the countdown timer
		#and add the user, time, and machine to the DB by sending an EVT_ADD_TIME event to the socket process
			#self.seconds2Expire = datetime.timedelta(minutes=1).seconds
			self.seconds2Expire = datetime.timedelta(minutes=int(timeHour)*60+int(timeMinute)+15).seconds
			self.socketWorker.sendEvent(["EVT_ADD_TIME",machineName,self.userIDnumber,str(self.seconds2Expire)])
			
	#this functions executes the countdown timer. It's called every second and decreases the seconds2Expire variable		
	def countDown2Expire(self, event):
		if self.seconds2Expire  > 0:
		#Sets the GUI branding to indicate the machine is in use, and how much time is remaining
			self.seconds2Expire -= 1
			self.branding.SetLabel("MACHINE IN USE: " + str(datetime.timedelta(seconds=self.seconds2Expire))+'\n')
		else:
		#When the timer expires, stop the countdown timer, indicate it's stopped (by setting seconds2Expire to False)
		#Stop the program thread by calling stop(), and set the label to its default string
			self.expireTimer.Stop()
			self.seconds2Expire = False
			if self.programWorker:
				self.programWorker.stop()
			self.branding.SetLabel(self.brandingLabel)
			self.Layout() #call layout to adjust the branding "sizer" to fit the updated label
	
	#this function listens to the published messages from the socket process
	def socketListener(self, sent=None, reply=None):
	#function expects two lists of strings 
		#set variables for clarity
		command = sent[0]
		user = sent[1]
		machine = sent[2]
		machineTime = sent[3]
		
		event = reply[0]
		status = reply[1]
		statusInfo = reply[2]
		
		if status == "OK":
		#checks if the command was accepted
			self.processReply(event,statusInfo)
		elif status == "DENY":
		#checks if the command was rejected
			self.processDeny(event, statusInfo)
	
	#called after the socketlistener determines the packets were properly formed, and were accepted by the server
	def processReply(self, command, info):
		#function expects two strings: the command and the information returned by the server
		infoList = info.split("|") #split the info string into a list, delineated by | ... 
		#extraneous info is often bundled together in one string to keep the reply packet uniform
		if command == "EVT_START":
		#A start event is called to start the appropirate program in a new thread
			if infoList[0]=="FRONT":
			#Front desk doesn't have a program to thread
				pass
			else:
				self.startSelect(wx.EVT_BUTTON)
		elif command == "EVT_CHECKID":
		#checkID is called to make sure the user is in the DB and has passed all of the required certifications
			if machineName.upper().startswith("FRONT"):
			#Front desk just needs to know if the user is an admin or not
				if infoList[0] == "ADMIN":
					self.frontCheckIn("True",info)
				else:
					self.frontCheckIn("False",info)
			elif infoList[0] == "ADMIN":
			#ADMINs can put machines into and out of maintenance mode
				if disabled:
					action = self.machineStatus(False)
					return
				else:
					self.machineStart("True",info)
			else:
				self.machineStart("False",info)
		
		elif command == "EVT_ADD_TIME":
		#add time events are called when a user adds time to a 3d print, or an admin adds additional time
			if infoList[0] == "STARTED":
			#server has indicated that the printer has started
				if infoList[1] == "FREE":
				#unlikely event that the printer was started and the user wasn't charged...it may happend because of server side issues
					wx.MessageBox("Congrats! Your print is free today!\n\n","ERROR")
				else:
				#indicate the users remaining balance
					wx.MessageBox("Printer has started!\n\nYour balance is $"+infoList[1],"SUCCESS")
				#disable the choice boxes in the timeFrame to prevent a user from adding additional time
				self.timeFrame.hourTxt.Enable(False)
				self.timeFrame.minTxt.Enable(False)
				self.timeFrame.submitBtn.Enable(False)
				#update the timer in timeFrame
				self.timeFrame.warning.SetLabel(str(datetime.timedelta(seconds=app.frame.seconds2Expire)))
				self.timeFrame.Layout()
				self.timeFrame.timer2.Start(1000) #start the idle timer, as most users tend to walk away after print was submitted
			
			elif infoList[0]=="ADDED":
			#if an ADMIN added time for the user
				self.seconds2Expire += int(infoList[1])
				wx.MessageBox("Time Added\n\nBalance is $"+infoList[2],"SUCCESS")
		elif command == "EVT_END":
		#called if an ADMIN cancels a print
			self.seconds2Expire = 0
		elif command == "EVT_CHANGE_STATUS":
		#change in and out of maintenance mode
			if info == "ENABLED":
				wx.MessageBox("Machine enabled\n\n","SUCCESS")
			elif info == "DISABLED":
				wx.MessageBox("Machine taken offline\n\n","SUCCESS")
	#this function is called if the socketListener determines that the packet was processed but not approved by the server
	def processDeny(self,command, error):
		#functions expects two lists, one command and containing any relevant error messages
		now = datetime.datetime.now()
		errorList = error.split("|")
		if machineName.upper().startswith("FRONT"):
			lightWorker = LightThread(self,wx.ID_NO)
			lightWorker.start()
		if command == "EVT_CHECKID":
		#if check id fails, explain why
			if errorList[0] == "WAIVER":
				errorMsg = 'Your Responsbility Contract has expired! (>90 days)\n\nPlease log into the EnVision Portal to complete'
			elif errorList[0] == "GRAD":
				errorMsg = "Engineering Graduate Use is Restricted \n\n Please see an admin for other options on campus"
			elif errorList[0] == "CERT":
				errorMsg = "You have not completed the training for this machine!\n\nPlease log into the EnVision Portal to complete"
			else:
				errorMsg = error
		
		elif command == "EVT_CONNECT":
		#if connect fails, the machine is in maintenance mode or already in use by a student
			if error == "OFFLINE":
				errorMsg = "Machine in in maintenance mode"
				self.changeStatus(True)
			else:
				errorMsg = "Machine is currently in use"
				startTime = datetime.datetime.strptime(errorList[1], '%Y%m%d-%H:%M:%S')
				timeLeft = datetime.timedelta(seconds=int(errorList[2]))
				if startTime + timeLeft > now:
					self.seconds2Expire = ((startTime + timeLeft)-now).seconds
					#self.branding.SetFont(self.countDownFont)
					self.branding.SetLabel("MACHINE IN USE: " + str(datetime.timedelta(seconds=self.seconds2Expire))+'\n')
					self.Layout()
					self.expireTimer.Start(1000)
		elif command == "EVT_CHANGE_STATUS":
		#this shouldn't happen
			errorMessage = "Unable to take machine offline\n\n This is safe to dismiss"		
		elif command == "EVT_START":
		#if start fails, the machine is already in use by another user, or a users ID is in use on another machine
			if errorList[0] == "OCCUPIED":
				errorMsg = "This machine is being used by another user"
			if errorList[0] == "IDINUSE":
				errorMsg = "Your ID is in use on another machine"
		elif command == "EVT_RELEASE":
			if errorList[0] == "BADTIME":
				#errorMsg = "Machine is currently in use"
				startTime = datetime.datetime.strptime(errorList[1], '%Y%m%d-%H:%M:%S')
				timeLeft = datetime.timedelta(seconds=int(errorList[2]))
				if startTime + timeLeft > now:
					self.seconds2Expire = ((startTime + timeLeft)-now).seconds
					self.branding.SetLabel("MACHINE IN USE: " + str(datetime.timedelta(seconds=self.seconds2Expire))+'\n')
					self.Layout()
					self.expireTimer.Start(1000)
				return
			else:
			#this fails if the user ID has already been released from the server DB, it's not really an error, but helpful for debugging
				return
				#errorMsg = "Can't Release ID:" +error + "\n\n You can (probably) safely ignore this message"
		elif command == "EVT_ADD_TIME":
		#if add time failed, there is usually an issue with the relay system
			if errorList[0] == "THREAD":
				errorMsg = "Machine appears to be in use...server file possibly corrupt"
				self.seconds2Expire = False
			elif errorList[0] == "RELAYFAIL":
				errorMsg = "Server failed to start printer\nPlease try to submit again"
				self.seconds2Expire = False
			elif errorList[0] == "FUNDS":
			#user does not have enough funds in their account
				self.seconds2Expire = False
				if errorList[1]=="FALSE":
					errorMsg = "You have a zero balance in your account\n\nPlease use the kiosk to add funds"
				else:
					errorMsg = "You do not have adequate funds for this print\n\nBalance is $"+errorList[1]
			elif errorList[0]=="ADDED":
			#if admin tries to add additional time for user, but user does not have enough funds to cover the extra time
				errorMsg = "This User Does Not Have Enough Funds\n\nBalance is $"+errorList[1]
		elif command == "ERROR":
		#catchall 
			errorMsg = "Received Error: " + error
		elif command == "EVT_END":
		#relay issues
			errorMsg = "RELAY DID NOT RESPOND. Try Again"
		else:
		#failsafe catch-all
			errorMsg = "UNKNOWN ERROR\n\n Please see an admin"
		wx.MessageBox(errorMsg,"ERROR")
	
	#this function opens a new frame for the printer timer, and starts the countdown timer if the machine was already active
	def onOpenFrame(self):
		self.timeFrame = popupFrame(self)
		time.sleep(2)
		self.timeFrame.Show()
		if self.seconds2Expire > 0:
			self.timeFrame.timer2.Start(1000)
			self.timeFrame.Layout()
			self.timeFrame.Refresh()
	
	#checks if open access hours are open or closed, fires from a timer in init
	def openAccess(self, event):
		#checks the server db for current open access hours, result returns true or not
		self.socketWorker.sendEvent(["EVT_OPEN_ACCESS",machineName,"False","False"])
		
		if self.isopenAccess:
			self.bmp = wx.Bitmap("front-desk.jpg")
			#call lightThread to turn the red light off
			
		else:
			self.bmp = wx.Bitmap("closed.jpg")
			#call light thread to turn red light on
		
		#update the layout of the GUI with the new background
		dc = wx.ClientDC(self)
		rect = self.GetUpdateRegion().GetBox()
		dc.SetClippingRect(rect)
		dc.Clear()
		dc.DrawBitmap(self.bmp, 0, 0)
		self.Refresh()
		
		#set the timer to fire every half hour on the hour
		if self.openAccessTimer.IsOneShot():
			if now.minute > 0 and now.minute < 30:
				self.openAccessTimer.Start((30 - now.minute) * 60 * 1000, True)
				#print "next timer in " + str(30 - now.minute) + " minute"
			elif now.minute > 30 and now.minute < 60:
				self.openAccessTimer.Start((60 - now.minute) * 60 * 1000, True)
				#print "next timer in " + str(60 - now.minute) + " minutes"
			else:
				self.openAccessTimer.Start(30 * 60 * 1000)
	
	def onKeyPress(self, event):
		"""
		capture key events in the panel focus
		if ESC is pressed, ask for the escape code
		if any other key but the "start-key" ($) are captured
		ignore and print an error message
		"""
		#these variables are local because each "key press" from the card reader is read as a seperate event...
		#it doesn't need to be global, but it should at least be a class variable
		global acceptString
		global inputList
		
		#pseudo buffer for inputList
		if len(inputList) > 50:
		#if the buffer overflows, reset and return
			inputList=[]
			return
		#get the ascii value of each key
		keycode = event.GetKeyCode()
		if keycode == wx.WXK_ESCAPE:
		#if escape is pressed, ask for the escape code in a dialog box
			self.requestExit()
			return
		if keycode > 256:
		#characters outside of ascii are not accepted
			wx.MessageBox("Please Use The ID-Reader", "ERROR")
			return
		#ascii code 36 is $ and is the start and trail char of the magreader
		elif keycode == 36:
			#if present, start accepting characters into the inputList
			acceptString = True
			inputList.append(keycode)
			return
		#look for an enter key
		if acceptString:
		#acceptString is only True if string started with a $
			if keycode == wx.WXK_RETURN:
				#if return is pressed, make sure the last character is $
				if inputList[-1] == 36:
				#if True, join the character together in a string
					inputString = ''.join(chr(i) for i in inputList)
					
					#check that the string matches at least the min length, there's no check for max length 
					if len(inputString) > idLength -1:
						self.idEnter(inputString)
					else:
						wx.MessageBox("Not a Recognized ID Type", "ERROR")
				#reset the capture variables
				acceptString = False
				inputList = []
			#keep capturing characters until return is pressed (or buffer overflows)
			else:
				inputList.append(keycode)
		#ignore all strings that don't start with '$'
		else:
			wx.MessageBox("Please Use The ID-Reader", "ERROR")
		#if this isn't called, the keypress will never propogate to the GUI level
		event.Skip()
	
	#dispaly a dialog box to request a code to exit the program
	def requestExit(self):
		exitDlg = wx.PasswordEntryDialog(self, "Enter Code To Exit", "EXIT", "", wx.OK | wx.CANCEL)
		result = exitDlg.ShowModal()
		if exitDlg.GetValue() == '111999':
			exitDlg.Destroy()
			self.OnClose(wx.EVT_CLOSE)
		else:
			exitDlg.Destroy()
	
	#(re)sets the background based on the image save to self.bmp
	def OnEraseBackground(self, evt):
		dc = evt.GetDC()
		if not dc:
			dc = wx.ClientDC(self)
			rect = self.GetUpdateRegion().GetBox()
			dc.SetClippingRect(rect)
		dc.Clear()
		dc.DrawBitmap(self.bmp, 0, 0)
	
	#after the input string has been accepted, this converts the magstripe string to the format used by UCSD
	def idEnter(self, idInput):
		print idInput
		idString = ""
		if (idInput.startswith('$') and idInput.endswith('$')):
		#check once more if the string is correclty formatted
			idChars = list(idInput)
			if idChars[2] == '9':
			#magstripe reads a '09' for students, replace this with a 'A' per UCSD standards
				idChars[2]='A'
			if idChars[2] == '7':
			#magstripe reads '07' for international students, replace with something
				idChars[2]='U'
				idChars[3]='0'
				for i in range(2,idLength):
					idString = idString + idChars[i]
			else:	
				for i in range(2,idLength):
					idString = idString + idChars[i]

			self.userIDnumber = idString #set the current user to this ID string
			print self.userIDnumber
			self.socketWorker.sendEvent(["EVT_CHECKID",machineName,self.userIDnumber,"False"]) #check the ID record on the server
		else:
			return

	#allows an admin to put a machine into maintenace mode (or change the timer on a 3d printer)
	# I should change the calls to changeStatus() to occur after the EVT reply from the server...
	def machineStatus(self,enabled):
		if enabled:
		#if the machine is currently enabled (not in maintenance mode)
			if self.seconds2Expire:
			#if a print is currently in progress
				agreeMessage = "You can MODIFY the timer, or DISABLE the machine"
				agreeDlg = wx.MessageDialog(self, agreeMessage, "ADMIN ACCESS", wx.YES | wx.CANCEL | wx.NO | wx.CENTRE)
				agreeDlg.SetYesNoCancelLabels("DISABLE", "MODIFY", "CANCEL")
				result = agreeDlg.ShowModal()
				agreeDlg.Close()
				agreeDlg.Destroy()
				if result == wx.ID_YES:
				#yes indicates the admin wants to disable the machine
					self.changeStatus(True)
					self.socketWorker.sendEvent(["EVT_CHANGE_STATUS",machineName,self.userIDnumber,str(not enabled)])
				elif result == wx.ID_NO:
				#no indicates the admin wants to change the printer timer
					self.changeTimer()
				elif result == wx.ID_CANCEL:
				#cancel is cancel
					pass
			else:
			#if the machine is enabled and there is NOT a print in progress
				agreeMessage = "Would you like to disable this machine?"
				agreeDlg = wx.MessageDialog(self, agreeMessage, "ADMIN ACCESS", wx.YES_NO | wx.ICON_EXCLAMATION | wx.CENTRE)
				result = agreeDlg.ShowModal()
				agreeDlg.Close()
				agreeDlg.Destroy()
				if result == wx.ID_YES:
					self.changeStatus(True)
					self.socketWorker.sendEvent(["EVT_CHANGE_STATUS",machineName,self.userIDnumber,str(not enabled)])
				elif result == wx.ID_NO:
					pass
		elif not enabled:
		#if the machine is already disabled, offer to re-enable it
			agreeMessage = "Would you like to re-enable this machine?"
			agreeDlg = wx.MessageDialog(self, agreeMessage, "ADMIN ACCESS", wx.YES_NO | wx.ICON_EXCLAMATION | wx.CENTRE)
			result = agreeDlg.ShowModal()
			agreeDlg.Close()
			agreeDlg.Destroy()
			if result == wx.ID_YES:
				self.changeStatus(False)
				self.socketWorker.sendEvent(["EVT_CHANGE_STATUS",machineName,self.userIDnumber,str(not enabled)])
			elif result == wx.ID_NO:
					pass
	
	#this function tells the server to put the machine in maintenance mode (it updates the DB), and changes the background accordingly
	def changeStatus(self,enabled):
		global disabled
		if enabled:
		#if machine is currently enabled (not in maintenace mode) take it offline
			disabled = True
			#change the background to the maintenace background
			if machineName.startswith('laser') or machineName.startswith("vacuum") or machineName.startswith("drill"):
				self.bmp = wx.Bitmap("maintenance.jpg")
			else:
				self.bmp = wx.Bitmap("maintenanceLarge.jpg")
			#change the label to indicate the machine is down
			brandingLabel = machineName + " is currently not working\nThank you for your patience"
			brandingFont = wx.Font(20, wx.DECORATIVE, wx.ITALIC, wx.LIGHT)
		elif not enabled:
		#if the machine is currently disabled, put it back online
			disabled = False
			brandingLabel = envisionVersion
			if machineName.startswith('laser') or machineName.startswith("vacuum") or machineName.startswith("drill"):
				self.bmp = wx.Bitmap("touch_screen.jpg")
				brandingFont = wx.Font(12, wx.DECORATIVE, wx.ITALIC, wx.LIGHT)
			else:
				self.bmp = wx.Bitmap("kiosk.jpg")
				brandingFont = wx.Font(24, wx.DECORATIVE, wx.ITALIC, wx.LIGHT)
			#branding = wx.StaticText(self, label = brandingLabel, style = wx.ALIGN_CENTRE_HORIZONTAL)
		
		#update the background...can probably call OnEraseBackground() instead
		dc = wx.ClientDC(self)
		rect = self.GetUpdateRegion().GetBox()
		dc.SetClippingRect(rect)
		dc.Clear()
		dc.DrawBitmap(self.bmp, 0, 0)
		self.branding.SetFont(brandingFont)
		self.branding.SetLabel(brandingLabel)
		#self.branding.SetStyle(wx.ALIGN_CENTRE_HORIZONTAL)
		self.Layout()
		self.Refresh()
		return(True)
	
	#function called if admin wants to modify the printer timer
	def changeTimer(self):
		timerMessage = "ADD / CANCEL TIMER"
		#admin can cancel the printer or add up to an hour in 15 minute increments...intentionally made difficult to add a lot of time
		timerDlg = wx.SingleChoiceDialog(self, timerMessage, "ADMIN ACCESS", ["CANCEL TIMER", "ADD 15 MINUTES", "ADD 30 MINUTES","ADD 60 MINUTES"],wx.CHOICEDLG_STYLE)
		timerDlg.ShowModal()
		timerDlg.Close()
		timerDlg.Destroy()
		result = timerDlg.GetSelection()
		
		#check the choice made. Currently if an admin chooses to do nothing (selecting the cancel BUTTON) it stops the print. Not ideal
		if result == 0:
		#cancel  timer
			self.socketWorker.sendEvent(["EVT_END",machineName,self.userIDnumber,"False"])
		elif result > 0:
		#convert string to seconds
			addedTime = int(timerDlg.GetStringSelection()[4:6])*60
			self.socketWorker.sendEvent(["EVT_ADD_TIME",machineName,self.userIDnumber,str(addedTime)])

	#called after thes server checks and accepts a user ID on the front desk		
	def frontCheckIn(self,admin,info):
	#logging of usage is done server side
		agreeMessage = "I declare that\n\n--"+self.userIDnumber + " is my ID \n--I have read and signed my Responsibility Contract\n--I understand the risks of the EnVision Maker Studio"
		if admin=="True":
			agreeDlg = wx.MessageDialog(self, agreeMessage, "TERMS OF USE", wx.YES_NO | wx.CANCEL | wx.CENTRE)
			agreeDlg.SetYesNoCancelLabels("YES", "NO", "ADMIN")
		else:
			agreeDlg = wx.MessageDialog(self, agreeMessage, "TERMS OF USE", wx.YES_NO | wx.CENTRE)
		result = agreeDlg.ShowModal()
		agreeDlg.Close()
		agreeDlg.Destroy()
		if result == wx.ID_CANCEL:
			if self.isOpenAccess:
				agreeDlg = wx.MessageDialog(self, "Would you like to close the check-in?", wx.YES_NO | wx.CENTRE | wx.ICON_QUESTION)
			else:
				agreeDlg = wx.MessageDialog(self, "This will open the Kiosk for Check-in. Continue?", wx.YES_NO | wx.CENTRE | wx.ICON_QUESTION)
			result = agreeDlg.ShowModal()
			agreeDlg.Close()
			agreeDlg.Destroy()
			if result == wx.ID_YES:
				if self.isOpenAccess:
					self.isOpenAccess = False
					self.openAccess(wx.EVT_TIMER)
				else:
					self.isOpenAccess = True
					self.openAccess(wx.EVT_TIMER)
		elif result == wx.ID_NO:
		#user declined to accept the terms, deny access and fire the red light
			lightWorker = LightThread(self,result)
			lightWorker.start()
		else:
		#user accepted the terms, allow access, fire the green light, and send EVT_START to the server to update the log
			lightWorker = LightThread(self,result)
			lightWorker.start()
			self.socketWorker.sendEvent(["EVT_START",machineName,self.userIDnumber,info])
	
	#called after the server checks and accepts the user ID for a machine
	def machineStart(self,admin, info):
	#logging of usage is done server side
		agreeMessage = "I declare that \n\n-- "+self.userIDnumber + " is my ID \n-- I am trained to use this machine"
		if admin=="True":
			agreeDlg = wx.MessageDialog(self, agreeMessage, "TERMS OF USE", wx.YES_NO | wx.CANCEL | wx.CENTRE)
			agreeDlg.SetYesNoCancelLabels("YES", "NO", "ADMIN")
		else:
			agreeDlg = wx.MessageDialog(self, agreeMessage, "TERMS OF USE", wx.YES_NO | wx.CENTRE)
		result = agreeDlg.ShowModal()
		agreeDlg.Close()
		agreeDlg.Destroy()
		if result == wx.ID_CANCEL and admin=="True":
			self.machineStatus(True)
			return
		elif result == wx.ID_NO:
			wx.MessageBox("Use is NOT authorized", "ERROR!")
		else:
			self.socketWorker.sendEvent(["EVT_START",machineName,self.userIDnumber,info])
	
	#define various reasons why a user ID was denied and display the appropriate message
	def restrictedID(self,reason):
		if (reason == 'expired'):
			errorMessage = 'Your Certification has expired! (>90 days)\n\nPlease redo Responsbility Contract'
		elif (reason == 'grad'):
			errorMessage = 'Engineering Graduate Use is Restricted. Please see an admin for other options on campus'
		elif (reason == 'inuse'):
			errorMessage = 'This Machine is being used by another User. \n\n Please wait for print to complete'
		elif (reason.startswith('laser')):
			errorMessage = 'Laser Cutter Training is not complete\n\nAccess is RESTRICTED\n\nPlease see an administrator'
		elif (reason.startswith('time')):
			errorMessage = 'Laser Cutter is only operational before 9pm\n\nAccess is RESTRICTED'
		elif (reason.startswith('vacuum')):
			errorMessage = 'Vacuum Forming Training is not complete\n\nAccess is RESTRICTED\n\nPlease see an administrator'
		elif (reason.startswith('drill')):
			errorMessage = 'Drill Press Training is not complete\n\nAccess is RESTRICTED\n\nPlease see an administrator'
		elif (reason.startswith('quota')):
			errorMessage = 'You have been SUSPENDED from the EnVision Maker Studio\n\nPlease see an administrator if this is an error'
		elif (reason.startswith('maker')):
			errorMessage = 'MakerBot Training is not complete\n\nAccess is RESTRICTED\n\nPlease visit envision.ucsd.edu'
		elif (reason.startswith('taz')):
			errorMessage = 'Lulzbot Training is not complete\n\nAccess is RESTRICTED\n\nPlease visit envision.ucsd.edu'
		elif (reason.startswith('up')):
			errorMessage = 'UP! Mini Training is not complete\n\nAccess is RESTRICTED\n\nPlease visit envision.ucsd.edu'
		elif (reason.startswith('front') or reason == 'not found'):
			errorMessage = 'Responsibility Contract is not complete\n\nAccess is RESTRICTED\n\nPlease visit envision.ucsd.edu'
		else:
		#catch-all
			errorMessage = 'Unknown Error\n\nPlease see an administrator'
		errorDlg = wx.MessageDialog(self, errorMessage, "ERROR", wx.OK | wx.ICON_ERROR)
		result = errorDlg.ShowModal()
		if result == wx.ID_OK:
			errorDlg.Destroy()
	
	#selects the appropriate program to run in a new thread once machineStart has completed
	def startSelect(self, event):
		if (machineName.startswith('maker')):
			if MSW:
				program = r"C:\Program Files (x86)\MakerBot\MakerWare\makerware.exe"
			else:
				program = 'makerware'
		elif (machineName.startswith('up')):
			program = r"C:\Program Files\UP Studio\X64\UPStudio.exe"
		elif (machineName.startswith('taz')):
			program = 'cura'
		elif (machineName.startswith('laser')):
			program = '/home/e4ms/job_tracking/timer.py ' +machineName
		elif (machineName.startswith('vacuum')):
			program = '/home/e4ms/job_tracking/timer.py ' +machineName
		elif (machineName.startswith('drill')):
			program = '/home/e4ms/job_tracking/drill.py'
		else:
		#catch-all...don't want to run a program for a machine that isn't defined
			errorDlg = wx.MessageDialog(self, "No Executables Defined For This Machine", "ERROR", wx.OK | wx.ICON_ERROR)
			result = errorDlg.ShowModal()
			if result == wx.ID_OK:
				errorDlg.Destroy()
			return
		
		#hide the main GUI
		self.Hide()
		
		if not self.threadRunning:
		#if a thread hasn't previously started (it's not just hiding) start a new thread 
			self.threadRunning = True
			self.programWorker = ProgramThread(self,program)
			self.programWorker.start()
			if self.isPrinter:
			#if machine is a printer, open the timer dialog with the program. onOpenFrame will place the dialog appropriately
				self.onOpenFrame()
		else:
		#if a thread is running, simply pull it to the foreground
		#I think that the start call for timer1 is causing the machine to countdown by 2 seconds. Commented for now, may need to fix
			self.timeFrame.Show()
			self.expireTimer.Stop()
			self.timeFrame.timer2.Start(1000)
			self.timeFrame.timer.Start(1000)
	
	#called after the thread has successfully ended, either by a user exit, or by the printer countdown ending
	def OnThreadEnded(self, event):
		self.threadRunning = False #let the GUI know that the thread is done
		if self.isPrinter:
		#if a printer, close the timeFrame
			self.timeFrame.Hide()
			self.timeFrame.onClose()
			if self.seconds2Expire is False:
			#if the timer never started, release the ID and print a debug message
				print "ended thread successfully with no user input"
				self.socketWorker.sendEvent(["EVT_RELEASE",machineName,self.userIDnumber,"False"])
			elif self.seconds2Expire == 0 :
			#if the timer expired, the ID was already release. Simply set seconds2Expire to False
				print "ended thread successfully after countdown expired"
				self.seconds2Expire = False
		else:
		#if not a printer, just release the ID
			self.socketWorker.sendEvent(["EVT_RELEASE",machineName,self.userIDnumber,"False"])
		#Bring GUI to foreground
		self.Show()
		self.Raise()
		
		#same GTK MSW behavior. Can fix with some tweaking
		if GTK:
			self.panel.SetFocus()
		else:
			self.SetFocus()
	#this is called if the socket is prematurely closed. Sometimes fires before the system has initialized
	def socketClosed(self, event, errorMsg):
		self.Show()
		self.Raise()
		errorMsg = str(errorMsg)
		errorDlg = wx.MessageDialog(self, "Connection to SERVER failed!\n\n"+errorMsg+"\n\nPlease see an Administrator", "ERROR", wx.OK | wx.ICON_ERROR | wx.CENTER)
		result = errorDlg.ShowModal()
		if result == wx.ID_OK:
			errorDlg.Destroy()
	#called on a GUI exit, cleans up some variables and kills any stray threads
	def OnClose(self, event):
		print ("Closing up...")
		if self.threadRunning:
			self.programWorker.stop()
		try:
			self.timeFrame.Destroy()
		except:
			pass
			
		self.Destroy()	

#main class for the application		
class EnVisionApp(wx.App):
    def OnInit(self):
		#title of the Application
		self.name = "EnVision-Tracker"
		#Check that the application isn't already running...it could get hairy if it was
		self.instance = wx.SingleInstanceChecker(self.name)
		if self.instance.IsAnotherRunning():
		#if another instance is running, exit
			wx.MessageBox("Another instance is running", "ERROR")
			return False
		self.frame = MainWindow(None, envisionVersion)
		self.frame.Show()
		self.frame.SetFocus()
		#get the application PID...used for killing threads and record keeping
		self.pid = os.getpid()
		with open('taskPID.txt','wb+') as pidFile:
		#saved in a text file for the server side update script. This allows the server to kill the process and spawn a new application
		#after updating the code
			pidFile.write(str(os.getpid())+'\n')
		#I don't remember why I need to see if socketworker exists yet, but this works
		try:
			self.frame.socketWorker
		except Exception as e:
			#print e
			pass
		else:
			self.frame.socketWorker.sendEvent(["EVT_CONNECT",machineName,"False","False"])
		return True
#create the application instance
app = EnVisionApp(False)
#start the GUI 
app.MainLoop()
