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

#import calls...pretty sure all of them are used
import os, time
import wx
import pysftp
import json
import sys
import datetime
from wx.lib.pubsub import pub
import wx.lib.agw.pybusyinfo as PBI
import socket, threading

#Version Tracking
version = "v1"
machineName="CASHIER"

if wx.Platform == "__WXMSW__":
	MSW = True
	GTK = False
else:
	GTK = True
	MSW = False

#set of global variables

#will the panel accept keyboard input?
acceptString = False 
#stores keyboard characters as they come in
inputList = []
now = datetime.datetime.now()
#time limit for the waivers...in days
timeLimit = 90

userIDnumber = None
#standard UCSD id length, including leading and trailing '$' from mag-reader
idLength = 11
envisionVersion = "EnVision Maker Studio (" +version + ")\n< " +machineName + " >"

serverAddress = 'envision-local'

disabled = False

class idleFrame(wx.Frame):
	def __init__(self,parent):
		"""Constructor"""
		wx.Frame.__init__(self, parent, style= wx.STAY_ON_TOP | wx.NO_BORDER | wx.FRAME_NO_TASKBAR, title="More Time?")
		panel = wx.Panel(self)
		
		self.idleMessage = "Do you need more time?\nProgram will exit in"
		self.idleText = wx.StaticText(self,label=self.idleMessage)
		self.idleMessageTime = 15
		self.timeText = wx.StaticText(self,label=str(self.idleMessageTime)+" seconds")
		self.timeFont = wx.Font(12,wx.FONTFAMILY_SWISS,wx.FONTSTYLE_NORMAL,wx.FONTWEIGHT_BOLD)
		self.timeText.SetFont(self.timeFont)
		self.timeText.SetForegroundColour((255,0,0))

		self.idleTimer = wx.Timer(self)
		self.Bind(wx.EVT_TIMER,self.idleUpdate,self.idleTimer)
		
		yesBtn = wx.Button(self, label="YES")
		exitBtn = wx.Button(self, label="EXIT")
		yesBtn.Bind(wx.EVT_BUTTON, self.onYes)
		exitBtn.Bind(wx.EVT_BUTTON, self.onExit)
		
		sizer = wx.BoxSizer(wx.VERTICAL)
		buttonSizer = wx.BoxSizer(wx.HORIZONTAL)
		flags = wx.ALL|wx.CENTER
		buttonSizer.Add(yesBtn,1,flags|wx.EXPAND,5)
		buttonSizer.Add(exitBtn,1,flags|wx.EXPAND,5)
		sizer.Add(self.idleText,1,flags|wx.ALIGN_CENTRE_HORIZONTAL,10)
		sizer.Add(self.timeText,1,flags|wx.ALIGN_CENTRE_HORIZONTAL,10)
		sizer.Add(buttonSizer,1,flags|wx.EXPAND,10)
		self.SetSizer(sizer)
		self.Layout()
		self.idleTimer.Start(1000)
	

	def alignToCenter(self,window):
		dw, dh = wx.DisplaySize()
		w, h = window.GetSize()
		x = dw/2 - w/2
		y = dh/2 - h/2
		window.SetPosition((x,y))
	def idleUpdate(self,event):
		if self.idleMessageTime > 0:
			self.idleMessageTime -= 1
			self.timeText.SetLabel(str(self.idleMessageTime)+" seconds")
		else:
			self.onExit(wx.EVT_BUTTON)
	def onExit(self,event):
		self.idleTimer.Stop()
		self.Destroy()
		
	def onYes(self,event):
		app.frame.timeFrame.inactiveCount = 0
		app.frame.timeFrame.timer.Start(5000)
		self.idleTimer.Stop()
		self.Destroy()

class OnScreenKB(wx.Frame):
	def __init__(self,parent,leadLabel="",trailLabel="", instructStr=""):
		wx.Frame.__init__(self, parent,style=wx.STAY_ON_TOP|wx.FRAME_NO_TASKBAR | wx.FRAME_FLOAT_ON_PARENT, title="KEYPAD", size=(400,600))
		panel = wx.Panel(self, size=(400,600))
		
		self.parent = parent
		self.gparent = self.parent.parent
		
		self.leadLabel = leadLabel
		self.trailLabel = trailLabel
		self.initialLabel = "----------"
		self.instructStr = instructStr
		
		
		self.instructions = wx.StaticText(panel, label=self.instructStr,style=wx.ALIGN_CENTRE_HORIZONTAL|wx.ST_NO_AUTORESIZE)
		self.instruxFont = wx.Font(16,wx.FONTFAMILY_SWISS,wx.FONTSTYLE_NORMAL,wx.FONTWEIGHT_BOLD)
		self.instructions.SetFont(self.instruxFont)
		
		self.inputNum = wx.StaticText(panel, label=self.initialLabel,style=wx.ALIGN_CENTRE_HORIZONTAL|wx.ST_NO_AUTORESIZE)
		self.inputNum.SetForegroundColour((255,0,0))
		self.inputFont = wx.Font(24,wx.FONTFAMILY_SWISS,wx.FONTSTYLE_NORMAL,wx.FONTWEIGHT_BOLD)
		self.inputNum.SetFont(self.inputFont)
		
		self.mainSizer = wx.BoxSizer(wx.VERTICAL)
		#self.btnBox = wx.StaticBox(panel)
		#self.btnSizer = wx.StaticBoxSizer(self.btnBox,wx.HORIZONTAL)
		self.btnSizer = wx.BoxSizer(wx.HORIZONTAL)
		self.mainGridSizer = wx.GridSizer(cols=3,hgap=5,vgap=5)
		
		
		self.numButtons=[]
		self.numButtons.append(wx.Button(panel, id=0, label="0"))
		self.numButtons[0].Bind(wx.EVT_BUTTON,self.updateLabel)
		for i in range (1,10):
			self.numButtons.append(wx.Button(panel, id=i, label=str(i)))
			self.numButtons[i].Bind(wx.EVT_BUTTON,self.updateLabel)
			self.mainGridSizer.Add(self.numButtons[i],1,wx.EXPAND)
		
		self.cancelBtn = wx.Button(panel, label="CANCEL")
		self.okBtn = wx.Button(panel, label="OK")		
		self.okBtn.Bind(wx.EVT_BUTTON, self.onOK)
		self.cancelBtn.Bind(wx.EVT_BUTTON, self.onClose)
		
		#self.btnSizer.AddSpacer(5)
		self.btnSizer.Add(self.cancelBtn,1,wx.EXPAND)
		self.btnSizer.AddSpacer(20)
		self.btnSizer.Add(self.okBtn,1,wx.EXPAND)
		self.mainSizer.AddSpacer(10)
		self.mainSizer.Add(self.instructions,0,wx.CENTER)
		self.mainSizer.AddSpacer(10)
		self.mainSizer.Add(self.inputNum,0, wx.CENTER)
		self.mainSizer.AddSpacer(10)
		self.mainSizer.Add(self.mainGridSizer,4,wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 10)
		self.mainSizer.AddSpacer(5)
		self.mainSizer.Add(self.numButtons[0],1,wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)
		self.mainSizer.AddSpacer(10)
		self.mainSizer.Add(self.btnSizer,1,wx.EXPAND|wx.LEFT|wx.RIGHT|wx.BOTTOM,10)
		self.mainSizer.AddSpacer(10)
		self.SetSizer(self.mainSizer)
		self.cancelBtn.SetBackgroundColour("Dim Grey")
		self.okBtn.SetBackgroundColour("Dim Grey")
		
		self.Centre()
		self.Layout()
	
	@classmethod
	def purchaseFunds(cls,parent):
		return cls(parent,"$",".00","How Much Money To Add?")
	@classmethod
	def useCode (cls,parent):
		return cls(parent,"","","Enter 6 Digit Class Code")
	
	
	def onOK(self,event):
		if self.leadLabel=="$":
			amount = self.inputNum.GetLabel()
			agreeMsg = "THIS IS THE SAME AS SWIPING A CREDIT CARD\n\nAnd will add "+amount+" to your balance"
			agreeDlg = wx.MessageDialog(self, agreeMsg, "PROCEED?", wx.YES | wx.NO | wx.ICON_EXCLAMATION | wx.CENTRE)
		else:
			code = self.inputNum.GetLabel()
			if len(code)<6:
				wx.MessageBox("Code needs to be 6 digits","ERROR!")
				return
			agreeMsg = "If you are not registered for this class:\n\nYOUR STUDENT ACCOUNT WILL BE CHARGED"
			agreeDlg = wx.MessageDialog(self, agreeMsg, "Are You Sure?", wx.YES | wx.NO | wx.ICON_EXCLAMATION | wx.CENTRE)			
		agreeDlg.SetYesNoLabels("Proceed","Cancel")
		result = agreeDlg.ShowModal()
		agreeDlg.Close()
		agreeDlg.Destroy()
		if result == wx.ID_NO:
			self.inputNum.SetLabel(self.initialLabel)
			self.Raise()
		elif result == wx.ID_YES:
			self.Destroy()
			if self.leadLabel=="$":
				self.gparent.socketWorker.sendEvent(["EVT_ADD_FUNDS",machineName,userIDnumber,amount[1:]])
			else:
				self.gparent.socketWorker.sendEvent(["EVT_ADD_CODE",machineName,userIDnumber,code])
	def onClose(self,event):
		self.parent.Show()
		self.parent.Raise()
		self.parent.panel.SetFocus()
		self.Destroy()
	
	def updateLabel(self,event):
		button = event.GetEventObject()
		buttonLabel = button.GetLabel()
		
		if self.inputNum.GetLabel() == self.initialLabel or self.inputNum.GetLabel()[:2]=="$0" :
			newLabel = self.leadLabel+buttonLabel+self.trailLabel
			self.inputNum.SetLabel(newLabel)
		elif len(self.inputNum.GetLabel()) < 6:
			if bool(self.leadLabel):
				self.inputNum.SetLabel(self.inputNum.GetLabel()[:2]+buttonLabel+self.trailLabel)
			else:
				self.inputNum.SetLabel(self.inputNum.GetLabel()+buttonLabel+self.trailLabel)
		else:
			self.inputNum.SetLabel(self.leadLabel+buttonLabel+self.trailLabel)
		self.Layout()
			
class MessageFrame(wx.Frame):
	def __init__(self,parent):
		"""Constructor"""
		#wx.Frame.__init__(self, parent, style=wx.STAY_ON_TOP | wx.NO_BORDER | wx.FRAME_NO_TASKBAR, title="Popup Frame")
		wx.Frame.__init__(self, parent, style=wx.STAY_ON_TOP | wx.FRAME_FLOAT_ON_PARENT, title="MESSAGE", size=(450,300))
		self.parent = parent
		self.panel = wx.Panel(self, style=wx.SUNKEN_BORDER,size=(450,300))
		msg = "THIS WHOLE MESSAGE IS MEANT FOR SIZING PURPOSES"
		
		self.instructions = wx.StaticText(self.panel, label=msg,style=wx.ALIGN_CENTRE_HORIZONTAL | wx.ALIGN_CENTRE)#, size=(400,100))
		self.instructions.SetForegroundColour((255,0,0))
		self.instructionsFont = wx.Font(18,wx.FONTFAMILY_SWISS,wx.FONTSTYLE_NORMAL,wx.FONTWEIGHT_BOLD)
		self.instructions.SetFont(self.instructionsFont)
		self.instructions.Wrap(400)
		#self.instructions.SetLabel(" ")
		
		self.msgIndex = 0
		self.msgList = []
		self.acceptedTOS = False
		
		self.exitBtn = wx.Button(self.panel, label="EXIT")
		self.actionBtn = wx.Button(self.panel, label="----")
		self.okBtn = wx.Button(self.panel, label="OK")
		
		self.okBtn.Bind(wx.EVT_BUTTON, self.onOK)
		self.actionBtn.Bind(wx.EVT_BUTTON,self.onClass)
		self.exitBtn.Bind(wx.EVT_BUTTON, self.onClose)
		
		self.actionBtn.Enable(False)
		
		# self.timer = wx.Timer(self)
		# self.Bind(wx.EVT_TIMER,self.UpdateEvent,self.timer)
		# self.timer2 = wx.Timer(self)
		# self.Bind(wx.EVT_TIMER, self.UpdateCountdown, self.timer2)
		
		sizerHor1 = wx.BoxSizer(wx.VERTICAL)
		sizerHor2 = wx.BoxSizer(wx.HORIZONTAL)
		mainSizer = wx.BoxSizer(wx.VERTICAL)
		
		#flags = wx.ALL|wx.CENTER
		#flags = wx.ALL|wx.CENTER
		#flags = wx.LEFT | wx.RIGHT | wx.CENTRE | wx.EXPAND
		flags = wx.CENTRE
		sizerHor2.AddSpacer(10)
		sizerHor2.Add(self.exitBtn, 1,wx.EXPAND)
		sizerHor2.AddSpacer(10)
		sizerHor2.Add(self.actionBtn, 1,wx.EXPAND)
		sizerHor2.AddSpacer(10)
		sizerHor2.Add(self.okBtn,1,wx.EXPAND)
		sizerHor2.AddSpacer(10)
		sizerHor1.Add(self.instructions, 1, flags, 10)
		
		
		#sizerVert.Add(sizerHor,0,flags,5)
		#mainSizer.AddStretchSpacer(prop=1)
		mainSizer.AddSpacer(20)
		mainSizer.Add(sizerHor1,1,wx.EXPAND|wx.CENTRE)
		mainSizer.AddSpacer(30)
		#mainSizer.AddStretchSpacer(prop=1)
		#mainSizer.AddSpacer(10)
		mainSizer.Add(sizerHor2,4,wx.EXPAND |wx.CENTRE)
		mainSizer.AddSpacer(10)
		
		
		#self.SetSizer(sizerVert)
		self.SetSizer(mainSizer)
		self.Centre()
		self.Layout()
		# self.timer.Start(10000)
		self.inactiveCount = 0
	
	def onOK(self,event):
		if self.msgList: 
			if self.acceptedTOS is False:
				if self.msgIndex < len(self.msgList)-1:
					self.msgIndex += 1
					self.showMessage(self.msgList[self.msgIndex])
					if self.msgIndex == len(self.msgList) - 1:
						self.exitBtn.SetLabel("REJECT")
						self.okBtn.SetLabel("ACCEPT")
				else:
					self.exitBtn.SetLabel("EXIT")
					self.okBtn.SetLabel("OK")
					self.acceptedTOS = True
					self.msgIndex = 0
					self.msgList = []
					self.showMessage("Thank You! Please press OK to continue")
			else:
				self.msgIndex += 1
				if self.msgIndex < len(self.msgList)-1:
					self.showMessage(self.msgList[self.msgIndex])
				elif self.msgIndex == len(self.msgList)-1:
					self.showMessage(self.msgList[self.msgIndex])
					self.actionBtn.SetLabel("CLASS")
					self.actionBtn.Enable(True)
				else:
					#self.Hide()
					self.kb=OnScreenKB.purchaseFunds(self)
					self.kb.Show()
					self.kb.Raise()

		else:
			#pass
			self.parent.socketWorker.sendEvent(["EVT_ADD_USER",machineName,userIDnumber,"False"])
	
	def onClass(self,event):
		#self.Hide()
		self.kb=OnScreenKB.useCode(self)
		self.kb.Show()
		self.kb.Raise()
	
	def showMessage(self,msg):
		self.instructions.SetLabel(msg)
		self.instructions.Wrap(400)
		self.instructions.Layout()
	def onClose(self,event):
		self.MakeModal(False)
		self.Destroy()
		app.frame.Raise()
		app.frame.panel.SetFocus()
		#time.sleep(1)
		# self.timer.Stop()
		# self.timer2.Stop()
		# if app.frame.seconds2Expire:
			# app.frame.branding.SetLabel("MACHINE IN USE: " + str(datetime.timedelta(seconds=app.frame.seconds2Expire))+'\n')
			# #app.frame.branding.SetFont(app.frame.countDownFont)
			# app.frame.Layout()
			# app.frame.expireTimer.Start(1000)

class SocketThread(threading.Thread):
	def __init__(self,parent,message):
		threading.Thread.__init__(self)
		self.parent=parent
		self.message=message
	def run(self):
		pass
	def sendEvent(self,eventPacket):
		message = "Contacting Server..."
		busyMsg = PBI.PyBusyInfo(message, parent=None, title=" ")
		wx.Yield()
		packet = [x.upper() for x in eventPacket]
		packetStr = ' '.join(packet)
		try:
			client = socket.create_connection((serverAddress, 6969))
			client.send(packetStr)
			reply=(client.recv(1024)).split()
			#I might need to close the client for other machines to work?
		except Exception, msg:
			del busyMsg
			wx.CallAfter(self.parent.socketClosed,wx.EVT_CLOSE,msg)
			
		else:
			del busyMsg
			if len(reply) == 3:
				if reply[0] == packet[0] and reply[1]:
					pub.sendMessage("socketListener", sent=packet, reply=reply)
			else:
				wx.CallAfter(self.parent.socketClosed,wx.EVT_CLOSE,"BAD-FORMED REPLY")
	def closeSocket(self):
		try:
			client.shutdown(socket.SHUT_RDWR)
			client.close()
		except Exception, msg:
			wx.CallAfter(self.parent.socketClosed,wx.EVT_CLOSE,msg)

class CustomDialog(wx.Frame):
	"""
	I'll use this one day make my error dialogs. Don't care rightn now
	"""
	
	def __init__(self,parent,message,discardBtn=False,acceptBtn=True):
		wx.Frame.__init__(self, parent, style=wx.STAY_ON_TOP|wx.FRAME_NO_TASKBAR, title="MESSAGE", size=(400,200))
		self.parent = parent
		panel = wx.Panel(self, style=wx.SUNKEN_BORDER,size=(400,200))
		
		self.msg = wx.StaticText(panel, label=msg,style=wx.ALIGN_CENTRE_HORIZONTAL|wx.ST_NO_AUTORESIZE)
		self.msgFont = wx.Font(16,wx.FONTFAMILY_SWISS,wx.FONTSTYLE_NORMAL,wx.FONTWEIGHT_BOLD)
		self.msg.SetFont(self.msgFont)
		self.msg.Wrap(350)
		
		
			
#create the frame, inside the app, that holds the panel, and all of the functionality
class MainWindow(wx.Frame):
	def __init__(self, parent, title):
		#i don't know what this does
		self.dirname = ' '
		styleFlags = wx.STAY_ON_TOP | wx.NO_BORDER | wx.FRAME_NO_TASKBAR
		if GTK:
			styleFlags = wx.DEFAULT_FRAME_STYLE #| wx.FRAME_NO_TASKBAR
		wx.Frame.__init__(self, parent, title = title, style=styleFlags)
		
		self.isAdmin = False
		self.bi = None
		#bind a close event to the function
		self.Bind(wx.EVT_CLOSE, self.OnClose)
		#sizers for centering the static text 
		self.mainSizer = wx.BoxSizer(wx.HORIZONTAL)
		self.layoutSizer = wx.BoxSizer(wx.VERTICAL)
		self.brandingLabel = envisionVersion
		
		#update users every 10 1/2 minutes. Sounds like it's often enough
		self.userTimer = wx.Timer(self)
		self.Bind(wx.EVT_TIMER,self.updateUsers,self.userTimer)
		self.userTimer.Start(10 * 60 * 1050)
		self.branding = wx.StaticText(self, label = self.brandingLabel, style = wx.ALIGN_CENTRE_HORIZONTAL)
		if disabled:
			self.bmp = wx.Bitmap("maintenanceLarge.jpg")
			self.isPrinter = True
			self.brandingLabel = machineName + " is currently not working\nThank you for your patience"
			self.brandingFont = wx.Font(20, wx.DECORATIVE, wx.ITALIC, wx.LIGHT)
			self.userTimer.Stop()

		else:
			#self.bmp = wx.Bitmap("front-desk.jpg")
			self.bmp = wx.Bitmap("cashier_bg.jpg")
			self.brandingFont = wx.Font(20, wx.DECORATIVE, wx.ITALIC, wx.BOLD)
		
		self.branding.SetFont(self.brandingFont)
		#after I call a program from the panel, the executes when the program closes
		
		dw, dh = wx.DisplaySize()
		w, h = self.branding.GetSize()
		y = dh/2 - h/2
		borderWidth = 20
		
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

		pub.subscribe(self.socketListener, "socketListener")
		
		self.ShowFullScreen(True)
		self.socketWorker = SocketThread(self,None)
		self.socketWorker.start()
		#self.Show()
		
		if GTK:
			self.panel = wx.Panel(self, wx.ID_ANY)
			self.panel.Bind(wx.EVT_CHAR, self.onKeyPress)
			self.panel.SetFocus()
		#MSW doesn't like key capture in panels
		elif MSW:
			self.Bind(wx.EVT_CHAR, self.onKeyPress)
			self.SetFocus()
		else:
			wx.MessageBox('Platform Not Supported','ERROR')
			self.Destroy()
			sys.exit(1)
		
	def socketListener(self, sent=None, reply=None):
		command = sent[0]
		user = sent[1]
		machine = sent[2]
		machineTime = sent[3]
		
		event = reply[0]
		status = reply[1]
		statusInfo = reply[2]
		if status == "OK":
			self.processReply(event,statusInfo)
		elif status == "DENY":
			self.processDeny(event, statusInfo)
	
	def processReply(self, command, info):
		if command == "EVT_CHECKID":
			if info == "ADMIN":
				if disabled:
					action = self.machineStatus(False)
					return
				else:
					self.startMessageFrame()
					self.socketWorker.sendEvent(["EVT_START",machineName,userIDnumber,"False"])
			else:
				self.startMessageFrame()
				self.socketWorker.sendEvent(["EVT_START",machineName,userIDnumber,"False"])
		elif command == "EVT_START":
			if info != "UNKNOWN":
				self.machineStart(True, info)
			elif info == "UNKNOWN":
				self.machineStart(False, info)
		else:
			if command == "EVT_CONNECT":
				return
			if command == "EVT_ADD_USER":
				wx.MessageBox("You've been added!\n\n$5.00 has also been added to your balance","SUCCESS")
			elif command == "EVT_ADD_CODE":
				wx.MessageBox("SUCCESS!\n\nYour balance is now: $"+info,"SUCCESS")
			elif command == "EVT_ADD_FUNDS":
				wx.MessageBox("SUCCESS!\n\nYour balance is now: $"+info,"SUCCESS")
			self.msgFrame.onClose(wx.EVT_BUTTON)
			self.startMessageFrame()
			self.socketWorker.sendEvent(["EVT_START",machineName,userIDnumber,"False"])
	def processDeny(self,command, error):
		if error == "DBERROR":
			errorMsg = "There is a problem with the DATABASE Connection. Please see an administrator"
		else:
			if command == "EVT_ADD_FUNDS":
				errorMsg = "Your balance cannot exceed $100.\n$"+error+" was successfully added"
			elif command == "EVT_ADD_CODE":
				if error == "MAX":
					errorMsg = "Adding this code would make your balance over the maximum\n\nPlease try again after you've used some funds"
				elif error == "ZERO":
					errorMsg = "No funds are available for this class\n\n Please notify your instructor"
				elif error == "USED":
					errorMsg = "You have already used this course code\n\nNo funds have been added"
				
				else:
					errorMsg = "That class code is not valid\n\n "
			else:
				errorMsg = "UNKNOWN ERROR. Please see an admin"
		errorDlg = wx.MessageDialog(self, errorMsg, "ERROR", wx.OK | wx.ICON_ERROR | wx.CENTER)
		result = errorDlg.ShowModal()
		if result == wx.ID_OK:
			errorDlg.Destroy()
			self.msgFrame.onClose(wx.EVT_BUTTON)
			self.startMessageFrame()
			self.socketWorker.sendEvent(["EVT_START",machineName,userIDnumber,"False"])
			
	
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
		if len(inputList) > 50:
			inputList=[]
			return
		keycode = event.GetKeyCode()
		if keycode == wx.WXK_ESCAPE:
			self.requestExit()
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
	
	def requestExit(self):
		exitDlg = wx.PasswordEntryDialog(self, "Enter Code To Exit", "EXIT", "", wx.OK | wx.CANCEL)
		result = exitDlg.ShowModal()
		if exitDlg.GetValue() == '111999':
			exitDlg.Destroy()
			self.OnClose(wx.EVT_CLOSE)
		else:
			exitDlg.Destroy()
	
	def OnEraseBackground(self, evt):
		dc = evt.GetDC()
		if not dc:
			dc = wx.ClientDC(self)
			rect = self.GetUpdateRegion().GetBox()
			dc.SetClippingRect(rect)
		dc.Clear()
		dc.DrawBitmap(self.bmp, 0, 0)
			
	def idEnter(self, idInput):
		global userIDnumber
		match = False
		idString = ""
		if (idInput.startswith('$') and idInput.endswith('$')):
			idChars = list(idInput)
			if idChars[2] == '9':
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
			
			#for i in range(2,idLength):
			#	idString = idString + idChars[i]
			userIDnumber = idString
			self.socketWorker.sendEvent(["EVT_CHECKID",machineName,userIDnumber,"False"])
		else:
			return
	def startMessageFrame(self):
		self.msgFrame = MessageFrame(self)
		self.msgFrame.Show()
		self.msgFrame.panel.SetFocus()
		self.msgFrame.MakeModal(True)
		self.msgFrame.showMessage("Contacting Sever...")
	def machineStatus(self,enabled):
		if enabled:
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
	def changeStatus(self,enabled):
		global disabled
		if enabled:
			disabled = True
			self.userTimer.Stop()
			self.bmp = wx.Bitmap("maintenanceLarge.jpg")
			brandingLabel = machineName + " is currently not working\nThank you for your patience"
		elif not enabled:
			disabled = False
			self.userTimer.Start(10 * 60 * 1050)
			brandingLabel = envisionVersion
			self.bmp = wx.Bitmap("cashier_bg.jpg")
		
		brandingFont = wx.Font(16, wx.DECORATIVE, wx.ITALIC, wx.LIGHT)
		dc = wx.ClientDC(self)
		rect = self.GetUpdateRegion().GetBox()
		dc.SetClippingRect(rect)
		dc.Clear()
		dc.DrawBitmap(self.bmp, 0, 0)
		self.branding.SetFont(brandingFont)
		self.branding.SetLabel(brandingLabel)
		self.Layout()
		self.Refresh()
		return(True)

	def machineStart(self,userExists, balance):
		if userExists:
			self.msgFrame.msgList = ["Your Balance is: $"+balance+"\n\nPress 'CLASS' to add Code\n'$$$' to add money"]
			self.msgFrame.acceptedTOS = True
			self.msgFrame.actionBtn.Enable(True)
			self.msgFrame.actionBtn.SetLabel("CLASS")
			self.msgFrame.okBtn.SetLabel("$$$")
			self.msgFrame.showMessage(self.msgFrame.msgList[0])
			self.msgFrame.Layout()
		else:
			self.msgFrame.msgList = ["As a new user, you will have to accept the terms of use. Press OK to advance","1) I understand that any funds I purchase will be charged to my UCSD account", "2) If I'm not registered for a 'COURSE CODE', my UCSD account will be charged", "3) If I do not use all of my funds, I will still be charged the full amount I purchased", "4) Refunds will not be issued (including failed prints)", "If you agree to these terms, select ACCEPT, otherwise select REJECT"]
			self.msgFrame.showMessage(self.msgFrame.msgList[0])
			self.msgFrame.Layout()
		
	def restrictedID(self,reason):
		if (reason == 'expired'):
			errorMessage = 'Your Certification has expired! (>90 days)\n\nPlease redo Responsbility Contract and/or Training'
		elif (reason.startswith('quota')):
			errorMessage = 'You have been SUSPENDED from the EnVision Maker Studio\n\nPlease see an administrator if this is an error'
		elif (reason == 'not found'):
			errorMessage = 'Responsibility Contract is not complete\n\nPlease visit envision.ucsd.edu'
		else:
			errorMessage = 'Unknown Error\n\nPlease see an administrator'
		errorDlg = wx.MessageDialog(self, errorMessage, "ERROR", wx.OK | wx.ICON_ERROR)
		result = errorDlg.ShowModal()
		if result == wx.ID_OK:
			errorDlg.Destroy()
	
	def updateUsers(self,event):
		global uniquePIDs
		global uniqueEIDs
		global userList
		global now

		if os.path.isfile(lockFile):
			while os.path.isfile(lockFile):
				continue
		with open(userFile,'r') as dataFile:
			lastMod = time.ctime(os.path.getmtime(userFile))
			userList = json.load(dataFile) # load json info into a list of dicts

		#populate lists of groups and ids from the larger list (easier/faster to work with)
		uniquePIDs = []
		uniqueEIDs = []
		for i in range(len(userList)):
			uniquePIDs.append(userList[i]['PID'])
			if not userList[i]['uceno'] =='0':
				uniqueEIDs.append(userList[i]['uceno'])
			else:
				uniqueEIDs.append("NO-EID")
		
		now = datetime.datetime.now()

		envisionVersion = "EnVision Maker Studio (" +version + ")\n<" +machineName + ">\n- user database updated: " +lastMod[4:16] +" -"
		self.branding.SetLabel(envisionVersion)

	def socketClosed(self, event, errorMsg):
		self.Show()
		self.Raise()
		errorMsg = str(errorMsg)
		errorDlg = wx.MessageDialog(self, "Connection to SERVER failed!\n\n"+errorMsg+"\n\nPlease see an Administrator", "ERROR", wx.OK | wx.ICON_ERROR | wx.CENTER)
		result = errorDlg.ShowModal()
		if result == wx.ID_OK:
			errorDlg.Destroy()

	def OnClose(self, event):
		print ("Closing up...")
		self.Destroy()	
	
class EnVisionApp(wx.App):
    def OnInit(self):
		self.name = "EnVision-Cashier"
		self.instance = wx.SingleInstanceChecker(self.name)
		if self.instance.IsAnotherRunning():
			wx.MessageBox("Another instance is running", "ERROR")
			return False
		self.frame = MainWindow(None, envisionVersion)
		self.frame.Show()
		self.frame.panel.SetFocus()
		self.pid = os.getpid()
		with open('taskPID.txt','wb+') as pidFile:
			pidFile.write(str(os.getpid())+'\n')
		try:
			self.frame.socketWorker
		except Exception as e:
			wx.MessageBox("Failed to Contact Server\nPlease see an Admin","ERROR")
		else:
			self.frame.socketWorker.sendEvent(["EVT_CONNECT",machineName,"False","False"])
		return True
app = EnVisionApp(False)
app.MainLoop()
