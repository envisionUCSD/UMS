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

import wx, os, datetime, json, pysftp,sys, MySQLdb


class MainWindow(wx.Frame):
	def __init__(self, parent, title):
		wx.Frame.__init__(self, parent, title = title)

		self.startPick = wx.GenericDatePickerCtrl(self, size=(120,-1),style = wx.TAB_TRAVERSAL| wx.DP_DROPDOWN)
		self.startPick.Bind(wx.EVT_DATE_CHANGED, self.onStartChange)
		self.endPick = wx.GenericDatePickerCtrl(self, size=(120,-1),style = wx.TAB_TRAVERSAL| wx.DP_DROPDOWN)
		self.endPick.Bind(wx.EVT_DATE_CHANGED, self.onEndChange)
		self.endPick.Enable(False)

		self.mainSizer = wx.BoxSizer(wx.VERTICAL)
		self.pickSizer = wx.BoxSizer(wx.HORIZONTAL)
		self.weekSizer = wx.BoxSizer(wx.HORIZONTAL)
		self.controlSizer = wx.BoxSizer(wx.HORIZONTAL)
		
		self.days = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]
		self.mainGridSizer = wx.GridSizer(cols=len(self.days),hgap=5,vgap=5)
		self.hours = []
		self.buttons = []
		self.dayBox = {}
		self.dayBoxSizer = {}
		self.hourGridSizer = {}
		self.hourBoxSizer = {}
		self.changesMade = False
		
		# self.startDate = None
		# self.endDate = None
		
		openTime = datetime.datetime.strptime('0800', '%H%M')
		self.hours.append(openTime.strftime('%H%M'))
		hoursOpen = 13
		for i in range(30,60*hoursOpen,30):
			self.hours.append((openTime+datetime.timedelta(minutes=i)).strftime('%H%M'))
		self.closeTime = (datetime.datetime.strptime(self.hours[-1],'%H%M') + datetime.timedelta(minutes=30)).strftime('%H%M')
		
		for day in self.days:
			self.dayBox[day] = wx.StaticBox(self, label= day)
			self.dayBoxSizer[day] = wx.StaticBoxSizer(self.dayBox[day],wx.VERTICAL)
			self.mainGridSizer.Add(self.dayBoxSizer[day],1,wx.EXPAND)
			self.hourGridSizer[day] = wx.GridSizer(cols=1,vgap=4)
			for hour in self.hours:
				if hour[2:] == '00':
					self.hourBoxSizer[day + ':' + hour[:2]+'00']= wx.BoxSizer(wx.HORIZONTAL)
					self.buttons.append(wx.ToggleButton(self,id=len(self.buttons),label=hour))
					self.hourBoxSizer[day + ':' + hour].Add(self.buttons[-1],1,wx.EXPAND | wx.LEFT , 4)
					self.buttons[-1].Bind(wx.EVT_TOGGLEBUTTON, self.buttonToggle)
				else:
					self.buttons.append(wx.ToggleButton(self,id=len(self.buttons),label=hour))
					self.hourBoxSizer[day + ':' + hour[:2]+'00'].Add(self.buttons[-1],1,wx.EXPAND | wx.RIGHT, 4)
					self.buttons[-1].Bind(wx.EVT_TOGGLEBUTTON, self.buttonToggle)
					self.hourGridSizer[day].Add(self.hourBoxSizer[day + ':' + hour[:2]+'00'], 1, wx.EXPAND)
			self.dayBoxSizer[day].Add(self.hourGridSizer[day],1,wx.EXPAND)	
		buttonSpace = 50
		self.reloadButton = wx.Button(self,id=-1,label="RELOAD")
		self.resetButton = wx.Button(self,id=-1,label="RESET")
		self.saveButton = wx.Button(self,id=-1,label="SAVE")
		self.exitButton = wx.Button(self,id=-1,label="EXIT")
		self.controlSizer.Add(self.reloadButton,1,wx.EXPAND | wx.RIGHT, buttonSpace)
		self.controlSizer.Add(self.resetButton,1,wx.EXPAND | wx.RIGHT, buttonSpace)
		self.controlSizer.Add(self.saveButton,1,wx.EXPAND | wx.RIGHT, buttonSpace)
		self.controlSizer.Add(self.exitButton,1,wx.EXPAND | wx.RIGHT, buttonSpace)
		
		self.saveButton.Enable(False)
		self.saveButton.Bind(wx.EVT_BUTTON,self.saveEvent)
		self.reloadButton.Bind(wx.EVT_BUTTON,self.reloadEvent)
		self.resetButton.Bind(wx.EVT_BUTTON,self.resetEvent)
		self.exitButton.Bind(wx.EVT_BUTTON,self.exitEvent)
		
		self.Bind(wx.EVT_CLOSE, self.exitEvent)
		self.pickSizer.Add(self.startPick, 0, wx.ALIGN_CENTER)
		self.pickSizer.AddSpacer(50)
		self.pickSizer.Add(self.endPick, 0, wx.ALIGN_CENTER)
		self.mainSizer.AddSpacer(10)
		self.mainSizer.Add(self.pickSizer,0,wx.ALIGN_CENTER)
		self.mainSizer.Add(self.mainGridSizer,1,wx.EXPAND | wx.ALL,10)
		self.mainSizer.Add(self.controlSizer, 0, wx.ALIGN_CENTER | wx.ALL, 20)
		self.mainSizer.SetSizeHints(self)
		self.SetSizer(self.mainSizer)
		self.Centre()
		self.Layout()
		self.Show()
	
	def onStartChange(self, event):
		#self.startDate = event.GetDate()
		self.startDate = self.startPick.GetValue()
		self.endPick.Enable(True)
		self.endPick.SetRange(self.startDate,self.startDate.__add__(wx.DateSpan(weeks=11)))
		#print start.FormatISODate()
		#print self.startDate, type(self.startDate)
	def onEndChange(self, event):
		self.endDate = self.endPick.GetValue()
		#end = event.GetDate()
		self.saveButton.Enable(True)
		#self.endPick.SetRange(start,start.__add__(wx.DateSpan(weeks=11)))

	def reloadEvent(self, event):
		loadMessage = "All Changes Will be Lost. Reload Open Access Hours?"
		loadDlg = wx.MessageDialog(self, loadMessage, "RELOAD Hours?", wx.YES_NO | wx.CENTRE)
		result = loadDlg.ShowModal()
		loadDlg.Close()
		loadDlg.Destroy()
		if result == wx.ID_NO:
			return
		elif result == wx.ID_YES:
			for button in self.buttons:
				button.SetValue(False)
			app.setOpenAccess()
	def resetEvent(self, event):
		for button in self.buttons:
			button.SetValue(False)
	def exitEvent(self, event):
		if self.changesMade:
			exitMessage = "UNSAVED Changes Will be Lost. EXIT Anyway"
			exitDlg = wx.MessageDialog(self, exitMessage, "EXIT?", wx.YES_NO | wx.CENTRE)
			result = exitDlg.ShowModal()
			exitDlg.Close()
			exitDlg.Destroy()
			if result == wx.ID_NO:
				return
			elif result == wx.ID_YES:
				self.onClose(wx.EVT_CLOSE)
		else:
			self.onClose(wx.EVT_CLOSE)
	def onClose(self,event):
		self.Destroy()
	def saveEvent(self,event):
		openAccessSave  = {}
		dayCount = 0
		dayLength = len(self.hours)
		blockStarted = False
		for day in self.days:
			dayName = str(dayCount)
			openAccessSave[dayName] = []
			for i in range(dayCount*dayLength,dayCount*dayLength+(dayLength)):
				if self.buttons[i].GetValue() is True: 
					if blockStarted is False:
						openAccessSave[dayName].append([])
						#openAccessSave[day][-1].append([])
						#print openAccessSave[dayName][-1].append(self.buttons[i].GetLabel())
						openAccessSave[dayName][-1].append(self.buttons[i].GetLabel())
						blockStarted = True
					elif i == (dayLength*dayCount)+dayLength-1:
						openAccessSave[dayName][-1].append(self.closeTime)
						blockStarted = False
						continue
				elif self.buttons[i].GetValue() is False:
					if blockStarted is True:
						openAccessSave[dayName][-1].append(self.buttons[i].GetLabel())
						blockStarted = False
			dayCount += 1
		if self.changesMade:
			saveMessage = "Open Access Hours have changed. Overwrite existing file?"
			saveDlg = wx.MessageDialog(self, saveMessage, "SAVE HOURS?", wx.YES_NO | wx.CENTRE)
			result = saveDlg.ShowModal()
			saveDlg.Close()
			saveDlg.Destroy()
			if result == wx.ID_NO:
				#print openAccessSave
				with open ('./openAccess.txt','wb') as file:
					json.dump(openAccessSave,file,indent=4,sort_keys=True)
				return
			elif result == wx.ID_YES:
				db = MySQLdb.connect(host="envision-local.dynamic.ucsd.edu",user=app.passDict['envision-user'],passwd=app.passDict['envision-pass'],db="envision_control")
				db.autocommit(True)
				cur = db.cursor()
				query = "DELETE FROM oa_hours"
				cur.execute(query)
				for i in range (0,7):
					if openAccessSave[str(i)]:
						for time in openAccessSave[str(i)]:
							#print time[0], time[1]
							query = 'INSERT INTO oa_hours (day,startTime,endtime) VALUES ('+str(i)+',"'+time[0]+'","'+time[1]+'")'
							cur.execute(query)

				db.close()
				self.updateMSDB(openAccessSave)
				wx.MessageBox("Changes Uploaded to Server", "Saved")
				self.changesMade = False
		else:
			wx.MessageBox("No Changes Detected", "Not Saved")
	
	def updateMSDB(self,oaDict):
		db = MySQLdb.connect(host="db.eng.ucsd.edu",user=app.passDict['db-user'],passwd=app.passDict['db-pass'],db="makerspace")
		db.autocommit(True)
		cur = db.cursor()
		query = "DELETE FROM laser_open_hours"
		cur.execute(query)
		
		dateDict = {}
		for i in range (0,7):
			dateDict[str(i)]=[]
		dayCount = 0
		daySpan = (self.endDate - self.startDate).days
		for i in range (0, daySpan):
			newDate = self.startDate.__add__(wx.DateSpan(days=i))
			dow = str((datetime.datetime.strptime(newDate.FormatISODate(), '%Y-%m-%d')).weekday())
			if dow in dateDict:
				dateDict[dow].append(newDate.FormatISODate())
		for i in range (0,7):
			if str(i) in oaDict:
				for day in dateDict[str(i)]:
					for time in oaDict[str(i)]:
						startTime = str(datetime.datetime.strptime(time[0],'%H%M').time())
						endTime = str(datetime.datetime.strptime(time[1],'%H%M').time())
						query = 'INSERT INTO laser_open_hours (reserve_date,starttime,endtime) VALUE ("'+day+'","'+startTime+'","'+endTime+'")'
						cur.execute(query)
		db.close()	
		

		
	def buttonToggle(self,event):
		self.changesMade = True
		button = event.GetEventObject()
		buttonId = button.GetId()
		buttonLabel = button.GetLabel()
		if buttonLabel[2:] == '00':
			if button.GetValue() is True:
				if self.buttons[int(buttonId) + 1].GetValue() is False:
					self.buttons[int(buttonId) + 1].SetValue(True)
			else:
				if self.buttons[int(buttonId) + 1].GetValue() is True:
					self.buttons[int(buttonId) + 1].SetValue(False)
			
			
class EnVisionScheduling(wx.App):
	def OnInit(self):
		self.name = "EnVision-Scheduling"
		self.instance = wx.SingleInstanceChecker(self.name)
		if self.instance.IsAnotherRunning():
			wx.MessageBox("Another instance is running", "ERROR")
			return False
		self.frame = MainWindow(None, "EnVision Scheduling App")
		self.frame.Show()
		self.openAccess = {}
		for i in range (0,7):
			self.openAccess[str(i)]=[]
		self.loadFile()
		self.setOpenAccess()
		return True
	
	def loadFile(self):
		if os.path.isfile('./passList.txt'):
			with open('passList.txt','r') as passFile:
				try:
					self.passDict = json.load(passFile) # load json info into a list of dicts
				except: 
					wx.MessageBox('Password File does not exist','ERROR')
					sys.exit(1)
		else:
			wx.MessageBox('Password File does not exist','ERROR')
			sys.exit(1)
		
		db = MySQLdb.connect(host="envision-local.dynamic.ucsd.edu",user=self.passDict['envision-user'],passwd=self.passDict['envision-pass'],db="envision_control")
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
		if self.openAccess:
			dayLength = len(self.frame.hours)
			for day in self.openAccess:
				if day:
					if self.openAccess[day]:
						for timeSlot in self.openAccess[day]:
							if timeSlot:
								multiplier = dayLength * int(day[:1])
								if timeSlot[0] in self.frame.hours: 
									startIndex = self.frame.hours.index(timeSlot[0])
									if timeSlot[1] in self.frame.hours:
										endIndex = self.frame.hours.index(timeSlot[1])
									elif timeSlot[1] == self.frame.closeTime:
										endIndex = len(self.frame.hours)
									else: 
										continue
									for i in range (multiplier+startIndex, multiplier+endIndex):
										self.frame.buttons[i].SetValue(True)
app = EnVisionScheduling(False)
app.MainLoop()
