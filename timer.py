#! /usr/bin/env python
"""
EnVision User Management System (EUMS)
Machine Time-Out Script
The EnVision Arts and Engineering Maker Studio
UC San Diego
Jacobs School of Engineering
Jesse DeWald
April 2016
All Rights Reserved
"""

#import calls...pretty sure all of them are used
import wx, sys
import RPi.GPIO as GPIO
import datetime

if len(sys.argv) > 1:
	machineName = sys.argv[1]
	#enables debug features (actually disables obnnoxious features while debugging)
	if machineName == "debug":
		debug = True
	else:
		debug = False
else:
	machineName = 'no_machine_name'

debug = False
laser = False
vacuum = False
if not debug:
	GPIO.setmode(GPIO.BOARD)
	if machineName.startswith('laser'):
		laser = True
		steadyRed = 35
		flashRed = 36
		green = 31
		siren = 32
		GPIO.setup((steadyRed,flashRed,green,siren),GPIO.OUT)
		GPIO.output((flashRed,siren),True)
		GPIO.output((steadyRed,green),False)
	else:
		vacuum = True
	startup = 40
	GPIO.setup((startup),GPIO.OUT)
	GPIO.output((startup,),True)
if vacuum:
	minutesStart = 10
	seconds = 0
	branding = "The EnVision Maker Studio\nVacuum Former "
elif laser:
	minutesStart = 3
	seconds = 0
	branding = "The EnVision Maker Studio\nLaser Cutter "
if debug:
	branding = branding + "DEBUG"

minutes = minutesStart
endHour = 21

class LaserWindow(wx.Frame):
	def __init__(self, parent, title):
		#i don't know what this does
		self.dirname = ' '
		wx.Frame.__init__(self, parent, title = title)
		#bind a close event to the function
		self.Bind(wx.EVT_CLOSE, self.OnClose)
		#sizers for centering the static text 
		self.mainSizer = wx.BoxSizer(wx.HORIZONTAL)
		self.layoutSizer = wx.BoxSizer(wx.VERTICAL)
		self.endButton = wx.Button(self, id=2, label=" END ")
		self.restartButton = wx.Button(self, id=3, label=" RESTART TIMER")
		self.endButton.Bind(wx.EVT_BUTTON, self.EndAsk)
		self.restartButton.Bind(wx.EVT_BUTTON, self.Restart)
		self.timer = wx.Timer(self)
		self.Bind(wx.EVT_TIMER,self.UpdateEvent,self.timer)
		#static text of the branding and version number
		self.branding = wx.StaticText(self, label = branding+"\n"+str(minutes)+":"+"%02d"%seconds,\
		style = wx.ALIGN_CENTRE_HORIZONTAL)
		self.brandingFont = wx.Font(26, wx.DECORATIVE, wx.ITALIC, wx.BOLD)
		self.branding.SetFont(self.brandingFont)
		self.layoutSizer.Add(self.endButton,2,wx.SHAPED | wx.ALIGN_CENTER | wx.TOP | wx.LEFT, wx.RIGHT,20)
		self.layoutSizer.Add(self.branding, 1, wx.ALIGN_CENTER | wx.ALL, 10)
		self.layoutSizer.Add(self.restartButton,2,wx.SHAPED | wx.ALIGN_CENTER | wx.BOTTOM | wx.LEFT, wx.RIGHT,20)
		
		self.mainSizer.Add(self.layoutSizer, 1, wx.ALIGN_CENTER)
		self.endButton.SetForegroundColour("red")
		self.endButton.SetFont(self.brandingFont)
		self.restartButton.SetForegroundColour("green")
		self.restartButton.SetFont(self.brandingFont)
		
		if laser:
			self.checkTimer = wx.Timer(self)
			self.Bind(wx.EVT_TIMER,self.CheckTime, self.checkTimer)
			self.checkTimer.Start(10, True)
		
		#more layout stuff...maybe not needed now that everything is fullscreen
		self.SetSizer(self.mainSizer)
		self.Centre()
		self.Layout()
		self.ShowFullScreen(True)
		#self.Show()
		
		self.timer.Start(1000)
	
	def CheckTime(self, event):
		now = datetime.datetime.now()
		day = now.weekday()
		hour = now.hour
		minute = now.minute
		if hour >= endHour: #or day >= 5:
			self.AfterHours()
		if self.checkTimer.IsOneShot():
			if 0 < minute < 30:
				self.checkTimer.Start((30 - minute) * 60 * 1000, True)
				#print "next timer in " + str(30 - now.minute) + " minute"
			elif 30 < minute < 60:
				self.checkTimer.Start((60 - minute) * 60 * 1000, True)
				#print "next timer in " + str(30 - now.minute) + " minutes"
			else:
				self.checkTimer.Start(30 * 60 * 1000)
				#print "main timer started"
	def AfterHours(self):
		if not debug:
			GPIO.output(startup,False)
			GPIO.output(green,True)
			GPIO.output(steadyRed,True)
			#GPIO.output(relay2Pin,False)
			GPIO.cleanup()
		agreeDlg = wx.MessageDialog(self, "The EnVision Laser Cutter will not operate after 9pm or on weekends", "SHUTTING DOWN", wx.ICON_EXCLAMATION | wx.OK | wx.CENTRE)
		result = agreeDlg.ShowModal()
		agreeDlg.Close()
		agreeDlg.Destroy()
		if result == wx.ID_OK:
			self.Destroy()
	def EndAsk (self,event):
		agreeDlg = wx.MessageDialog(self, "ARE YOU SURE?", "SHUT DOWN", wx.ICON_EXCLAMATION | wx.OK | wx.CENTRE)
		result = agreeDlg.ShowModal()
		agreeDlg.Close()
		agreeDlg.Destroy()
		if result == wx.ID_OK:
			self.OnClose(wx.EVT_CLOSE)
		else:
			return
	
	def Restart(self,event):
		global minutes, seconds
		self.timer.Stop()
		minutes=minutesStart
		seconds=0
		if not debug and laser:
			GPIO.output(flashRed,True)
			GPIO.output(siren,True)
		self.branding.SetLabel(branding+"\n"+str(minutes)+":"+"%02d"%seconds)
		self.timer.Start(1000)
		
	def OnClose(self, event):
		if not debug:
			if laser:
				GPIO.output(green,True)
				GPIO.output(steadyRed,True)
			GPIO.output(startup,False)
			GPIO.cleanup()
		self.Destroy()	
	def UpdateEvent(self,event):
		global minutes, seconds
		if seconds == 0:
			if minutes > 0:
				minutes -= 1
				seconds = 59
			else:
				self.OnClose(wx.EVT_CLOSE)
		else:
			seconds -= 1
			if not debug:
				if minutes < 1 and seconds == 30:
					GPIO.output(flashRed,False)
				elif minutes < 1 and seconds == 15:
					GPIO.output(siren,False)
		self.branding.SetLabel(branding+"\n"+str(minutes)+":"+"%02d"%seconds)
		

class TimerApp(wx.App):
    def OnInit(self):
        self.name = "Laser Timer"
        self.instance = wx.SingleInstanceChecker(self.name)
        if self.instance.IsAnotherRunning():
            wx.MessageBox("Another instance is running", "ERROR")
            return False
        frame = LaserWindow(None, "EnVision Laser Cutter")
        frame.Show()
        return True
		
app = TimerApp(False)
app.MainLoop()
