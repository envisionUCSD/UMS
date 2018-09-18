#! /usr/bin/env python
"""
EnVision Class Scheduling System
The EnVision Arts and Engineering Maker Studio
UC San Diego
Jacobs School of Engineering
Jesse DeWald
April 2017
All Rights Reserved
"""

import wx, os, datetime, json, pysftp,sys, MySQLdb, time
import  wx.lib.buttons  as  GenButtons

if os.path.isfile('./passList.txt'):
	with open('passList.txt','r') as passFile:
		try:
			passDict = json.load(passFile) # load json info into a list of dicts
		except: 
			print "Error loading password file"
			sys.exit(1)
else:
	print "Password file does not exist"
	sys.exit(1)


class MainWindow(wx.Frame):
	def __init__(self, parent, title):
		wx.Frame.__init__(self, parent, title = title)
		self.panel = wx.Panel(self, style=wx.SUNKEN_BORDER)
		now = datetime.datetime.now()
		self.today = now.strftime(": %m/%d")
		self.dow = now.weekday()
		
		self.mainSizer = wx.BoxSizer(wx.VERTICAL)

		
		self.days = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]
		
		self.mainGridSizer = wx.GridSizer(cols=len(self.days),hgap=10,vgap=5)
		self.dayLabelSizer = wx.GridSizer(cols=len(self.days),hgap=0,vgap=0)
		self.dayLabels = []
		self.hours = []
		self.buttons = []
		self.dayBox = {}
		self.dayBoxSizer = {}
		self.hourGridSizer = {}
		self.hourBoxSizer = {}
		self.changesMade = False
		self.legendSizer = wx.BoxSizer(wx.HORIZONTAL)
		
		for day in self.days:
			tempBox=(wx.BoxSizer(wx.HORIZONTAL))
			tempBox.AddStretchSpacer(prop=1)
			dayLabel = day+(now+datetime.timedelta(days=self.days.index(day))).strftime(": %m/%d")
			self.dayLabels.append(wx.StaticText(self.panel,-1,dayLabel,style = wx.ALIGN_CENTER_HORIZONTAL))
			dayLabelFont = wx.Font(16,wx.FONTFAMILY_SWISS,wx.FONTSTYLE_NORMAL,wx.FONTWEIGHT_BOLD)
			self.dayLabels[-1].SetFont(dayLabelFont)
			tempBox.Add(self.dayLabels[-1],0,wx.EXPAND | wx.ALIGN_CENTER | wx.ALIGN_CENTER_HORIZONTAL | wx.CENTRE)
			tempBox.AddStretchSpacer(prop=1)
			self.dayLabelSizer.Add(tempBox,1,wx.EXPAND | wx.ALIGN_CENTER | wx.ALIGN_CENTER_HORIZONTAL | wx.CENTRE)

		openTime = datetime.datetime.strptime('0800', '%H%M')
		self.hours.append(openTime.strftime('%H%M'))
		hoursOpen = 13
		timeStep = 15
		lastBtn = str(60-timeStep)
		for i in range(timeStep,60*hoursOpen,timeStep):
			self.hours.append((openTime+datetime.timedelta(minutes=i)).strftime('%H%M'))
		self.closeTime = (datetime.datetime.strptime(self.hours[-1],'%H%M') + datetime.timedelta(minutes=timeStep)).strftime('%H%M')
		
		for day in self.days:
			self.dayBox[day] = wx.StaticBox(self.panel, label= "")
			self.dayBoxSizer[day] = wx.StaticBoxSizer(self.dayBox[day],wx.VERTICAL)
			self.dayBoxSizer[day].AddSpacer(10)
			self.hourGridSizer[day] = wx.GridSizer(cols=1,vgap=10, hgap=0)
			for hour in self.hours:
				if hour[2:] == '00':
					self.hourBoxSizer[day + ':' + hour[:2]+'00']= wx.GridSizer(cols=4,vgap=0)
				b = GenButtons.GenButton(self.panel,-1,hour)
				b.SetBezelWidth(0)
				b.SetUseFocusIndicator(False)
				b.SetFont(wx.Font(10, wx.SWISS, wx.NORMAL, wx.BOLD, False))
				self.buttons.append(b)
				self.hourBoxSizer[day + ':' + hour[:2]+'00'].Add(self.buttons[-1],1,wx.EXPAND | wx.LEFT , 1)
				self.buttons[-1].Enable(False)
				if hour[2:] == lastBtn:
					self.hourGridSizer[day].Add(self.hourBoxSizer[day + ':' + hour[:2]+'00'], 1, wx.EXPAND)
			self.dayBoxSizer[day].Add(self.hourGridSizer[day],1,wx.EXPAND)
			self.mainGridSizer.Add(self.dayBoxSizer[day],1,wx.EXPAND)	

		resButton = GenButtons.GenButton(self.panel,-1,"RESERVED")
		resButton.SetBezelWidth(0)
		resButton.SetUseFocusIndicator(False)
		resButton.SetFont(wx.Font(10, wx.SWISS, wx.NORMAL, wx.BOLD, False))
		resButton.SetBackgroundColour("red")
		resButton.SetForegroundColour(wx.WHITE)
		resButton.SetMinSize(wx.DefaultSize)
		resButton.Bind(wx.EVT_BUTTON,self.refresh)
		
		availButton = GenButtons.GenButton(self.panel,-1,"AVAILABLE")
		availButton.SetBezelWidth(0)
		availButton.SetUseFocusIndicator(False)
		availButton.SetFont(wx.Font(10, wx.SWISS, wx.NORMAL, wx.BOLD, False))
		availButton.SetBackgroundColour("forest green")
		availButton.SetForegroundColour(wx.WHITE)
		
		tempBox=(wx.BoxSizer(wx.HORIZONTAL))
		updateTime = "Last Updated @ " + now.strftime("%H:%M")
		self.updateText=(wx.StaticText(self.panel,-1,updateTime,style = wx.ALIGN_CENTER_HORIZONTAL))
		updateFont = wx.Font(12,wx.FONTFAMILY_SWISS,wx.FONTSTYLE_ITALIC,wx.FONTWEIGHT_NORMAL)
		self.updateText.SetFont(updateFont)
		
		
		self.legendSizer.AddStretchSpacer(prop=1)
		self.legendSizer.Add(resButton,1,wx.EXPAND|wx.ADJUST_MINSIZE)
		self.legendSizer.Add(wx.Size(100,0), 0)
		self.legendSizer.Add(self.updateText,0,wx.EXPAND | wx.ALIGN_CENTER | wx.ALIGN_CENTER_HORIZONTAL | wx.CENTRE)
		# self.legendSizer.AddStretchSpacer(prop=1)
		self.legendSizer.Add(wx.Size(100,0), 0) #this is a spacer --AddSpacer adds space in BOTH directions! ugh.
		self.legendSizer.Add(availButton,1,wx.EXPAND|wx.ADJUST_MINSIZE)
		self.legendSizer.AddStretchSpacer(prop=1)

		self.mainSizer.Add(wx.Size(0,10), 0)
		self.mainSizer.Add(self.dayLabelSizer,0,wx.EXPAND)
		self.mainSizer.Add(self.mainGridSizer,1,wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM,10)
		self.mainSizer.Add(wx.Size(0,10), 0)
		self.mainSizer.Add(self.legendSizer,0,wx.EXPAND)
		self.mainSizer.Add(wx.Size(0,20), 0)
		
		self.panel.Bind(wx.EVT_CHAR, self.onKeyPress)
		self.panel.SetFocus()
		
		self.mainSizer.SetSizeHints(self)
		self.panel.SetSizerAndFit(self.mainSizer)
		self.Centre()
		self.Layout()
		self.refreshTimer = wx.Timer(self)
		self.Bind(wx.EVT_TIMER,self.refresh, self.refreshTimer)
		#self.refreshTimer.Start(10, True)
	
		#self.Show()
		self.ShowFullScreen(True)
		
		
	def refresh(self,event):
		now = datetime.datetime.now()
		print "fired at " +str(now.minute)
		self.Freeze()
		dbHandler.setOpenAccess()		
		self.adjustDays()
		updateTime = "Last Updated @ " + now.strftime("%H:%M")
		self.updateText.SetLabel(updateTime)
		self.panel.Update()
		self.panel.Refresh()
		self.panel.Layout()
		self.Thaw()
		if self.refreshTimer.IsRunning() is False:
			if now.minute % 16 == 0:
				self.refreshTimer.Start(15 * 60 * 1000)
			else:
				nextFire = 16 - (now.minute % 16)
				self.refreshTimer.Start(nextFire * 60 * 1000, True)
		time.sleep(2)
		self.takeScreenShot()
		self.panel.SetFocus()
	def takeScreenShot(self):
		""" Takes a screenshot of the screen at give pos & size (rect). """
		print 'Taking screenshot...'
		rect = self.GetRect()
		# see http://aspn.activestate.com/ASPN/Mail/Message/wxpython-users/3575899
		# created by Andrea Gavana

		# adjust widths for Linux (figured out by John Torres 
		# http://article.gmane.org/gmane.comp.python.wxpython/67327)
		if sys.platform == 'linux2':
			client_x, client_y = self.ClientToScreen((0, 0))
			border_width = client_x - rect.x
			title_bar_height = client_y - rect.y
			rect.width += (border_width * 2)
			rect.height += title_bar_height + border_width

		#Create a DC for the whole screen area
		dcScreen = wx.ScreenDC()

		#Create a Bitmap that will hold the screenshot image later on
		#Note that the Bitmap must have a size big enough to hold the screenshot
		#-1 means using the current default colour depth
		bmp = wx.EmptyBitmap(rect.width, rect.height)

		#Create a memory DC that will be used for actually taking the screenshot
		memDC = wx.MemoryDC()

		#Tell the memory DC to use our Bitmap
		#all drawing action on the memory DC will go to the Bitmap now
		memDC.SelectObject(bmp)

		#Blit (in this case copy) the actual screen on the memory DC
		#and thus the Bitmap
		memDC.Blit( 0, #Copy to this X coordinate
					0, #Copy to this Y coordinate
					rect.width, #Copy this width
					rect.height, #Copy this height
					dcScreen, #From where do we copy?
					rect.x, #What's the X offset in the original DC?
					rect.y  #What's the Y offset in the original DC?
					)

		#Select the Bitmap out of the memory DC by selecting a new
		#uninitialized Bitmap
		memDC.SelectObject(wx.NullBitmap)

		img = bmp.ConvertToImage()
		fileName = "./schedule.png"
		img.SaveFile(fileName, wx.BITMAP_TYPE_PNG)
		print '...saving as png!'
		self.uploadFile()
	def uploadFile(self):
		try:
			srv = pysftp.Connection(host='envision-local',username=passDict['envision-user'],password=passDict['envision-pass'])
			target = ('/home/e4ms/job_tracking/images')
			srv.chdir(target)
			try:
				srv.put('./schedule.png')
			except:
				pass
			srv.close()
		except Exception as e:
			print ("Server Connection FAILED", e)
		
	def onKeyPress(self, event):
		keycode = event.GetKeyCode()
		if keycode == wx.WXK_ESCAPE:
			self.Destroy()
		else:
			return
	
	def adjustDays(self):
		now = datetime.datetime.now()
		self.today = now.strftime("-%m/%d")
		self.dow = now.weekday()
		#self.Freeze()

		for i in range (len(self.mainGridSizer.GetChildren()),0,-1):
			self.mainGridSizer.Hide(i-1)
			self.mainGridSizer.Detach(i-1)

		for i in range (self.dow, len(self.days)):
			self.mainGridSizer.Add(self.dayBoxSizer[self.days[i]],1,wx.EXPAND)
			dlabel = self.days[i]+(now+datetime.timedelta(days=i-self.dow)).strftime(": %m/%d")
			self.dayLabels[i-self.dow].SetLabel(dlabel)
		for i in range (0, self.dow):
			offset = len(self.days) - self.dow
			self.mainGridSizer.Add(self.dayBoxSizer[self.days[i]],1,wx.EXPAND)
			dlabel = self.days[i]+(now+datetime.timedelta(days=i+offset)).strftime(": %m/%d")
			self.dayLabels[i+offset].SetLabel(dlabel)
		self.mainGridSizer.ShowItems(True)

class EnVisionScheduling(wx.App):
	def OnInit(self):
		self.name = "EnVision-LaserScheduling"
		self.instance = wx.SingleInstanceChecker(self.name)
		if self.instance.IsAnotherRunning():
			wx.MessageBox("Another instance is running", "ERROR")
			return False
		self.frame = MainWindow(None, "EnVision Laser Schedule")
		self.frame.Show()
		return True
	
class DatabaseHandler():
	def __init__(self):
		self.openAccess = {}	
		for i in range (0,7):
			self.openAccess[str(i)]=[]
	
	def loadOpenAccess(self):
		db = MySQLdb.connect(host="envision-local.dynamic.ucsd.edu",user=passDict['envision-user'],passwd=passDict['envision-pass'],db="envision_control")
		db.autocommit(True)
		cur = db.cursor()
		query = "SELECT day,startTime,endTime FROM oa_hours"
		cur.execute(query)
		results = cur.fetchall()
		for result in results:
			if result[0] in self.openAccess:
				self.openAccess[result[0]].append([])
				self.openAccess[result[0]][-1].extend((result[1],result[2]))
		db.close()
	
	def setOpenAccess(self):
		self.loadOpenAccess()
		reservedDict = self.getReservedTimes()
		if self.openAccess:
			dayLength = len(app.frame.hours)
			for day in self.openAccess:
				if day:
					if self.openAccess[day]:
						for timeSlot in self.openAccess[day]:
							if timeSlot:
								multiplier = dayLength * int(day[:1])
								if timeSlot[0] in app.frame.hours:
									startIndex = app.frame.hours.index(timeSlot[0])
									if timeSlot[1] in app.frame.hours:
										endIndex = app.frame.hours.index(timeSlot[1])
									elif timeSlot[1] == app.frame.closeTime:
										endIndex = len(app.frame.hours)
									else: 
										continue
									for i in range (multiplier+startIndex, multiplier+endIndex):
										if day in reservedDict:
											buttonTime = app.frame.buttons[i].GetLabel()
											buttonTime = datetime.datetime.strptime(buttonTime,'%H%M')
											for reservedSlot in reservedDict[day]:
												reservedStart = datetime.datetime.strptime(reservedSlot[0],'%H%M')
												reservedEnd = datetime.datetime.strptime(reservedSlot[1],'%H%M')
												if reservedStart <= buttonTime < reservedEnd:
													app.frame.buttons[i].SetBackgroundColour("red")
													break
												else:
													app.frame.buttons[i].SetBackgroundColour("forest green")
										else:
											app.frame.buttons[i].SetBackgroundColour("forest green")
										app.frame.buttons[i].Enable(True)
										app.frame.buttons[i].SetForegroundColour(wx.WHITE)
	def getReservedTimes(self):
		reservedDict = {}
		today = datetime.datetime.now()
		endDay = today + datetime.timedelta(days=6)
		today = today.strftime("%Y-%m-%d")
		endDay = endDay.strftime("%Y-%m-%d")
		query = 'SELECT reserve_date,startTime,endTime FROM laser_reserve WHERE reserve_date >= CURDATE() AND reserve_date <="'+endDay+'"'
		db = MySQLdb.connect(host='envision-local.dynamic.ucsd.edu',user=passDict['envision-user'],passwd=passDict['envision-pass'],db="envision_control")
		cur = db.cursor()
		cur.execute(query)
		results = cur.fetchall()
		for result in results:
			day = str((datetime.datetime.strptime(result[0],'%Y-%m-%d')).weekday())
			if day not in reservedDict:
				reservedDict[day]=[]
			reservedDict[day].append([])
			startTime = result[1][:-3].replace(":",'')
			endTime = result[2][:-3].replace(":",'')
			reservedDict[day][-1].extend((startTime,endTime))
		return reservedDict

app = EnVisionScheduling(False)
dbHandler = DatabaseHandler()
app.frame.refresh(wx.EVT_TIMER)
app.frame.panel.SetFocus()
# import wx.lib.inspection
# wx.lib.inspection.InspectionTool().Show()
app.MainLoop()
