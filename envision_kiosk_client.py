#!/usr/bin/env python
# -*- coding: UTF-8 -*-

import wx, threading, datetime, time
from wx.lib.pubsub import pub 
import socket #communicate, via a socket, to external (or local!) server
import wx.lib.agw.pybusyinfo as PBI
import serial, serial.tools.list_ports


if wx.Platform == "__WXMSW__":
	MSW = True
	GTK = False
else:
	GTK = True
	MSW = False

VERSION = "400"
MINIMUMFONTSIZE = 4
NUMPRINTERS = 16
#SERVERADDRESS = 'localhost'
SERVERADDRESS = '192.168.111.111'
#SERVERPORT = "9000"
SERVERPORT = "6969"
MACHINENAME = socket.gethostname().upper()
#MACHINENAME = "PRINTER_KIOSK"
#MACHINENAME = "LAPTOP_CHECKOUT_01"
MAXPRINTLENGTH = 5
envisionVersion = "\nEnVision Arts & Engineering Maker Studio\n-- "+MACHINENAME.split("_")[0]+" Control (v. " +VERSION + ") --\n"
acceptString = False 
#stores keyboard characters as they come in
inputList = []
#standard UCSD id length, including leading and trailing '$' from mag-reader
idLength = 11
IDLETIME = 30000

PORTSAVAIL = list(serial.tools.list_ports.comports())
for port in PORTSAVAIL:
	print port.description
	if "ARDUINO" in port.description.upper():
		ARDUINO = serial.Serial(port.device, 9600)
	elif "CP210" in port.description.upper():
		ARDUINO = serial.Serial(port.device, 9600)


class idleFrame(wx.Frame):
	def __init__(self,parent):
		"""Constructor"""
		wx.Frame.__init__(self, parent, style= wx.STAY_ON_TOP | wx.NO_BORDER | wx.FRAME_NO_TASKBAR | wx.FRAME_FLOAT_ON_PARENT, title="More Time?",size=(400,250))
		#wx.Dialog.__init__(self,parent,style= wx.STAY_ON_TOP, title = "MORE TIME?", size = (400,200))
		panel = wx.Panel(self,style=wx.SUNKEN_BORDER,size=(400,250))
		self.parent = parent
		self.idleMessage = "Do you need more time?\nProgram will exit in"
		self.idleText = wx.StaticText(panel,label=self.idleMessage)
		#how many seconds to give the user to decide if they need more time
		self.idleMessageTime = 15
		self.timeText = wx.StaticText(panel,label=str(self.idleMessageTime)+" seconds")
		self.timeFont = wx.Font(20,wx.FONTFAMILY_SWISS,wx.FONTSTYLE_NORMAL,wx.FONTWEIGHT_BOLD)
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
		#self.EndModal(0)
		self.MakeModal(False)
		self.Destroy()
		self.idleTimer.Stop()
		
		if app.frame.activeInput:
			app.frame.activeInput = False
			app.frame.timeInputFrame.MakeModal(False)
			app.frame.timeInputFrame.Destroy()
			#app.frame.timeInputFrame.onClose(wx.EVT_CLOSE)
		if app.signOnFrame.adminMode:
			if app.adminFrame.activeInput:
				app.adminFrame.activeInput = False
				app.adminFrame.inputFrame.MakeModal(False)
				app.adminFrame.inputFrame.Destroy()
			app.adminFrame.Hide()
			app.signOnFrame.adminMode = False
		app.frame.HideSelf()

		
	def onYes(self,event):
	#is user needs more time, restart the timer in timeFrame
		app.frame.inactiveCount = 0
		app.frame.timer.Start(IDLETIME)
		self.MakeModal(False)
		if app.frame.activeInput:
			app.frame.timeInputFrame.MakeModal(True)
		elif app.signOnFrame.adminMode:
			if app.adminFrame.activeInput:
				app.adminFrame.inputFrame.MakeModal(True)

		self.idleTimer.Stop()
		self.Destroy()

class SimplePopupFrame(wx.Frame):
	def __init__(self,parent, machine):
		"""Constructor"""
		wx.Frame.__init__(self, parent, style=wx.STAY_ON_TOP | wx.NO_BORDER | wx.FRAME_NO_TASKBAR |wx.FRAME_FLOAT_ON_PARENT, title="Popup Frame",size=(800,400))
		#wx.Dialog.__init__(self,parent,style=wx.STAY_ON_TOP | wx.NO_BORDER | wx.FRAME_NO_TASKBAR |wx.FRAME_FLOAT_ON_PARENT,title="Popup Frame", size = (800,400))
		self.panel = wx.Panel(self,style=wx.SUNKEN_BORDER,size=(800,400))
		self.parent = parent
		self.machine = machine
		msg = "* LAPTOP CHECKOUT *"
		msg3 = "LOCKER WILL OPEN AFTER SUBMISSION"
		self.instructions = wx.StaticText(self.panel, label=msg)
		#instructions.SetForegroundColour((255,0,0))
		#information = wx.StaticText(self.panel, label=msg2, style=wx.ALIGN_CENTRE_HORIZONTAL)
		self.warning = wx.StaticText(self.panel, label=msg3, style=wx.ALIGN_CENTRE_HORIZONTAL)
		self.warningFont = wx.Font(20,wx.FONTFAMILY_SWISS,wx.FONTSTYLE_NORMAL,wx.FONTWEIGHT_BOLD)
		self.warning.SetFont(self.warningFont)
		self.instructions.SetFont(self.warningFont)
		#control the number of hours allowed with a global variable
		self.maxTime = MAXPRINTLENGTH
		
		#hours = wx.StaticText(self.panel,label="HOURS")
		#minutes = wx.StaticText(self.panel, label="MINUTES")
		#self.hourTxt = wx.Choice(self.panel, choices=[str(x) for x in range(0,self.maxTime + 1)])
		self.font = self.warning.GetFont()
		self.font.SetPointSize(32)
		#self.hourTxt.SetFont(self.font)
		#15 minute increments
		#self.minTxt = wx.Choice(self.panel, choices=['00','15','30','45'])
		#self.minTxt.SetFont(self.font)
		self.submitBtn = wx.Button(self.panel, label=" BORROW ")
		self.cancelBtn = wx.Button(self.panel, label=" CANCEL ")
		self.optionalBtn = wx.Button(self.panel, label=" RETURN ")
		
		#available buttons to the user
		self.submitBtn.Bind(wx.EVT_BUTTON, self.onEnter)
		self.submitBtn.SetFont(self.font)
		self.cancelBtn.Bind(wx.EVT_BUTTON, self.onClose)
		self.cancelBtn.SetFont(self.font)
		self.optionalBtn.SetFont(self.font)
		self.optionalBtn.Bind(wx.EVT_BUTTON,self.onReturn)
		
		#self.hourTxt.Bind(wx.EVT_CHOICE, self.onChoice)
		#self.minTxt.Bind(wx.EVT_CHOICE, self.onChoice)
		
		#self.Bind(wx.EVT_CLOSE,self.onClose)
		
		
		#sizer layout
		self.sizerVert = wx.BoxSizer(wx.VERTICAL)
		#self.sizerHor = wx.BoxSizer(wx.HORIZONTAL)
		self.sizerHor2 = wx.BoxSizer(wx.HORIZONTAL)
		self.sizerHor3 = wx.BoxSizer(wx.HORIZONTAL)
		flags = wx.ALL|wx.CENTER
		#self.sizerHor.Add(self.hourTxt, 1, flags, 5)
		#self.sizerHor.Add(hours,0,flags,5)
		#self.sizerHor.Add(self.minTxt, 1, flags, 5)
		#self.sizerHor.Add(minutes,0,flags,5)
		self.sizerHor2.AddStretchSpacer()
		self.sizerHor2.Add(self.submitBtn, 1, wx.TOP | wx.BOTTOM | wx.CENTER, 20)
		self.sizerHor2.AddStretchSpacer()
		self.sizerHor2.Add(self.optionalBtn, 1, wx.TOP | wx.BOTTOM | wx.CENTER, 20)
		self.sizerHor2.AddStretchSpacer()
		self.sizerHor2.Add(self.cancelBtn, 1, wx.TOP | wx.BOTTOM | wx.CENTER, 20)
		self.sizerHor2.AddStretchSpacer()
		self.sizerVert.AddStretchSpacer()
		self.sizerVert.Add(self.instructions, 0, flags, 10)
		self.sizerVert.AddStretchSpacer()
		#self.sizerVert.Add(self.sizerHor,0,flags,5)
		#self.sizerVert.Add(self.submitBtn, 0, flags, 5)
		self.sizerVert.Add(self.sizerHor2,1,flags|wx.EXPAND,5)
		self.sizerVert.AddStretchSpacer()
		self.sizerVert.Add(self.sizerHor3,1,flags|wx.EXPAND,5)
		self.sizerVert.AddStretchSpacer()
		#self.sizerVert.Add(information, 0, flags, 10)
		self.sizerVert.Add(self.warning, 0, flags, 10)
		self.sizerVert.AddStretchSpacer()
		
		#self.minTxt.Enable(False)
		#self.submitBtn.Enable(False)
		self.optionalBtn.Enable(False)
		
		#self.SetBackgroundColour('#cfe8ff')
		self.panel.SetBackgroundColour('sky blue')
		self.SetSizer(self.sizerVert)
		self.alignToCenter(self)
		self.Layout()
	
	#align the print time frame to the bottom right of the screen...this seems to be the least obstrusive
	def alignToCenter(self,window):
	#set the window dead-center of the screen
		dw, dh = wx.DisplaySize()
		w, h = window.GetSize()
		x = dw/2 - w/2
		y = dh/2 - h/2
		window.SetPosition((x,y))
		#print dw, dh, w, h, x, y
	
	#makes sure all timers are cancelled on close and set the GUI to lock if a user has started a print
	def onClose(self,event):
		if app.frame.activeInput:
			app.frame.activeInput = False
			app.frame.Raise()
		elif app.signOnFrame.adminMode:
			if app.adminFrame.activeInput:
				app.adminFrame.activeInput = False
				app.adminFrame.Raise()
		self.MakeModal(False)
		self.Hide()
	
	
	def onReturn(self,event):
		app.frame.timer.Stop()
		btn = event.GetEventObject()
		btnLabel = btn.GetLabel()
		agreeDlg = wx.MessageDialog(self, "Please make sure door locks after return\n\nClick OK to proceed", "PROCEED?", wx.OK | wx.CANCEL)
		result = agreeDlg.ShowModal()
		agreeDlg.Close()
		agreeDlg.Destroy()
		if result == wx.ID_CANCEL:
			app.frame.timer.Start()
		elif result == wx.ID_OK:
			app.frame.socketWorker.sendEvent(["EVT_RETURN",self.machine,app.signOnFrame.userIDnumber,"False"])
	
	#action to take on submit button
	def onEnter(self, event):
		#should probably change this to reflect how much the print is going to cost
		app.frame.timer.Stop()
		btn = event.GetEventObject()
		btnLabel = btn.GetLabel()
		agreeDlg = wx.MessageDialog(self, "You will be responsible for all damages and losses\n\nClick OK to agree", "PROCEED?", wx.OK | wx.CANCEL)
		result = agreeDlg.ShowModal()
		agreeDlg.Close()
		agreeDlg.Destroy()
		if result == wx.ID_CANCEL:
			app.frame.timer.Start()
		elif result == wx.ID_OK:
			app.frame.socketWorker.sendEvent(["EVT_START",self.machine,app.signOnFrame.userIDnumber,"|".join(["FALSE",app.signOnFrame.major,app.signOnFrame.level])])
	
	def killPrinter(self,event):
		app.adminFrame.socketWorker.sendEvent(["EVT_END",self.machine,app.signOnFrame.userIDnumber,"False"])
		self.onClose(wx.EVT_BUTTON)
	
	def AdminTime(self,event):
		app.adminFrame.socketWorker.sendEvent(["EVT_ADD_TIME",self.machine,app.signOnFrame.userIDnumber,"ADMIN"])
		self.onClose(wx.EVT_BUTTON)
	
	def StatusChange(self,event):
		#print "status change"
		for machineNum, machine in enumerate(app.frame.bitmap_buttons):
			machineName = machine.sizer.GetStaticBox().GetLabel()
			if machineName == self.machine:
				if app.frame.bitmap_buttons[machineNum].status == "ENABLED":
					app.adminFrame.socketWorker.sendEvent(["EVT_STATUS",self.machine,app.signOnFrame.userIDnumber,"FALSE"])
				elif app.frame.bitmap_buttons[machineNum].status == "DISABLED":
					app.adminFrame.socketWorker.sendEvent(["EVT_STATUS",self.machine,app.signOnFrame.userIDnumber,"TRUE"])
				break
		self.onClose(wx.EVT_BUTTON)
	def LockerOpen(self,event):
		app.frame.timer.Stop()
		solenoid = str((int(self.machine[-2:])-1) - ((int(app.lockerNumber) - 1) * 16)) + '\n'
		machineLocker = str(int(self.machine[-2:])-1)+'\n'
		try:
			ARDUINO.write(solenoid)
		except Exception as e:
			print e
			message = "Solenoid failed...please try again"
			success = False
		else:
			message = self.machine + " OPENED!\n\nPlease remember to close the door"
			success = True
		successDlg = wx.MessageDialog(self, message, "SUCCESS", wx.OK | wx.CENTRE)
		result = successDlg.ShowModal()
		successDlg.Close()
		successDlg.Destroy()
		if result == wx.ID_OK:
			app.frame.timer.Start()
			self.onClose(wx.EVT_BUTTON)
		return
	def ReleaseID(self,event):
		app.adminFrame.socketWorker.sendEvent(["EVT_RELEASE",self.machine,app.signOnFrame.userIDnumber,"TRUE"])
class popupFrame(wx.Frame):
	def __init__(self,parent, machine):
		"""Constructor"""
		wx.Frame.__init__(self, parent, style=wx.STAY_ON_TOP | wx.NO_BORDER | wx.FRAME_NO_TASKBAR |wx.FRAME_FLOAT_ON_PARENT, title="Popup Frame",size=(800,400))
		#wx.Dialog.__init__(self,parent,style=wx.STAY_ON_TOP | wx.NO_BORDER | wx.FRAME_NO_TASKBAR |wx.FRAME_FLOAT_ON_PARENT,title="Popup Frame", size = (800,400))
		self.panel = wx.Panel(self,style=wx.SUNKEN_BORDER,size=(800,400))
		self.parent = parent
		self.machine = machine
		msg = "* Enter the Duration of Your Print *"
		msg3 = "PRINTER WILL TURN ON AFTER SUBMISSION"
		self.instructions = wx.StaticText(self.panel, label=msg)
		#instructions.SetForegroundColour((255,0,0))
		#information = wx.StaticText(self.panel, label=msg2, style=wx.ALIGN_CENTRE_HORIZONTAL)
		self.warning = wx.StaticText(self.panel, label=msg3, style=wx.ALIGN_CENTRE_HORIZONTAL)
		self.warningFont = wx.Font(20,wx.FONTFAMILY_SWISS,wx.FONTSTYLE_NORMAL,wx.FONTWEIGHT_BOLD)
		self.warning.SetFont(self.warningFont)
		self.instructions.SetFont(self.warningFont)
		#control the number of hours allowed with a global variable
		self.maxTime = MAXPRINTLENGTH
		
		hours = wx.StaticText(self.panel,label="HOURS")
		minutes = wx.StaticText(self.panel, label="MINUTES")
		self.hourTxt = wx.Choice(self.panel, choices=[str(x) for x in range(0,self.maxTime + 1)])
		self.font = self.hourTxt.GetFont()
		self.font.SetPointSize(32)
		self.hourTxt.SetFont(self.font)
		#15 minute increments
		self.minTxt = wx.Choice(self.panel, choices=['00','15','30','45'])
		self.minTxt.SetFont(self.font)
		self.submitBtn = wx.Button(self.panel, label=" SUBMIT ")
		self.cancelBtn = wx.Button(self.panel, label=" CANCEL ")
		self.optionalBtn = wx.Button(self.panel, label=" ----- ")
		
		#available buttons to the user
		self.submitBtn.Bind(wx.EVT_BUTTON, self.onEnter)
		self.submitBtn.SetFont(self.font)
		self.cancelBtn.Bind(wx.EVT_BUTTON, self.onClose)
		self.cancelBtn.SetFont(self.font)
		self.optionalBtn.SetFont(self.font)
		
		self.hourTxt.Bind(wx.EVT_CHOICE, self.onChoice)
		self.minTxt.Bind(wx.EVT_CHOICE, self.onChoice)
		
		#self.Bind(wx.EVT_CLOSE,self.onClose)
		
		
		#sizer layout
		self.sizerVert = wx.BoxSizer(wx.VERTICAL)
		self.sizerHor = wx.BoxSizer(wx.HORIZONTAL)
		self.sizerHor2 = wx.BoxSizer(wx.HORIZONTAL)
		self.sizerHor3 = wx.BoxSizer(wx.HORIZONTAL)
		flags = wx.ALL|wx.CENTER
		self.sizerHor.Add(self.hourTxt, 1, flags, 5)
		self.sizerHor.Add(hours,0,flags,5)
		self.sizerHor.Add(self.minTxt, 1, flags, 5)
		self.sizerHor.Add(minutes,0,flags,5)
		self.sizerHor2.AddStretchSpacer()
		self.sizerHor2.Add(self.submitBtn, 1, wx.TOP | wx.BOTTOM | wx.CENTER, 20)
		self.sizerHor2.AddStretchSpacer()
		self.sizerHor2.Add(self.optionalBtn, 1, wx.TOP | wx.BOTTOM | wx.CENTER, 20)
		self.sizerHor2.AddStretchSpacer()
		self.sizerHor2.Add(self.cancelBtn, 1, wx.TOP | wx.BOTTOM | wx.CENTER, 20)
		self.sizerHor2.AddStretchSpacer()
		self.sizerVert.AddStretchSpacer()
		self.sizerVert.Add(self.instructions, 0, flags, 10)
		self.sizerVert.AddStretchSpacer()
		self.sizerVert.Add(self.sizerHor,0,flags,5)
		#self.sizerVert.Add(self.submitBtn, 0, flags, 5)
		self.sizerVert.Add(self.sizerHor2,1,flags|wx.EXPAND,5)
		self.sizerVert.AddStretchSpacer()
		self.sizerVert.Add(self.sizerHor3,1,flags|wx.EXPAND,5)
		self.sizerVert.AddStretchSpacer()
		#self.sizerVert.Add(information, 0, flags, 10)
		self.sizerVert.Add(self.warning, 0, flags, 10)
		self.sizerVert.AddStretchSpacer()
		
		self.minTxt.Enable(False)
		self.submitBtn.Enable(False)
		self.optionalBtn.Enable(False)
		
		#self.SetBackgroundColour('#cfe8ff')
		self.panel.SetBackgroundColour('sky blue')
		self.SetSizer(self.sizerVert)
		self.alignToCenter(self)
		self.Layout()
	
	#align the print time frame to the bottom right of the screen...this seems to be the least obstrusive
	def alignToCenter(self,window):
	#set the window dead-center of the screen
		dw, dh = wx.DisplaySize()
		w, h = window.GetSize()
		x = dw/2 - w/2
		y = dh/2 - h/2
		window.SetPosition((x,y))
		#print dw, dh, w, h, x, y
	
	#makes sure all timers are cancelled on close and set the GUI to lock if a user has started a print
	def onClose(self,event):
		if app.frame.activeInput:
			app.frame.activeInput = False
			app.frame.Raise()
		elif app.signOnFrame.adminMode:
			if app.adminFrame.activeInput:
				app.adminFrame.activeInput = False
				app.adminFrame.Raise()
		self.MakeModal(False)
		self.Hide()
	
	#action to take on button press
	def onChoice(self, event):
		#pull the user selections
		admin = False
		if app.signOnFrame.adminMode:
			if app.adminFrame.activeInput:
				admin = True
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
					if admin:
						self.optionalBtn.Enable(False)
				else:
					if mins:
					#if hour and minute have been selected, enable the submit button
						self.submitBtn.Enable(True)
						if admin and hours == "0":
							self.optionalBtn.Enable(True)
						else:
							self.optionalBtn.Enable(False)
			else:
			#if hours are greater than max time, set minutes to zero automatically
				self.minTxt.Enable(False)
				self.minTxt.SetSelection(0)
				self.submitBtn.Enable(True)
				if admin:
					self.optionalBtn.Enable(False)
	#action to take on submit button
	def onEnter(self, event):
		#should probably change this to reflect how much the print is going to cost
		app.frame.timer.Stop()
		btn = event.GetEventObject()
		btnLabel = btn.GetLabel()
		agreeDlg = wx.MessageDialog(self, "THIS IS REAL MONEY\n\nAre you sure?", "PROCEED?", wx.OK | wx.CANCEL)
		result = agreeDlg.ShowModal()
		agreeDlg.Close()
		agreeDlg.Destroy()
		if result == wx.ID_CANCEL:
			app.frame.timer.Start()
		elif result == wx.ID_OK:
		#if user agress, get the time choosen and send it to the pub listener "timelistener"
			hours = self.hourTxt.GetStringSelection()
			mins = self.minTxt.GetStringSelection()
			#print hours, mins
			if "FREE" in btnLabel:
				pub.sendMessage("timeListener", timeHour=hours, timeMinute=mins, machine=self.machine, free=True)
			else:
				pub.sendMessage("timeListener", timeHour=hours, timeMinute=mins, machine=self.machine, free=False)
			#pub.sendMessage("timeListener", timeHour=hours, timeMinute="1")		
	
	def killPrinter(self,event):
		app.adminFrame.socketWorker.sendEvent(["EVT_END",self.machine,app.signOnFrame.userIDnumber,"False"])
		self.onClose(wx.EVT_BUTTON)
	
	def AdminTime(self,event):
		app.adminFrame.socketWorker.sendEvent(["EVT_ADD_TIME",self.machine,app.signOnFrame.userIDnumber,"ADMIN"])
		self.onClose(wx.EVT_BUTTON)
	
	def StatusChange(self,event):
		#print "status change"
		for machineNum, machine in enumerate(app.frame.bitmap_buttons):
			machineName = machine.sizer.GetStaticBox().GetLabel()
			if machineName == self.machine:
				if app.frame.bitmap_buttons[machineNum].status == "ENABLED":
					app.adminFrame.socketWorker.sendEvent(["EVT_STATUS",self.machine,app.signOnFrame.userIDnumber,"FALSE"])
				elif app.frame.bitmap_buttons[machineNum].status == "DISABLED":
					app.adminFrame.socketWorker.sendEvent(["EVT_STATUS",self.machine,app.signOnFrame.userIDnumber,"TRUE"])
				break
		self.onClose(wx.EVT_BUTTON)

		
class CountDownThread(threading.Thread):
	def __init__(self,parent):
	#accept machine and machine properties as args
		threading.Thread.__init__(self)
		self.parent = parent
		self.runFlag = True #run Flag indicates the thread is still running. Can be called externally to end the thread
		
	#required function called by start()
	def run(self):
		while self.runFlag:
		#run until timer expires or kill flag is set
			if (self.parent.seconds2Expire <= 1):
			#check if the timer has expired, and end the thread by setting the run flag...kills the while loop
				self.runFlag = False
			else:
				wx.CallAfter(app.frame.updateFromThread, self.parent)
				time.sleep(1)
		wx.CallAfter(app.frame.ResetMachine,self.parent)
	def stop(self):
	#pretty sure the order of these variables are important. Set the kill(ed) flag, and then end the thread.
		self.runFlag = False

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
		#display a waiting message inside the GUI thread with callafter
		wx.CallAfter(self.parent.contactServer)
		wx.GetApp().ProcessPendingEvents()
		#I think this is actually pretty hacky
		
		# convert all messages to uppercase
		packet = [x.upper() for x in eventPacket]
		#form the list into a string delineated by a SPACE 
		packetStr = ' '.join(packet)
		try:
			#connect to the server on the port specified
			client = socket.create_connection((SERVERADDRESS, SERVERPORT))
			#send the packet string
			client.send(packetStr)
			#receive a response in a buffer, and split string into a list
			reply=(client.recv(1024)).split()
			wx.CallAfter(self.parent.closeSocket)
			wx.GetApp().ProcessPendingEvents()
		except Exception, msg:
			#call this function if the connection was a failure
			wx.CallAfter(self.parent.socketClosed,wx.EVT_CLOSE,msg)
		else:
			if len(reply) == 3:
			#make sure the reply packet is properly formed
				if reply[0] == packet[0] and reply[1]:
				#make sure the correct packet was received by comparing the outgoing and the incoming EVENT (EVT)
					#send the reply to the pub listener "socketListener"
					#print self.parent
					if self.parent is app.frame:
						pub.sendMessage("frameListener", sent=packet, reply=reply)
					elif self.parent is app.signOnFrame:
						pub.sendMessage("signOnListener", sent=packet, reply=reply)
					elif self.parent is app.adminFrame:
						pub.sendMessage("adminListener", sent=packet, reply=reply)
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

			
class MainWindow(wx.Frame):
	def __init__(self, parent, title):
		#i don't know what this does
		self.dirname = ' '
		styleFlags = wx.STAY_ON_TOP# | wx.NO_BORDER# | wx.FRAME_NO_TASKBAR
		if GTK:
			styleFlags = wx.DEFAULT_FRAME_STYLE | wx.STAY_ON_TOP
		wx.Frame.__init__(self, parent, title = title, style=styleFlags)
		self.adminMode = False
		self.bi = None
		#bind a close event to the function
		self.Bind(wx.EVT_CLOSE, self.OnClose)
		#sizers for centering the static text 
		self.mainSizer = wx.BoxSizer(wx.HORIZONTAL)
		#self.layoutSizer = wx.BoxSizer(wx.VERTICAL)
		brandingLabel = envisionVersion
		#self.branding = wx.StaticText(self, label = self.brandingLabel, style = wx.ALIGN_CENTRE_HORIZONTAL)
		#self.bmp = wx.Bitmap("front-desk.jpg")
		dw, dh = wx.DisplaySize()
		if MACHINENAME.startswith("LAPTOP"):
			self.bmp = wx.Image("./images/laptop_ideas.jpg")
			color = wx.WHITE
		else:
			self.bmp = wx.Image("./images/printerBG.png")
			color = wx.BLACK
		self.bmp = self.bmp.Scale(dw, dh, wx.IMAGE_QUALITY_HIGH)
		self.bmp = wx.BitmapFromImage(self.bmp)
		brandingFont = wx.Font(20, wx.DECORATIVE, wx.ITALIC, wx.BOLD)
		self.bmp = app.WriteCaptionOnBitmap(self,brandingLabel,self.bmp,brandingFont, (2,2), color)
		
		#self.branding.SetFont(self.brandingFont)
		

		#w, h = self.branding.GetSize()
		#y = dh/2 - h/2
		#borderWidth = 20
		
		#layout stuff
		#self.layoutSizer.AddSpacer(y-borderWidth)
		#self.layoutSizer.Add(self.branding, 0, wx.ALIGN_CENTER | wx.ALL, borderWidth)
		#self.layoutSizer.AddSpacer(y-borderWidth)
		#self.panel.SetSizer(self.layoutSizer)
		#self.mainSizer.Add(self.layoutSizer, 1)

		#more layout stuff...maybe not needed now that everything is fullscreen
		self.SetSizer(self.mainSizer)
		self.Centre()
		self.Layout()
		#allows the background image to be set (and redrawn)


		pub.subscribe(self.socketListener, "signOnListener")
		
		
		self.ShowFullScreen(True)
		self.socketWorker = SocketThread(self,None)
		self.socketWorker.start()
		#self.Show()
		if GTK:
			self.panel = wx.Panel(self, wx.ID_ANY)
			self.panel.Bind(wx.EVT_CHAR, self.onKeyPress)
			self.panel.SetFocus()
			self.panel.Bind(wx.EVT_KILL_FOCUS, self.onFocusLost)
		#MSW doesn't like key capture in panels
		elif MSW:
			self.Bind(wx.EVT_CHAR, self.onKeyPress)
			self.SetFocus()
		else:
			wx.MessageBox('Platform Not Supported','ERROR')
			self.Destroy()
			sys.exit(1)
		self.SetBackgroundStyle(wx.BG_STYLE_ERASE)
		self.Bind(wx.EVT_ERASE_BACKGROUND, self.OnEraseBackground)
		
		
		
		
		#~ #i don't know what this does
		#~ self.dirname = ' '
		#~ styleFlags = wx.STAY_ON_TOP# | wx.NO_BORDER# | wx.FRAME_NO_TASKBAR
		#~ if GTK:
			#~ styleFlags = wx.DEFAULT_FRAME_STYLE | wx.STAY_ON_TOP
		#~ wx.Frame.__init__(self, parent, title = title, style=styleFlags)
		#~ color = "light gray"
		#~ self.adminMode = False
		#~ self.Bind(wx.EVT_CLOSE, self.OnClose)
		#~ self.panel = wx.Panel(self, wx.ID_ANY,style=wx.WANTS_CHARS)
		
		#~ self.mainSizer = wx.BoxSizer(wx.VERTICAL)

		#~ self.grid_sizer = wx.GridSizer(app.grids, app.grids, app.grid_gap, app.grid_gap)
		#~ printerInfoFont = wx.Font(app.printerFontSize,wx.FONTFAMILY_SWISS,wx.FONTSTYLE_NORMAL,wx.FONTWEIGHT_BOLD)

		#~ self.printerPanels = []
		#~ self.sizers=[]
		#~ for i in xrange(NUMPRINTERS):
			#~ self.printerPanels.append(wx.Panel(self.panel, wx.ID_ANY))
			#~ this = self.printerPanels[-1]
			#~ this.sizer = wx.StaticBoxSizer(wx.StaticBox(this, wx.ID_ANY, "THIS IS A PRINTER"), wx.VERTICAL)
			#~ this.label = wx.StaticText(this, label="----------------------------------------",style=wx.ALIGN_CENTRE_HORIZONTAL|wx.ST_NO_AUTORESIZE)
			#~ this.label.SetFont(printerInfoFont)
			#~ this.sizer.AddStretchSpacer()
			#~ this.sizer.Add(this.label,0, wx.CENTER)# | wx.EXPAND, 0)
			#~ this.SetSizer(this.sizer)
			#~ this.seconds2Expire = False
			#~ this.bitmap = app.bitmaps["default"]
			#~ this.SetBackgroundColour(color)
			#~ this.SetBackgroundStyle(wx.BG_STYLE_ERASE)
			#~ this.Bind(wx.EVT_ERASE_BACKGROUND, self.OnEraseBackground)
			#~ self.grid_sizer.Add(this,1,wx.EXPAND,0)

		
		#~ #self.mainSizer = wx.BoxSizer(wx.HORIZONTAL)
		#~ self.brandSizer = wx.BoxSizer(wx.HORIZONTAL)
		#~ brandingLabel = envisionVersion
		#~ instructions = "\n **** SIGN IN TO CONTINUE **** \n"
		#~ self.brand = wx.StaticText(self,label=brandingLabel,style=wx.ALIGN_CENTER_HORIZONTAL | wx.ST_NO_AUTORESIZE)
		#~ self.instructions1 = wx.StaticText(self,label=instructions,style=wx.ALIGN_CENTER_HORIZONTAL | wx.ST_NO_AUTORESIZE)
		#~ self.instructions2 = wx.StaticText(self,label=instructions,style=wx.ALIGN_CENTER_HORIZONTAL | wx.ST_NO_AUTORESIZE)
		#~ sizer1 = wx.BoxSizer(wx.VERTICAL)
		#~ sizer2 = wx.BoxSizer(wx.VERTICAL)
		#~ sizer3 = wx.BoxSizer(wx.VERTICAL)
		
		#~ #self.brand = wx.StaticText(self,label=brandingLabel,style=wx.ALIGN_CENTRE|wx.ST_NO_AUTORESIZE)
		#~ #self.brandSizer.Add(brand,1,wx.CENTER)
		#~ self.panel.SetSizer(self.grid_sizer)
		#~ self.mainSizer.Add(self.panel, 1, wx.EXPAND, 0)
		#~ sizer1.Add(self.instructions1, 0, wx.ALIGN_CENTER, 0)
		#~ sizer2.Add(self.brand, 0, wx.ALIGN_CENTER, 0)
		#~ sizer3.Add(self.instructions2, 0, wx.ALIGN_CENTER, 0)
		
		#~ self.brandSizer.Add(sizer1,1,wx.EXPAND,0)
		#~ self.brandSizer.Add(sizer2,1,wx.EXPAND,0)
		#~ self.brandSizer.Add(sizer3,1,wx.EXPAND,0)
		
		#~ self.mainSizer.Add(self.brandSizer,0, wx.ALIGN_CENTER | wx.EXPAND, 0)
	
		#~ brandingFont = wx.Font(14, wx.DECORATIVE, wx.ITALIC, wx.LIGHT)
		#~ self.brand.SetFont(brandingFont)
		#~ self.instructions1.SetFont(printerInfoFont)
		#~ self.instructions2.SetFont(printerInfoFont)
		
		#~ self.instructions1.SetForegroundColour("red")
		#~ self.instructions2.SetForegroundColour("red")		
		
		#~ self.SetSizer(self.mainSizer)
		
		#~ self.Centre()
		#~ self.Layout()

		#~ pub.subscribe(self.socketListener, "signOnListener")
		
		
		#~ self.socketWorker = SocketThread(self,None)
		#~ self.socketWorker.start()
		#~ self.shiftSet = False
		#~ if GTK:
			#~ #self.panel = wx.Panel(self, wx.ID_ANY)
			#~ #self.panel.Bind(wx.EVT_CHAR, self.onKeyPress)
			#~ self.Bind(wx.EVT_CHAR_HOOK,self.onKeyPress)
			#~ #self.panel.Bind(wx.EVT_KEY_DOWN,self.onKeyPress)
			
			#~ #self.panel.SetFocusIgnoringChildren()
			#~ #self.Bind(wx.EVT_SET_FOCUS,self.onFocus)
			#~ #self.Bind(wx.EVT_CHILD_FOCUS,self.onFocus)
			#~ #self.panel.Bind(wx.EVT_KILL_FOCUS, self.onFocusLost)
		#~ #MSW doesn't like key capture in panels
		#~ elif MSW:
			#~ self.Bind(wx.EVT_CHAR, self.onKeyPress)
			#~ self.SetFocus()
		#~ else:
			#~ wx.MessageBox('Platform Not Supported','ERROR')
			#~ self.Destroy()
			#~ sys.exit(1)
		#~ self.panel.SetBackgroundColour(color)

	def onFocus(self,event):
		#print self.FindFocus()
		self.panel.SetFocus()
		#self.panel.SetFocusIgnoringChildren()
		#print "This is main panel: "+ str(self.FindFocus())
	#~ def OnEraseBackground(self, event):
		#~ panel = event.GetEventObject()
		#~ panelSize = panel.GetSize()
		#~ bitmapSize = panel.bitmap.GetSize()
		#~ dc = event.GetDC()
		#~ if not dc:
			#~ print "not dc"
			#~ dc = wx.ClientDC(self)
			#~ rect = self.GetUpdateRegion().GetBox()
			#~ dc.SetClippingRect(rect)
		#~ dc.Clear()
		#~ xStart = (panelSize[0] - bitmapSize[0]) / 2
		#~ yStart = (panelSize[1] - bitmapSize[1]) / 2
		#~ dc.DrawBitmap(panel.bitmap, xStart,yStart)
	def OnEraseBackground(self, evt):
		dc = evt.GetDC()
		if not dc:
			dc = wx.ClientDC(self)
			rect = self.GetUpdateRegion().GetBox()
			dc.SetClippingRect(rect)
		dc.Clear()
		dc.DrawBitmap(self.bmp, 0, 0)	
	def onFocusLost(self,event):
		#print self.FindFocus()
		if self.FindFocus() is None:
			#print "lost focus"
			if GTK:
				self.SetFocus()
				self.panel.SetFocusIgnoringChildren()
				#self.Raise()
			else:
				self.SetFocus()

	def onKeyPress(self, event):
		"""
		capture key events in the panel focus
		if ESC is pressed, ask for the escape code
		if any other key but the "start-key" ($) are captured
		ignore and print an error message
		"""
		global acceptString
		global inputList
		#pseudo buffer for inputList
		keycode = event.GetKeyCode()
		if keycode == 306:
			return
		#print keycode
		if len(inputList) > 50:
			inputList=[]
			return
		
		if keycode == wx.WXK_ESCAPE:
			self.requestExit()
			self.SetFocus()
			return
		if keycode > 256:
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
			if keycode == wx.WXK_RETURN:
				#if return is pressed, make sure the last character is $
				if inputList[-1] == 36:
					#join the character together in a string
					inputString = ''.join(chr(i) for i in inputList)
					#wx.MessageBox("You Entered \n"+inputString, "ERROR")
					
					#check that the string matches the min length
					if len(inputString) > idLength -1:
						self.idEnter(inputString)
					else:
						wx.MessageBox("Not a Recognized ID Type", "ERROR")
						#print inputString
				#reset the capture variables
				acceptString = False
				inputList = []
			#keep capturing characters until return is pressed (or buffer overflows)
			else:
				inputList.append(keycode)
		#ignore all strings that don't start with '$'
		else:
			wx.MessageBox("Please Use The ID-Reader", "ERROR")
		event.Skip()
	def idEnter(self, idInput):
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
			self.socketWorker.sendEvent(["EVT_CHECKID",MACHINENAME,self.userIDnumber,"False"]) #check the ID record on the server
		else:
			self.SetFocus()
			return
	def OnClose(self, event):
		print ("Closing up...")
		for thread in app.frame.bitmap_buttons:
			thread.expireTimer.stop()
		message = "Closing Up..."
		busyMsg = PBI.PyBusyInfo(message, parent=None, title=" ")
		wx.Yield()
		time.sleep(2)
		app.adminFrame.Destroy()
		app.frame.Destroy()
		self.Destroy()
	def requestExit(self):
		exitDlg = wx.PasswordEntryDialog(self, "Enter Code To Exit", "EXIT", "", wx.OK | wx.CANCEL)
		result = exitDlg.ShowModal()
		if exitDlg.GetValue() == '111999':
			exitDlg.Destroy()
			self.OnClose(wx.EVT_CLOSE)
		else:
			exitDlg.Destroy()
	def socketListener(self, sent=None, reply=None):
	#function expects two lists of strings 
		#set variables for clarity
		#del parent.busyMsg
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
		infoList = info.upper().split("|") #split the info string into a list, delineated by | ... 
		#extraneous info is often bundled together in one string to keep the reply packet uniform
		if command == "EVT_CONNECT":
			machines = []
			machines.extend(info.split("|"))
			app.frame.setupMachines(machines)
		elif command == "EVT_SETUP":
			pass
		elif command == "EVT_CHECKID":
		#checkID is called to make sure the user is in the DB and has passed all of the required certifications
			self.major = infoList[1]
			self.level = infoList[2]
			app.frame.ShowFullScreen(True)
			app.frame.Show()
			self.Hide()
			app.frame.timer.inactiveCount = 0
			app.frame.timer.Start(IDLETIME)
			if infoList[0] == "ADMIN":
				app.frame.bitmap_buttons[-1].Enable()

	def processDeny(self,command, error):
		#functions expects two lists, one command and containing any relevant error messages
		#now = datetime.datetime.now()
		errorList = error.split("|")
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
		else:
		#failsafe catch-all
			errorMsg = "UNKNOWN ERROR\n\n Please see an admin"
		wx.MessageBox(errorMsg,"ERROR")
	def contactServer(self):
		message = "Contacting Server..."
		self.busyMsg = PBI.PyBusyInfo(message, parent=None, title=" ")
		time.sleep(0.1)
		try:
			wx.Yield()
		except Exception as e:
			print e
	def closeSocket(self):
		try:
			del self.busyMsg
		except Exception as e:
			print e
			print "busy message didn't exist"
	
	def socketClosed(self, event, errorMsg):
		self.closeSocket()
		errorMsg = str(errorMsg)
		errorDlg = wx.MessageDialog(self, "Connection to SERVER failed!\n\n"+errorMsg+"\n\nPlease see an Administrator", "ERROR", wx.OK | wx.ICON_ERROR | wx.CENTER)
		result = errorDlg.ShowModal()
		if result == wx.ID_OK:
			errorDlg.Destroy()
		# end of class MyFrame
		
class PrinterFrame(wx.Frame):
	def __init__(self, parent,isAdmin=False):
		#i don't know what this does
		self.dirname = ' '
		styleFlags = wx.STAY_ON_TOP# | wx.NO_BORDER# | wx.FRAME_NO_TASKBAR
		if GTK:
			styleFlags = wx.DEFAULT_FRAME_STYLE | wx.STAY_ON_TOP#| wx.FRAME_NO_TASKBAR
		wx.Frame.__init__(self, parent, title = "Printer Selector", style=styleFlags)
		self.panel_1 = wx.Panel(self, wx.ID_ANY)
		self.btnPanel = wx.Panel(self,wx.ID_ANY)
		self.inactiveCount = 0
		self.activeInput = False
		#bind a wxTimer to UpdateEvent, this timer determines if the windows is inactive
		#it does this by checking if the popupFrame has focus for a set amount of time (it shouldn't if the user is using the system)
		self.timer = wx.Timer(self)
		self.Bind(wx.EVT_TIMER,self.UpdateEvent,self.timer)
		self.sizer4 = wx.BoxSizer(wx.VERTICAL)
		self.btnSizer = wx.BoxSizer(wx.HORIZONTAL)

		self.grid_sizer1 = wx.GridSizer(app.grids, app.grids, app.grid_gap, app.grid_gap)
		self.printerInfo = []
		printerInfoFont = wx.Font(app.printerFontSize,wx.FONTFAMILY_SWISS,wx.FONTSTYLE_NORMAL,wx.FONTWEIGHT_BOLD)
		self.bitmap_buttons=[]
		self.sizers=[]
		color = 'medium goldenrod'
		for i in xrange(NUMPRINTERS):
			self.bitmap_buttons.append(wx.BitmapButton(self.panel_1, wx.ID_ANY, app.bitmaps["default"], style = wx.NO_BORDER))
			this = self.bitmap_buttons[-1]
			this.printerInfo = wx.StaticText(self.panel_1, label="----------------------------------------",style=wx.ALIGN_CENTRE_HORIZONTAL|wx.ST_NO_AUTORESIZE)
			this.printerInfo.SetFont(printerInfoFont)
			this.sizer = (wx.StaticBoxSizer(wx.StaticBox(self.panel_1, wx.ID_ANY, " "), wx.VERTICAL))
			this.seconds2Expire = False
			this.expireTimer = CountDownThread(self.bitmap_buttons[-1])
			#self.bitmap_buttons[-1].SetBackgroundColour('#9f9f5f')
			this.SetBackgroundColour(color)
			this.status = "ENABLED"
			#self.Bind(wx.EVT_TIMER,self.countDown2Expire,self.bitmap_buttons[-1].expireTimer)
			this.Bind(wx.EVT_BUTTON, self.onClick)
			#self.bitmap_buttons[-1].Unbind(wx.EVT_BUTTON)
		self.bitmap_buttons[-1].Unbind(wx.EVT_BUTTON)
		self.bitmap_buttons[-1].Bind(wx.EVT_BUTTON, self.onAdmin)
		self.bitmap_buttons[-1].Disable()
		
		buttonFont = wx.Font(40,wx.FONTFAMILY_SWISS,wx.FONTSTYLE_NORMAL,wx.FONTWEIGHT_BOLD)
		self.cancelBtn = wx.Button(self.btnPanel, label=" CANCEL ")
		self.cancelBtn.SetFont(buttonFont)
		self.cancelBtn.Bind(wx.EVT_BUTTON,self.CancelEvent)
		#self.cancelBtn.SetBackgroundColour(color)

		self.seconds2Expire = None
		#self.SetBackgroundColour('#9f9f5f')
		self.panel_1.SetBackgroundColour(color)
		self.btnPanel.SetBackgroundColour(color)
		self.SetBackgroundColour(color)
		self.timeInputFrame = None

		if isAdmin:
			color = "turquoise"
			self.panel_1.SetBackgroundColour(color)
			self.btnPanel.SetBackgroundColour(color)
			self.SetBackgroundColour(color)
			for machineNum, button in enumerate (self.bitmap_buttons):
				button.Unbind(wx.EVT_BUTTON)
				if MACHINENAME.startswith("LAPTOP"):
					button.Bind(wx.EVT_BUTTON, self.onAdminClickLaptop)
				else:
					button.Bind(wx.EVT_BUTTON, self.onAdminClick)
				#machineNum += 1
			self.bitmap_buttons[-1].printerInfo.SetLabel("*** ADMIN MODE ***")
			self.bitmap_buttons[-1].printerInfo.SetForegroundColour((255,0,0))
			self.bitmap_buttons[-1].Enable()
			self.bitmap_buttons[-1].Unbind(wx.EVT_BUTTON)
			self.bitmap_buttons[-1].Bind(wx.EVT_BUTTON,self.closeAdmin)
			self.cancelBtn.Disable()
			
			pub.subscribe(self.socketListener, "adminListener")
			pub.subscribe(self.timeListener, "adminTimeListener")
			#this.cancelBtn.Unbind(wx.EVT_BUTTON)
			#this.cancelBtn.Bind(wx.EVT_BUTTON,this.closeAdmin)
		else:
			self.lock = threading.Lock()
			pub.subscribe(self.socketListener, "frameListener")
			pub.subscribe(self.timeListener, "timeListener")
		self.__do_layout()
		#create a socket instance and start it
		self.socketWorker = SocketThread(self,None)
		self.socketWorker.start()
	def StartTimers(self,machine):
		if machine.startswith("MAKERBOT"):
			bmp = "mbInUse"
		elif machine.startswith("MAKER_MINI"):
			bmp = "mbMiniInUse"
		elif machine.startswith("TAZ_MINI"):
			bmp = "tazMiniInUse"
		elif machine.startwith("LAPTOP"):
			bmp = "laptopInUse"
		else:
			bmp = "tazInUse"
		machineNum = self.bitmap_buttons.index(machine)
		self.bitmap_buttons[machineNum].SetBitmapDisabled(self.bitmaps[bmp])
		self.bitmap_buttons[machineNum].Disable()
		self.bitmap_buttons[machineNum].status = "USER"
		if startTime + timeLeft > now:
			self.bitmap_buttons[machineNum].seconds2Expire = ((startTime + timeLeft)-now).seconds
			self.printerInfo[machineNum].SetLabel(str(datetime.timedelta(seconds=self.bitmap_buttons[machineNum].seconds2Expire)))
			self.bitmap_buttons[machineNum].expireTimer.start()
	
	def CancelEvent(self,event):
		self.HideSelf()
	
	def HideSelf(self):
		self.timer.Stop()
		self.inactiveCount = 0
		self.bitmap_buttons[-1].Disable()
		app.signOnFrame.Show()
		app.signOnFrame.Raise()
		app.signOnFrame.panel.SetFocus()
		self.Hide()
		
	
	def updateFromThread(self,button):
		#print "in thread"
		app.frame.lock.acquire()
		button.seconds2Expire -= 1
		#print button.seconds2Expire
		num = app.frame.bitmap_buttons.index(button)
		app.frame.bitmap_buttons[num].printerInfo.SetLabel((str(datetime.timedelta(seconds=button.seconds2Expire))))
		#app.signOnFrame.printerPanels[num].label.SetLabel((str(datetime.timedelta(seconds=button.seconds2Expire))))
		app.frame.lock.release()
	def ResetMachine(self,button):
		app.frame.lock.acquire()
		machineNum = app.frame.bitmap_buttons.index(button)
		button.seconds2Expire = False
		btnSizer = button.GetContainingSizer().GetStaticBox()
		machine = btnSizer.GetLabel()
		button.seconds2Expire = False
		button.expireTimer = CountDownThread(button)
		button.Enable()
		button.status = "ENABLED"
		app.frame.bitmap_buttons[machineNum].printerInfo.SetLabel(machine)
		app.frame.bitmap_buttons[machineNum].printerInfo.Layout()
		app.frame.Layout()
		
		app.adminFrame.bitmap_buttons[machineNum].printerInfo.SetForegroundColour((0,0,0))
		app.adminFrame.bitmap_buttons[machineNum].printerInfo.SetLabel(machine)
		app.adminFrame.bitmap_buttons[machineNum].status="ENABLED"
		app.adminFrame.bitmap_buttons[machineNum].SetBitmap(button.GetBitmapLabel())
		app.adminFrame.bitmap_buttons[machineNum].printerInfo.Layout()
		app.adminFrame.Layout()
		app.adminFrame.Refresh()
		app.adminFrame.bitmap_buttons[machineNum].printerInfo.Layout()
		#app.signOnFrame.printerPanels[machineNum].sizer.Layout()
		
		app.signOnFrame.Refresh()
		app.frame.lock.release()
	def timeListener(self,timeHour=None,timeMinute=None,machine=None,free=None):
		if app.signOnFrame.adminMode:
			addedTime = datetime.timedelta(minutes=int(timeHour)*60+int(timeMinute)).seconds
		else:
			addedTime = datetime.timedelta(minutes=int(timeHour)*60+int(timeMinute)+15).seconds
		#wx.MessageBox("You can use this machine for "+str(addedTime)+" seconds\n\n","SUCCESS")
		if free:
			self.socketWorker.sendEvent(["EVT_FREE_TIME",machine,app.signOnFrame.userIDnumber,str(addedTime)])
		else:
			self.socketWorker.sendEvent(["EVT_ADD_TIME",machine,app.signOnFrame.userIDnumber,str(addedTime)])
	
	#checks if the user is inactive by seeing if the popupFrame has had focus for a period of time
	#if if has for 2 straight cycles, user is determined to be inactive
	def UpdateEvent(self,event):
		# #if inactive is at zero, it means the timer fired on opening, it restarts the timer to a specified time 
		# #print "update event"
		# # if self.inactiveCount == 0:
			# # self.timer.Stop()
			# # #self.timer.Start(1000*60*2) #set the idle time to be 2 minutes
			# # self.timer.Start(1000*5)
			# # self.inactiveCount += 1
		# if not PrinterFrame.IsActive(self):
		# #if the popupFrame is not active, make it active, restart the inactive count (because the user was using the system)
		# #this takes the users' focus away from their task, it's not ideal, but it works
			# if app.signOnFrame.adminMode:
				# if PrinterFrame.IsActive(app.adminFrame):
					# self.inactiveCount +=1
			# else:
				# self.SetFocus()
				# #self.Raise()
				# self.inactiveCount = 0
		# else:
		# #else if the popupFrame was active, increase the inactive count, because the user hasn't been using the system
			# #print "self is active"
			# self.inactiveCount +=1
		if self.inactiveCount >= 0:
		#if the user hasn't used the system for two cylces, stop the timer, and call the idleframe message to ask if user
		#wants more time
			if self.activeInput:
				self.timeInputFrame.MakeModal(False)
				self.timeInputFrame.idleMessage = this = idleFrame(self.timeInputFrame)
			elif app.signOnFrame.adminMode:
				if app.adminFrame.activeInput:
					app.adminFrame.inputFrame.MakeModal(False)
					app.adminFrame.inputFrame.idleMessage = this = idleFrame(app.adminFrame.inputFrame)
				else:
					app.adminFrame.idleMessage = this = idleFrame(app.adminFrame)
			
			else:
				self.idleMessage = this = idleFrame(self)
			self.timer.Stop()
			this.Show()
			this.MakeModal(True)
		else:
			self.inactiveCount +=1
	
	def onAdmin(self,event):
		this = app.adminFrame
		app.signOnFrame.adminMode = True
		#machineNum = 0
		for machineNum, button in enumerate (this.bitmap_buttons):
			if button.status == "DISABLED" or button.status == "USER":
				button.printerInfo.SetForegroundColour((255,0,0))
				button.printerInfo.SetLabel(self.bitmap_buttons[machineNum].printerInfo.GetLabel())
				button.printerInfo.Layout()
					
			elif button.status == "MAINTENANCE":
				button.printerInfo.SetLabel("MAINTENANCE")
				button.printerInfo.SetForegroundColour((255,0,0))
				button.printerInfo.Layout()
				#button.Unbind(wx.EVT_BUTTON)
		#app.adminFrame = PrinterFrame(None)
		this.Layout()
		this.Refresh()
		this.ShowFullScreen(True)
		this.Show()
		self.Hide()
			
	def onAdminClickLaptop(self, event):
		btn = event.GetEventObject()
		btnSizer = btn.GetContainingSizer().GetStaticBox()
		machine = btnSizer.GetLabel()
		status = btn.status
		self.activeInput = True
		self.inputFrame = SimplePopupFrame(self,machine)
		that = self.inputFrame
		that.warning.SetLabel("** ADMINISTRATOR MODE **")
		that.instructions.SetLabel("* WHAT DO YOU WANT TO DO *")
		#that.killBtn = wx.Button(that.panel, label= " CANCEL ")
		
		that.optionalBtn.Unbind(wx.EVT_BUTTON)
		that.submitBtn.Unbind(wx.EVT_BUTTON)
		
		if status == "USER":
			that.optionalBtn.SetLabel(" RELEASE ")
			that.submitBtn.SetLabel(" OPEN ")
			that.optionalBtn.Bind(wx.EVT_BUTTON, that.ReleaseID)
		else:
			that.submitBtn.SetLabel(" OPEN ")
			if status == "DISABLED":
				that.optionalBtn.SetLabel(" ENABLE ")
			elif status == "ENABLED":
				that.optionalBtn.SetLabel(" DISABLE ")
			that.optionalBtn.Bind(wx.EVT_BUTTON, that.StatusChange)
		
		that.submitBtn.Bind(wx.EVT_BUTTON, that.LockerOpen)
		#that.killBtn.Bind(wx.EVT_BUTTON, that.onClose)
		
		
		#that.killBtn.SetFont(that.font)
		#that.sizerHor3.Add(that.killBtn, 1, wx.TOP | wx.BOTTOM | wx.CENTER, 5)
		that.optionalBtn.Enable()
		that.Layout()
		that.Show()
		that.MakeModal(True)
	
	def onAdminClick(self, event):
		btn = event.GetEventObject()
		btnSizer = btn.GetContainingSizer().GetStaticBox()
		machine = btnSizer.GetLabel()
		status = btn.status
		self.activeInput = True
		self.inputFrame = popupFrame(self,machine)
		that = self.inputFrame
		that.warning.SetLabel("** ADMINISTRATOR MODE **")
		if status == "USER" or status == "MAINTENANCE":
			that.instructions.SetLabel("* ENTER THE ADDITIONAL TIME TO ADD *")
			that.optionalBtn.SetLabel(" FREE ")
			#that.optionalBtn.Enable()
			that.optionalBtn.Bind(wx.EVT_BUTTON,that.onEnter)
			that.submitBtn.SetLabel(" USER ")
			that.killBtn = wx.Button(that.panel, label= " KILL ")
			that.killBtn.SetFont(that.font)
			that.killBtn.Bind(wx.EVT_BUTTON,that.killPrinter)
			that.sizerHor3.Add(that.killBtn, 1, wx.TOP | wx.BOTTOM | wx.CENTER, 5)
			if status == "MAINTENANCE":
				that.hourTxt.Disable()
		else:
			that.hourTxt.Disable()
			that.instructions.SetLabel("* WHAT WOULD YOU LIKE TO DO? *")
			that.optionalBtn.SetLabel(" DISABLE ")
			that.submitBtn.SetLabel(" ENABLE ")
			that.killBtn = wx.Button(that.panel, label= " ADD MAINTENANCE TIME ")
			that.killBtn.SetFont(that.font)
			that.killBtn.Bind(wx.EVT_BUTTON,that.AdminTime)
			that.sizerHor3.Add(that.killBtn, 1, wx.TOP | wx.BOTTOM | wx.CENTER, 5)
			if status == "DISABLED":
				that.optionalBtn.Disable()
				that.submitBtn.Enable()
			elif status == "ENABLED":
				that.optionalBtn.Enable()
				that.submitBtn.Disable()
			elif status == "MAINTENANCE":
				that.optionalBtn.Disable()
				that.submitBtn.Disable()
				that.killBtn.Disable()
			that.optionalBtn.Unbind(wx.EVT_BUTTON)
			that.submitBtn.Unbind(wx.EVT_BUTTON)
			that.optionalBtn.Bind(wx.EVT_BUTTON, that.StatusChange)
			that.submitBtn.Bind(wx.EVT_BUTTON, that.StatusChange)
		that.Layout()
		that.Show()
		that.MakeModal(True)

		
	def closeAdmin(self,event):
		app.frame.timer.Stop()
		app.signOnFrame.adminMode = False
		app.frame.bitmap_buttons[-1].Disable()
		app.signOnFrame.Show()
		app.signOnFrame.Raise()
		app.signOnFrame.SetFocus()
		app.frame.timer.inactiveCount = 0
		self.Hide()
	
	def onClick(self, event):
		btn = event.GetEventObject()
		btnSizer = btn.GetContainingSizer().GetStaticBox()
		machine = btnSizer.GetLabel()
		self.socketWorker.sendEvent(["EVT_CHECKID",machine,app.signOnFrame.userIDnumber,"False"])
		
	#end def
	

	def __set_properties(self):
		# begin wxGlade: MyFrame.__set_properties
		self.SetTitle(_("frame"))
		for button in self.bitmap_buttons:
			button.SetSize(button.GetBestSize())

	def __do_layout(self):
		for button in self.bitmap_buttons:
			button.sizer.Add(button, 1, wx.ALL | wx.EXPAND, 0)
			button.sizer.Add(button.printerInfo,0,wx.CENTER)
			self.grid_sizer1.Add(button.sizer, 1, wx.ALL | wx.EXPAND, app.gridSizerBorder)
		
		self.panel_1.SetSizer(self.grid_sizer1)
		self.sizer4.Add(self.panel_1, 1, wx.EXPAND, 0)
		#self.sizer4.AddStretchSpacer()
		
		#self.sizer4.Add((0,0), 1, wx.EXPAND, 0)
		self.btnSizer.AddStretchSpacer()
		self.btnSizer.Add(self.cancelBtn,1,wx.EXPAND|wx.BOTTOM|wx.TOP,app.buttonSize//4)
		self.btnSizer.AddStretchSpacer()
		self.btnPanel.SetSizer(self.btnSizer)
		self.sizer4.Add(self.btnPanel,1,wx.EXPAND,0)
		#self.sizer4.AddStretchSpacer()

		
		
		self.SetSizer(self.sizer4)
		self.sizer4.Fit(self)
		self.Layout()
		# end wxGlade
		#this function listens to the published messages from the socket process
	def socketListener(self, sent=None, reply=None):
	#function expects two lists of strings 
		#set variables for clarity
		#del self.busyMsg
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

	def setupMachines(self,machines):
		#machineNum = 0
		for machineNum, machine in enumerate(machines):
			this = app.frame.bitmap_buttons[machineNum]
			that = app.adminFrame.bitmap_buttons[machineNum]
			this.sizer.GetStaticBox().SetLabel(machine)
			this.printerInfo.SetLabel(machine)
			that.sizer.GetStaticBox().SetLabel(machine)
			that.printerInfo.SetLabel(machine)
			#app.signOnFrame.printerPanels[machineNum].sizer.GetStaticBox().SetLabel(machine)
			#app.signOnFrame.printerPanels[machineNum].label.SetLabel(machine)
			if machine.startswith("MAKERBOT"):
				this.SetBitmap(app.bitmaps["mbEnabled"])
				this.SetBitmapDisabled(app.bitmaps["mbDisabled"])
				that.SetBitmap(app.bitmaps["mbEnabled"])
				that.SetBitmapDisabled(app.bitmaps["mbDisabled"])
			elif machine.startswith("LAPTOP"):
				this.SetBitmap(app.bitmaps["laptopEnabled"])
				this.SetBitmapDisabled(app.bitmaps["laptopDisabled"])
				that.SetBitmap(app.bitmaps["laptopEnabled"])
				that.SetBitmapDisabled(app.bitmaps["laptopDisabled"])
			elif machine.startswith("MAKER_MINI"):
				this.SetBitmap(app.bitmaps["mbMiniEnabled"])
				this.SetBitmapDisabled(app.bitmaps["mbMiniDisabled"])
				that.SetBitmap(app.bitmaps["mbMiniEnabled"])
				that.SetBitmapDisabled(app.bitmaps["mbMiniDisabled"])
			elif machine.startswith("TAZ_MINI"):
				this.SetBitmap(app.bitmaps["tazMiniEnabled"])
				this.SetBitmapDisabled(app.bitmaps["tazMiniDisabled"])
				that.SetBitmap(app.bitmaps["tazMiniEnabled"])
				that.SetBitmapDisabled(app.bitmaps["tazMiniDisabled"])
			else:
				this.SetBitmap(app.bitmaps["tazEnabled"])
				this.SetBitmapDisabled(app.bitmaps["tazDisabled"])
				that.SetBitmap(app.bitmaps["tazEnabled"])
				that.SetBitmapDisabled(app.bitmaps["tazDisabled"])
			self.socketWorker.sendEvent(["EVT_SETUP",MACHINENAME,"False",machine])
			#machineNum += 1
		#print machineNum, NUMPRINTERS
		machineNum += 1
		if machineNum < NUMPRINTERS:
			for i in xrange(machineNum,NUMPRINTERS):
				#print "disabling"
				self.bitmap_buttons[i].Disable()
	
	#called after the server checks and accepts the user ID for a machine
	def agreeUse(self, machine):
	#logging of usage is done server side
		self.timer.Stop()
		agreeMessage = "I declare that \n\n-- "+app.signOnFrame.userIDnumber + " is my ID \n-- I am trained to use this machine"
		agreeDlg = wx.MessageDialog(self, agreeMessage, "TERMS OF USE", wx.YES_NO | wx.CENTRE)
		result = agreeDlg.ShowModal()
		agreeDlg.Close()
		agreeDlg.Destroy()
		if result == wx.ID_NO:
			wx.MessageBox("Use is NOT authorized", "ERROR!")
			self.timer.Start()
		else:
			self.socketWorker.sendEvent(["EVT_SINGLE_CHECK",machine,app.signOnFrame.userIDnumber,"False"])
		
	
	#called after the socketlistener determines the packets were properly formed, and were accepted by the server
	def processReply(self, command, info):
		app.frame.timer.Stop()
		#function expects two strings: the command and the information returned by the server
		infoList = info.upper().split("|") #split the info string into a list, delineated by | ... 
		#extraneous info is often bundled together in one string to keep the reply packet uniform
		
		if command == "EVT_CONNECT":
			machines = []
			machines.extend(info.split("|"))
			self.setupMachines(machines)
			return
		elif command == "EVT_SETUP":
			#for machine in app.signOnFrame.printerPanels:
			for machineNum, machine in enumerate(app.frame.bitmap_buttons):
				machineName = machine.sizer.GetStaticBox().GetLabel()
				if machineName == infoList[0]:
					if machineName.startswith("MAKERBOT"):
						bmp = app.bitmaps["mbEnabled"]
					elif machineName.startswith("MAKER_MINI"):
						bmp = app.bitmaps["mbMiniEnabled"]
					elif machineName.startswith("TAZ_MINI"):
						bmp = app.bitmaps["tazMiniEnabled"]
					elif machineName.startswith("LAPTOP"):
						bmp = app.bitmaps["laptopEnabled"]
					else:
						bmp = app.bitmaps["tazEnabled"]
					
					machine.SetBitmap(bmp)
					machine.bitmap = bmp
					machine.printerInfo.SetLabel(machineName)
					machine.printerInfo.SetForegroundColour((0,0,0))
					machine.printerInfo.Layout()
					
					app.adminFrame.bitmap_buttons[machineNum].printerInfo.SetForegroundColour((0,0,0))
					app.adminFrame.bitmap_buttons[machineNum].printerInfo.SetLabel(machineName)
					app.adminFrame.bitmap_buttons[machineNum].status="ENABLED"
					app.adminFrame.bitmap_buttons[machineNum].SetBitmap(machine.GetBitmapLabel())
					app.adminFrame.bitmap_buttons[machineNum].printerInfo.Layout()
					
					app.adminFrame.Layout()
					app.adminFrame.Refresh()
					app.frame.Layout()
					app.frame.Refresh()
					break
			return
			
		elif command == "EVT_SINGLE_CHECK":
			if infoList[0] == "SAME":
				machine = infoList[1]
				self.timeInputFrame = SimplePopupFrame(self,machine)
				self.timeInputFrame.submitBtn.Enable(False)
				self.timeInputFrame.optionalBtn.Enable(True)
			else:
				machine = infoList[0]
				if machine.startswith("LAPTOP"):
					self.timeInputFrame = SimplePopupFrame(self,machine)
				else:
					self.timeInputFrame = popupFrame(self,machine)
			self.activeInput = True
			self.timeInputFrame.Show()
			self.timeInputFrame.MakeModal(True)
			return
		elif command == "EVT_START":
			machine = infoList[1]
			if MACHINENAME.startswith("LAPTOP"):
				solenoid = str((int(machine[-2:])-1) - ((int(app.lockerNumber) - 1) * 16)) + '\n'
				machineLocker = str(int(machine[-2:])-1)+'\n'
				#print machineLocker
				self.timeInputFrame.onClose(wx.EVT_CLOSE)
				try:
					ARDUINO.write(solenoid)
				except Exception as e:
					print e
					message = "Solenoid failed...please see an admin"
					success = False
					#Need to add an ID release here....a good one anyway
					self.socketWorker.sendEvent(["EVT_RELEASE",machine,app.signOnFrame.userIDnumber,"False"])
				else:
					message = machine + " SUCCESSFULLY CHECKED OUT\n\nPlease remember to close the door"
					success = True
				successDlg = wx.MessageDialog(self, message, "SUCCESS", wx.OK | wx.CENTRE)
				successDlg.ShowModal()
				successDlg.Close()
				successDlg.Destroy()
				if success:
					self.socketWorker.sendEvent(["EVT_SETUP",MACHINENAME,"False",machine])
				self.HideSelf()
			else:
				self.socketWorker.sendEvent(["EVT_SETUP","PRINTER_KIOSK","False",machine])
				self.HideSelf()
			return
		
		elif command == "EVT_RETURN":
			machine = infoList[1]
			solenoid = str((int(machine[-2:])-1) - ((int(app.lockerNumber) - 1) * 16)) + '\n'
			machineLocker = str(int(machine[-2:])-1)+'\n'
			#print machineLocker
			self.timeInputFrame.onClose(wx.EVT_CLOSE)
			#wx.MessageBox("Printer has started!\n\nYour balance is $"+infoList[1],"SUCCESS")
			try:
				ARDUINO.write(solenoid)
			except Exception as e:
				print e
			else:
				message = "Laptop is returned\n\nThanks!"
				successDlg = wx.MessageDialog(self, message, "SUCCESS", wx.OK | wx.CENTRE)
				successDlg.ShowModal()
				successDlg.Close()
				successDlg.Destroy()
				self.socketWorker.sendEvent(["EVT_SETUP",MACHINENAME,"False",machine])
			app.adminFrame.bitmap_buttons[int(solenoid)].status="ENABLED"
			#app.adminFrame.bitmap_buttons[machineLocker].printerInfo.SetLabel(machineName)
			app.adminFrame.bitmap_buttons[int(solenoid)].printerInfo.SetForegroundColour((0,0,0))
			self.HideSelf()
			return
		elif command == "EVT_CHECKID":
			machine = infoList[3]
			self.agreeUse(machine)
			return
		
		elif command == "EVT_ADD_TIME":
		#add time events are called when a user adds time to a 3d print, or an admin adds additional time
			machine = infoList[2]
			if infoList[0] == "STARTED":
			#server has indicated that the printer has started
				if infoList[1] == "FREE":
				#unlikely event that the printer was started and the user wasn't charged...it may happend because of server side issues
					message = "Congrats! Your print is free today!\n\n"
					#wx.MessageBox("Congrats! Your print is free today!\n\n","ERROR")
				else:
				#indicate the users remaining balance
					if infoList[1] == "ADMIN":
						#wx.MessageBox("Maintenance Mode ENABLED for 30 minutes","SUCCESS")
						message = "Maintenance Mode ENABLED for 30 minutes"
						app.frame.socketWorker.sendEvent(["EVT_SETUP","PRINTER_KIOSK","False",machine])
						#app.adminFrame.inputFrame.onClose(wx.EVT_BUTTON)
						for machineNum, button in enumerate(app.frame.bitmap_buttons):
							machineName = button.sizer.GetStaticBox().GetLabel()
							if machineName == infoList[2]:
								#machineIndex = button.index(button)
								app.adminFrame.bitmap_buttons[machineNum].status = "MAINTENANCE"
								button.status = "MAINTENANCE"
								app.adminFrame.bitmap_buttons[machineNum].printerInfo.SetLabel("MAINTENANCE")
								app.adminFrame.bitmap_buttons[machineNum].printerInfo.SetForegroundColour((255,0,0))
								break
						app.adminFrame.bitmap_buttons[machineNum].printerInfo.Layout()
						app.adminFrame.Layout()
						app.adminFrame.Refresh()
					else:
						self.timeInputFrame.onClose(wx.EVT_CLOSE)
						#wx.MessageBox("Printer has started!\n\nYour balance is $"+infoList[1],"SUCCESS")
						message = "Printer has started!\n\nYour balance is $"+infoList[1]
						successDlg = wx.MessageDialog(self, message, "TERMS OF USE", wx.OK | wx.CENTRE)
						successDlg.ShowModal()
						successDlg.Close()
						successDlg.Destroy()
						self.socketWorker.sendEvent(["EVT_START",machine,app.signOnFrame.userIDnumber,"|".join(["FALSE",app.signOnFrame.major,app.signOnFrame.level])])
						return
					
			elif infoList[0]=="ADDED":
			#if an ADMIN added time for the user
				for machineNum, machine in enumerate(app.frame.bitmap_buttons):
					machineName = machine.sizer.GetStaticBox().GetLabel()
					if machineName == infoList[3]:
						app.frame.lock.acquire()
						try:
							machine.seconds2Expire += int(infoList[1])
						finally:
							app.frame.lock.release()
						break
				#wx.MessageBox("Time Added\n\nBalance is $"+infoList[2],"SUCCESS")
				message = "Time Added\n\nBalance is $"+infoList[2]
				app.adminFrame.inputFrame.onClose(wx.EVT_BUTTON)
				#time.sleep(2)
				app.adminFrame.bitmap_buttons[machineNum].printerInfo.SetLabel((str(datetime.timedelta(seconds=machine.seconds2Expire))))
				#app.adminFrame.bitmap_buttons[machineNum].printerInfo.SetLabel(machine.printerInfo.GetLabel())
				app.adminFrame.bitmap_buttons[machineNum].printerInfo.Layout()
				#app.adminFrame.bitmap_buttons[machineNum].printerInfo.Refresh()
				app.adminFrame.Layout()
				app.adminFrame.Refresh()
		
		elif command == "EVT_FREE_TIME":
			for machineNum, machine in enumerate(app.frame.bitmap_buttons):
				machineName = machine.sizer.GetStaticBox().GetLabel()
				if machineName == infoList[2]:
					app.frame.lock.acquire()
					try:
						machine.seconds2Expire += int(infoList[1])
					finally:
						app.frame.lock.release()
					break
			#wx.MessageBox("Time Added\n\nBalance is $"+infoList[2],"SUCCESS")
			message = "FREE Time Added"#\n\nBalance is $"+infoList[2]
			app.adminFrame.inputFrame.onClose(wx.EVT_BUTTON)
			app.adminFrame.bitmap_buttons[machineNum].printerInfo.SetLabel((str(datetime.timedelta(seconds=machine.seconds2Expire))))
			#app.adminFrame.bitmap_buttons[machineNum].printerInfo.SetLabel(machine.printerInfo.GetLabel())
			app.adminFrame.bitmap_buttons[machineNum].printerInfo.Layout()
			app.adminFrame.Layout()
			app.adminFrame.Refresh()
		
		elif command == "EVT_RELEASE":
			for machineNum, machine in enumerate(app.frame.bitmap_buttons):
				machineName = machine.sizer.GetStaticBox().GetLabel()
				if machineName == infoList[0]:
					self.ResetMachine(machine)
					self.socketWorker.sendEvent(["EVT_SETUP",MACHINENAME,"False",machineName])
			message = "ID RELEASED"
		
		elif command == "EVT_END":
		#called if an ADMIN cancels a print
			for machineNum, machine in enumerate(app.frame.bitmap_buttons):
				machineName = machine.sizer.GetStaticBox().GetLabel()
				if machineName == infoList[1]:
					machine.expireTimer.stop()
					break
			#update the bitmap button label in adminFrame
			#Note: the updating is done in ResetMachine that is called after the thread ends
			#wx.MessageBox("Print Has Been KILLED","SUCCESS")
			message = "Print has been KILLED"
		elif command == "EVT_STATUS":
		#change in and out of maintenance mode
			for machineNum, machine in enumerate(app.frame.bitmap_buttons):
				machineName = machine.sizer.GetStaticBox().GetLabel()
				if machineName == infoList[1]:
					#print machineName
					#machineIndex = app.frame.sizers.index(machine)
					if infoList[0] == "ENABLED":
						#wx.MessageBox("Machine enabled\n\n","SUCCESS")
						message = "Machine enabled\n\n"
						machine.status="ENABLED"
						app.adminFrame.bitmap_buttons[machineNum].status="ENABLED"
						machine.Enable()
						machine.printerInfo.SetLabel(machineName)
						machine.printerInfo.SetForegroundColour((0,0,0))
						app.adminFrame.bitmap_buttons[machineNum].printerInfo.SetLabel(machineName)
						app.adminFrame.bitmap_buttons[machineNum].printerInfo.SetForegroundColour((0,0,0))
					elif infoList[0] == "DISABLED":
						#wx.MessageBox("Machine taken offline\n\n","SUCCESS")
						message = "Machine taken offline\n\n"
						machine.status="DISABLED"
						app.adminFrame.bitmap_buttons[machineNum].status="DISABLED"
						machine.Disable()
						machine.printerInfo.SetLabel("** OFFLINE **")
						app.adminFrame.bitmap_buttons[machineNum].printerInfo.SetLabel("** OFFLINE **")
						app.adminFrame.bitmap_buttons[machineNum].printerInfo.SetForegroundColour((255,0,0))
			machine.printerInfo.Layout()
			app.adminFrame.bitmap_buttons[machineNum].printerInfo.Layout()
			app.frame.Layout()
			app.adminFrame.Layout()
			app.adminFrame.Refresh()
		successDlg = wx.MessageDialog(self, message, "SUCCESS!", wx.OK | wx.CENTRE)
		successDlg.ShowModal()
		successDlg.Close()
		successDlg.Destroy()
		app.frame.timer.Start()				
						
	#this function is called if the socketListener determines that the packet was processed but not approved by the server
	def processDeny(self,command, error):
		#functions expects two lists, one command and containing any relevant error messages
		#now = datetime.datetime.now()
		app.frame.timer.Stop()
		errorList = error.split("|")
		if command == "EVT_CHECKID":
		#if check id fails, explain why
			if errorList[0] == "CERT":
				errorMsg = "You have not completed the training for this machine!\n\nPlease log into the EnVision Portal to complete"
			else:
				errorMsg = error
		
		elif command == "EVT_SETUP":
			if errorList[1] == "OFFLINE":
				for num, machine in enumerate(self.bitmap_buttons):
					machineName = machine.sizer.GetStaticBox().GetLabel()
					if machineName == errorList[0]:
						machine.printerInfo.SetLabel("** OFFLINE **")
						app.adminFrame.bitmap_buttons[num].printerInfo.SetLabel("** OFFLINE **")
						app.adminFrame.bitmap_buttons[num].printerInfo.SetForegroundColour((255,0,0))
						if machineName.startswith("MAKERBOT"):
							bmp = "mbDisabled"
						elif machineName.startswith("MAKER_MINI"):
							bmp = "mbMiniDisabled"
						elif machineName.startswith("TAZ_MINI"):
							bmp = "tazMiniDisabled"
						elif machineName.startswith("LAPTOP"):
							bmp = "laptopDisabled"
						else:
							bmp = "tazDisabled"
						machine.SetBitmapDisabled(app.bitmaps[bmp])
						
						#machine.bitmap = app.bitmaps[bmp]
						machine.Disable()
						#app.adminFrame.bitmap_buttons[num].Disable()
						machine.status = "DISABLED"
						app.adminFrame.bitmap_buttons[num].status = "DISABLED"
						break
			elif errorList[1] == "USER":
				for num, machine in enumerate(self.bitmap_buttons):
					machineName = machine.sizer.GetStaticBox().GetLabel()
					if machineName == errorList[0]:
						if machineName.startswith("MAKERBOT"):
							bmp = "mbInUse"
						elif machineName.startswith("MAKER_MINI"):
							bmp = "mbMiniInUse"
						elif machineName.startswith("TAZ_MINI"):
							bmp = "tazMiniInUse"
						elif machineName.startswith("LAPTOP"):
							bmp = "laptopInUse"
						else:
							bmp = "tazInUse"
						machine.SetBitmapDisabled(app.bitmaps[bmp])
						machine.status = "USER"
						app.adminFrame.bitmap_buttons[num].status = "USER"
						app.adminFrame.bitmap_buttons[num].printerInfo.SetForegroundColour((255,0,0))
						if machineName.startswith("LAPTOP"):
							machine.printerInfo.SetLabel("** IN USE **")
							machine.SetBitmap(app.bitmaps[bmp])
							machine.sizer.Layout()
							app.adminFrame.bitmap_buttons[num].printerInfo.SetLabel("**IN USE**")
							app.adminFrame.bitmap_buttons[num].SetBitmap(app.bitmaps[bmp])
							app.adminFrame.bitmap_buttons[num].sizer.Layout()
						else:
							machine.Disable()
							now = datetime.datetime.now()
							print machineName,errorList[2], errorList[3]
							startTime = datetime.datetime.strptime(errorList[2], '%Y%m%d-%H:%M:%S')
							timeLeft = datetime.timedelta(seconds=int(errorList[3]))
							if startTime + timeLeft > now:
								machine.seconds2Expire = ((startTime + timeLeft)-now).seconds
								print machine.seconds2Expire
								machine.printerInfo.SetLabel(str(datetime.timedelta(seconds=self.bitmap_buttons[num].seconds2Expire)))
								machine.expireTimer.start()
						break
			return
		elif command == "EVT_STATUS":
		#this shouldn't happen
			errorMessage = "Unable to take machine offline\n\n This is safe to dismiss"		
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
		elif command == "EVT_SINGLE_CHECK":
			if errorList[0] == "OCCUPIED":
				if MACHINENAME.startswith("LAPTOP"):
					errorMsg = "\n\nThis laptop is in use. Please select a different machine\n"
				else:
					errorMsg = "\n\nThis printer is in use.\nPlease sign in again\n"
					successDlg = wx.MessageDialog(self, errorMsg, "ERROR", wx.OK | wx.CENTRE)
					successDlg.ShowModal()
					successDlg.Close()
					successDlg.Destroy()
					self.socketWorker.sendEvent(["EVT_SETUP",MACHINENAME,"False",machine])
					self.HideSelf()
					return
			else:
				errorMsg = "\n\nYour ID is already in use on another machine\n"
		else:
		#failsafe catch-all
			errorMsg = command + " ERROR\n\n Please see an admin"
		errorDlg = wx.MessageDialog(self, errorMsg, command, wx.OK | wx.CENTRE)
		errorDlg.ShowModal()
		errorDlg.Close()
		errorDlg.Destroy()
		
		#wx.MessageBox(errorMsg,"ERROR")
		app.frame.timer.Start()
	#this is called if the socket is prematurely closed. Sometimes fires before the system has initialized
	def contactServer(self):
		message = "Contacting Server..."
		self.busyMsg = PBI.PyBusyInfo(message, parent=None, title=" ")
		time.sleep(0.1)
		try:
			wx.Yield()
		except Exception as e:
			print e
	def closeSocket(self):
		try:
			del self.busyMsg
		except Exception as e:
			print e
			print "busy message didn't exist"
	
	def socketClosed(self, event, errorMsg):
		self.closeSocket()
		self.Show()
		self.Raise()
		errorMsg = str(errorMsg)
		errorDlg = wx.MessageDialog(self, "Connection to SERVER failed!\n\n"+errorMsg+"\n\nPlease see an Administrator", "ERROR", wx.OK | wx.ICON_ERROR | wx.CENTER)
		result = errorDlg.ShowModal()
		if result == wx.ID_OK:
			errorDlg.Destroy()
# end of class PrinterFrame
class MyApp(wx.App):
	def OnInit(self):
		self.lockerNumber = socket.gethostname()[-1]
		self.bitmaps = {}
		self.gridSizerBorder = 5
		self.grid_gap = 5
		self.grids = 4
		self.printerFontSize = 14
		self.buttonSize = 60
		self.isInitialized = False
		self.__set_bitmaps__()
		self.signOnFrame = None
		return True
	
	def SetMemDcContext( self, memory, font=None, color=None ) :

		if font:
			memory.SetFont( font )
		else:
			memory.SetFont( wx.NullFont )

		if color:
			memory.SetTextForeground( color )	
	
	def WriteCaptionOnBitmap(self,parent,text, bitmap, font, margins, color):
		memory = wx.MemoryDC()
		memory.SetFont(font)
		font = font
		fit = False
		size = font.GetPointSize()
		textLines = text.split('\n')
		while not fit:
			totalWidth=0
			totalHeight = 0
			setLines = []
			for line in textLines:
				width, height = memory.GetTextExtent(line)
				totalWidth = max(totalWidth,width)
				totalHeight += height
				setLines.append((line,width,height))
			#print bitmap.GetWidth(), width, height
			if (totalWidth > (bitmap.GetWidth()- 2*margins[0])  or  totalHeight > (bitmap.GetHeight()- 2*margins[0])) :
				size -= 1
				if size < MINIMUMFONTSIZE:
					fit = True # will overdraw!!!
				else:
					font.SetPointSize(size)
					memory.SetFont(font)
			else:
				fit = True
		
		centreX, centreY = (bitmap.GetWidth()/2), (bitmap.GetHeight()/2)
		x, y = centreX-(totalWidth/2), centreY-(totalHeight/2)
		memory.SelectObject( bitmap )
		self.SetMemDcContext( memory, font, color)
		for line, deltaX, deltaY in setLines:
			#print line, deltaX, deltaY
			x = centreX - (deltaX/2)
			memory.DrawText( line, x, y,)
			y += deltaY
		memory.SelectObject( wx.NullBitmap)
		return bitmap
	
	
	def __set_bitmaps__(self):
		bmpFont = wx.Font(20,wx.FONTFAMILY_SWISS,wx.FONTSTYLE_NORMAL,wx.FONTWEIGHT_BOLD,underline=False)
		imageDir = "./images/"
		imageList = ["mb_rep.jpg","mb_rep_disabled.jpg","mbImage1.jpg","mbImage_disabled.jpg","taz.jpg","taz_disabled.jpg","taz_mini.jpg","taz_mini_disabled.jpg","dell.jpg", "dell_disabled.jpg","logo-EnVision-HEX_val_044363@3x.png"]
		bitmaps = []
		bitmap_padding = 20
		dw, dh = wx.DisplaySize()
		#print dw, dh
		#bitmapWidth = -(2 * (self.gridSizerBorder + (self.grids * bitmap_padding)) + (self.grid_gap*(self.grids - 1)) - dw) / self.grids
		bitmapWidth = (dw - 2 * self.gridSizerBorder - self.grid_gap)/self.grids - 2 * bitmap_padding
		#bitmapHeight = -(2 * (self.gridSizerBorder + (self.grids * bitmap_padding + self.printerFontSize + self.buttonSize)) + (self.grid_gap*(self.grids - 1)) - dh) / self.grids
		bitmapHeight = (dh - 2*self.gridSizerBorder - self.grid_gap) / self.grids - 2 * bitmap_padding - self.buttonSize
		#print bitmapWidth, bitmapHeight
		bitmapScale = bitmapHeight if bitmapHeight < bitmapWidth else bitmapWidth
		#for image in imageList:
		#	bitmap = wx.Image(imageDir+image)
		#	bitmap = bitmap.Scale(bitmapScale, bitmapScale, wx.IMAGE_QUALITY_HIGH)
		#	bitmaps.append(wx.BitmapFromImage(bitmap))
		#	if image is imageList[-1]:
		#		continue
		#	else:
		#		mask = wx.Mask(bitmaps[-1], wx.WHITE)
		#		bitmaps[-1].SetMask(mask)
		#		if "disabled" in image:
		#			bitmaps.append(wx.BitmapFromImage(bitmap))
		#imageList = ["dell.jpg", "dell_disabled.jpg", "logo-EnVision-HEX_val_044363@3x.png"]
		for image in imageList:
			bitmap = wx.Image(imageDir + image)
			W, H = bitmap.GetSize()
			proportion = W / H
			scaleH = bitmapScale
			scaleW = scaleH * proportion
			bitmap = bitmap.Scale(scaleW, scaleH, wx.IMAGE_QUALITY_HIGH)
			bitmaps.append(wx.BitmapFromImage(bitmap))
			if image is imageList[-1]:
				continue
			mask = wx.Mask(bitmaps[-1], wx.WHITE)
			bitmaps[-1].SetMask(mask)
			if "disabled" in image:
					bitmaps.append(wx.BitmapFromImage(bitmap))
		#bitmaps.append(bitmaps[-1])

		self.bitmaps = {"mbEnabled":bitmaps[0], "mbDisabled":bitmaps[1], "mbInUse":bitmaps[2], "mbMiniEnabled":bitmaps[3], "mbMiniDisabled":bitmaps[4], "mbMiniInUse":bitmaps[5],"tazEnabled": bitmaps[6], "tazDisabled":bitmaps[7], "tazInUse":bitmaps[8], "tazMiniEnabled":bitmaps[9], "tazMiniDisabled":bitmaps[10], "tazMiniInUse":bitmaps[11], "laptopEnabled":bitmaps[12], "laptopDisabled":bitmaps[13], "laptopInUse":bitmaps[14], "default":bitmaps[15]}		
		for key, value in self.bitmaps.iteritems():
			if "Disabled" in key:
				msg = "** OFFLINE **"
				self.WriteCaptionOnBitmap(self,msg,value,bmpFont, (2,2), wx.RED)
			elif "InUse" in key:
				msg = "** IN USE **"
				self.WriteCaptionOnBitmap(self,msg,value,bmpFont, (2,2), wx.RED)

# end of class MyApp

if __name__ == "__main__":
	app = MyApp(0)
	app.signOnFrame = MainWindow(None, envisionVersion)
	app.SetTopWindow(app.signOnFrame)
	app.signOnFrame.Show()
	app.frame = PrinterFrame(None)
	app.adminFrame = PrinterFrame(None,True)
	try:
		app.signOnFrame.socketWorker
	except Exception as e:
		#print e
		pass
	else:
		#pass
		app.signOnFrame.socketWorker.sendEvent(["EVT_CONNECT",MACHINENAME,"False","False"])
	app.signOnFrame.Refresh()
	#app.signOnFrame.panel.SetFocusIgnoringChildren()
	app.signOnFrame.SetFocus()
	#print wx.Window.FindFocus()
	#print app.signOnFrame.panel.AcceptsFocus()
	app.MainLoop()
