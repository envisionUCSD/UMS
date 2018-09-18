#! /usr/bin/env python

import wx, MySQLdb, csv, datetime, gettext, os, json, threading,sys
from collections import OrderedDict
import wx.lib.mixins.listctrl as listmix
import xlwt
import wx.lib.mixins.inspection

PASSFILE = '/home/e4ms/job_tracking/passList.txt'

"""
Todo: need to add calendar limits
need to add weekly data option (using datetime...probably)
save as file dialog
"""
class RunReportThread(threading.Thread):
	def __init__(self,parent):
	#accept machine and machine properties as args
		threading.Thread.__init__(self)
		self.parent = parent
		self.runFlag = True #run Flag indicates the thread is still running. Can be called externally to end the thread
		
	#required function called by start()
	def run(self):
		print "running"
		numMachines = self.parent.machineListBox.GetCheckedStrings()
		rowList = self.parent.majorListBox.GetCheckedStrings()
		if self.parent.hourReports == True:
			columnList = self.parent.hourList
			numQueries = len(numMachines) * len(columnList) * len(rowList)
		elif self.parent.weeklyReports == True:
			self.parent.weekList = []
			startYear = self.parent.startDate.GetValue().GetYear()
			endYear = self.parent.endDate.GetValue().GetYear()
			startDate = self.parent.startDate.GetValue().GetWeekOfYear()
			endDate = self.parent.endDate.GetValue().GetWeekOfYear()
			dateDiffWeeks = (((endYear - startYear)*52) - (startDate - endDate)) + 1
			#print startYear, endYear, startDate, endDate, dateDiffWeeks
			for i in range(dateDiffWeeks):
				#week = self.parent.startDate.GetValue().__add__(wx.DateSpan(weeks=i))
				#self.parent.weekList.append(week.FormatISODate().replace('-',""))
				self.parent.weekList.append(str(i))
			columnList = self.parent.weekList
			numQueries = len(numMachines) * len(columnList) * len(rowList)
		else:
			columnList = self.parent.levelListBox.GetCheckedStrings()
			#print numMachines, columnList, rowList
			numQueries = len(numMachines) * len(columnList) * len(rowList)
		wx.CallAfter(self.parent.SetGauge,numQueries-35)
		queries = 0
		self.reportDict = OrderedDict()
		self.parent.umsDB.connectDB()
		for machine in numMachines:
			self.reportDict[machine]=OrderedDict()
			if self.parent.singleUser:
				self.reportDict[machine]["USER"] = self.parent.user
				uses = self.parent.umsDB.getCount(self.parent.user, "","",machine,False)
				queries +=1
				self.reportDict[machine]["USES"] = uses
			else:
				for i, level, in enumerate(columnList):
					self.reportDict[machine][level] = OrderedDict()
					for j,major in enumerate(rowList):
						numUsers = self.parent.umsDB.getCount(self.parent.user, major, level, machine, self.parent.hourReports)
						queries += 1
						wx.CallAfter(self.parent.updateGauge,queries)
						self.reportDict[machine][level][major] = numUsers
		self.parent.umsDB.closeDB()
		wx.CallAfter(self.parent.threadFinished, self.reportDict)
	def stop(self):
	#pretty sure the order of these variables are important. Set the kill(ed) flag, and then end the thread.
		self.runFlag = False



class TestNB(wx.Notebook):
	def __init__(self, parent, id):
		wx.Notebook.__init__(self, parent, id, size=(21,21), style= wx.BK_DEFAULT)

		#win = wx.Panel(self, -1)
		#self.AddPage(win, "Blue")

class DatabaseHandler():
	def __init__(self,parent):
		self.db = None
		self.cur = None
		self.username = 'reports'
		self.password = 'envisionLogs'
		self.host = "envision-local.dynamic.ucsd.edu"
		self.port = 3306
		self.database = "envision_control"
		self.parent = parent
	def connectDB(self):
		try:
			self.db = MySQLdb.connect(host=self.host,port=self.port,user=self.username,passwd=self.password,db=self.database)
		except Exception as e:
		#if you can't connect, end the program
			print e
			print "unable to connect to DB...Shutting down."
			return (False)
		else:
			print "Successful Connection to DB"
		self.db.autocommit(True) #changes made are committed on execution
		self.cur = self.db.cursor() #set the cursor to the beginning of the DB
	#function to clean up the connection 
	def closeDB(self):
		self.db.close()
		self.db = None
		self.cur = None
		print "DB Closed" #debug info
	
	def getCount(self, user, major, level, machine, hourReports):
		if hourReports == True:
			query = self.getHourly(user,major,level,machine)
		elif self.parent.weeklyReports == True:
			query = self.getWeekly(user,major,level,machine)
		else:
			query = self.getLevels(user,major,level,machine)
		numRows = self.cur.execute(query)
		result = self.cur.fetchone()
		return str(result[0])
	
	
	def getWeekly(self,user,major,week,machine):
		thisWeek = self.parent.startDate.GetValue().__add__(wx.DateSpan(weeks=int(week))).FormatISODate().replace('-',"")
		nextWeek = self.parent.startDate.GetValue().__add__(wx.DateSpan(weeks=int(week)+1)).FormatISODate().replace('-',"")
		if user.startswith("DISTINCT"):
			query = 'SELECT COUNT(DISTINCT user) FROM log WHERE major="'+major+'" and machine = "'+machine+'" AND level != "FALSE" AND level != "DEAN" and starttime between "' + thisWeek + '" and "' + nextWeek + '"'
			# query = 'SELECT COUNT(DISTINCT user) FROM log where major="'+major+'" and level="'+level+'" and machine="'+machine+'"'
		elif user.startswith("ALL"):
			query = 'SELECT COUNT(*) FROM log WHERE major="'+major+'" and machine = "'+machine+'" AND level != "FALSE" AND level != "DEAN" and starttime between "' + thisWeek + '" and "' + nextWeek + '"'
		else:
			query = 'SELECT COUNT(*) FROM log where major="'+major+'" and machine = "'+machine+'" and user="'+user+'" and starttime between "' + thisWeek + '" and "' + nextWeek + '"'
		return query

	
	
	def getHourly(self,user,major,hour,machine):
		if user.startswith("DISTINCT"):
			query = 'SELECT COUNT(DISTINCT user) FROM log WHERE HOUR(STR_TO_DATE(starttime, "%Y%m%d-%T")) BETWEEN '+hour+' AND '+ hour +' AND major="'+major+'" and machine="'+machine+'" AND level != "FALSE" AND level != "DEAN" and starttime between "' + self.parent.startDateSelection + '" and "' + self.parent.endDateSelection + '"'
			# query = 'SELECT COUNT(DISTINCT user) FROM log where major="'+major+'" and level="'+level+'" and machine="'+machine+'"'
		elif user.startswith("ALL"):
			query = 'SELECT COUNT(*) FROM log WHERE HOUR(STR_TO_DATE(starttime, "%Y%m%d-%T")) BETWEEN '+hour+' AND '+ hour+' AND major="'+major+'" and machine="'+machine+'" AND level != "FALSE" AND level !="DEAN" and starttime between "' + self.parent.startDateSelection + '" and "' + self.parent.endDateSelection + '"'
		else:
			query = 'SELECT COUNT(*) FROM log where user="'+user+'" and machine="'+machine+'" and starttime between "' + self.parent.startDateSelection + '" and "' + self.parent.endDateSelection + '"'	
		return query
	def getLevels(self,user,major,level,machine):
		if user.startswith("DISTINCT"):
			query = 'SELECT COUNT(DISTINCT user) FROM log where major="'+major+'" and level="'+level+'" and machine="'+machine+'" and starttime between "' + self.parent.startDateSelection + '" and "' + self.parent.endDateSelection + '"'
		elif user.startswith("ALL"):
			query = 'SELECT COUNT(*) FROM log where major="'+major+'" and level="'+level+'" and machine="'+machine+'" and starttime between "' + self.parent.startDateSelection + '" and "' + self.parent.endDateSelection + '"'
		else:
			query = 'SELECT COUNT(*) FROM log where user="'+user+'" and machine="'+machine+'" and starttime between "' + self.parent.startDateSelection + '" and "' + self.parent.endDateSelection + '"'
		return query
		#SELECT COUNT(*) FROM log where major="BENG" and level="D1" and machine = "FRONT-DESK" and starttime between "20171126" and "20171128"
	
	def getFields(self):
		query = 'select distinct major from log order by major'
		numRows = self.cur.execute(query)
		while True:
			row = self.cur.fetchone()
			if row == None:
				break
			else:
				if row[0] =="FALSE" or row[0] == "DEAN":
					continue
				else:
					self.parent.majorList.append(row[0])
		query = 'select name from machines order by name'
		numRows = self.cur.execute(query)
		while True:
			row = self.cur.fetchone()
			if row == None:
				break
			else:
				self.parent.machineList.append(row[0])
		query = 'select distinct level from log order by level'
		numRows = self.cur.execute(query)
		while True:
			row = self.cur.fetchone()
			if row == None:
				break
			else:
				if row[0] != "FALSE":
					self.parent.levelList.append(row[0])					
			#print(row)
class MyFrame(wx.Frame):
	def __init__(self, *args, **kwds):
		size = (80,80)
		# begin wxGlade: MyFrame.__init__
		kwds["style"] = wx.DEFAULT_FRAME_STYLE
		wx.Frame.__init__(self, *args, **kwds)
		self.panel_1 = wx.Panel(self, wx.ID_ANY)
		self.userBox = wx.ComboBox(self.panel_1, wx.ID_ANY, choices=["DISTINCT","ALL"], style=wx.CB_DROPDOWN | wx.TE_PROCESS_ENTER)
		self.majorListBox = wx.CheckListBox(self.panel_1, wx.ID_ANY, choices=[_("c"), _("a"), _("b"), _("d")], style=wx.LB_ALWAYS_SB | wx.LB_MULTIPLE, size=size )
		self.allButton_1 = wx.Button(self.panel_1, wx.ID_ANY, _("ALL"))
		self.allButton_1.cat = "MAJOR"
		self.clearButton_1 = wx.Button(self.panel_1, wx.ID_ANY, _("CLEAR"))
		self.clearButton_1.cat = "MAJOR"
		self.allButton_2 = wx.Button(self.panel_1, wx.ID_ANY, _("ALL"))
		self.allButton_2.cat = "LEVEL"
		self.clearButton_2 = wx.Button(self.panel_1, wx.ID_ANY, _("CLEAR"))
		self.clearButton_2.cat = "LEVEL"
		self.allButton_3 = wx.Button(self.panel_1, wx.ID_ANY, _("ALL"))
		self.allButton_3.cat = "MACHINE"
		self.clearButton_3 = wx.Button(self.panel_1, wx.ID_ANY, _("CLEAR"))
		self.clearButton_3.cat = "MACHINE"
		self.levelListBox = wx.CheckListBox(self.panel_1, wx.ID_ANY, choices=[_("c"), _("a"), _("b"), _("d")], style=wx.LB_ALWAYS_SB | wx.LB_MULTIPLE , size=size)
		self.machineListBox = wx.CheckListBox(self.panel_1, wx.ID_ANY, choices=[_("c"), _("a"), _("b"), _("d")], style=wx.LB_ALWAYS_SB | wx.LB_MULTIPLE , size=size)
		
		self.startCheckbox = wx.CheckBox(self.panel_1, wx.ID_ANY, "")
		self.startDate = wx.GenericDatePickerCtrl(self.panel_1, size=(120,-1),style = wx.DP_DROPDOWN)
		# self.startDateSelection = wx.DateTime.Today().FormatISODate().replace('-',"")
		self.startDateSelection = "%"
		self.startDate.SetRange(wx.DateTime.Today().__add__(wx.DateSpan(years=-5)),wx.DateTime.Today())
		self.endCheckbox = wx.CheckBox(self.panel_1, wx.ID_ANY, "")
		self.endDate = wx.GenericDatePickerCtrl(self.panel_1, size=(120,-1),style = wx.DP_DROPDOWN)
		self.endDateSelection = wx.DateTime.Today().__add__(wx.DateSpan(days=1)).FormatISODate().replace('-',"")
		self.endDate.SetValue(wx.DateTime.Today().__add__(wx.DateSpan(days=1)))
		
		self.hourBox = wx.CheckBox(self.panel_1, wx.ID_ANY, "HOURLY DATA")
		self.weeklyBox = wx.CheckBox(self.panel_1, wx.ID_ANY, "WEEKLY DATA")
		self.timedBox = wx.CheckBox(self.panel_1,wx.ID_ANY,"TIMED DATA")
		self.runButton = wx.Button(self.panel_1, wx.ID_ANY, _(" RUN "))
		self.appendBox = wx.CheckBox(self.panel_1, wx.ID_ANY, "APPEND REPORTS")
		self.exportButton = wx.Button(self.panel_1, wx.ID_ANY, _("EXPORT"))
		self.exportButton.Disable()
		
		self.notebook = TestNB(self.panel_1,wx.ID_ANY)
		self.hourReports = False
		self.weeklyReports = False
		self.hourList = []
		for i in range(9,21,1):
			self.hourList.append(str(i))
		self.user = None
		self.singleUser = False
		self.umsDB = DatabaseHandler(self)
		self.majorList = []
		self.machineList = []
		self.levelList = []
		self.reportDict = {}

		self.__set_properties()
		self.__do_layout()
		self.__set_values()
		#self.gauge = None
		# end wxGlade
	
	def __set_values(self):
		self.umsDB.connectDB()
		self.umsDB.getFields()
		self.umsDB.closeDB()
		self.majorListBox.Clear()
		self.majorListBox.InsertItems(self.majorList,0)
		self.levelListBox.Clear()
		self.levelListBox.InsertItems(self.levelList,0)
		self.machineListBox.Clear()
		self.machineListBox.InsertItems(self.machineList,0)
	
	def __set_properties(self):
		# begin wxGlade: MyFrame.__set_properties
		self.SetTitle(_("frame"))
		self.startDate.Enable(False)
		self.endDate.Enable(False)
		self.allButton_1.Bind(wx.EVT_BUTTON,self.onAll)
		self.allButton_2.Bind(wx.EVT_BUTTON,self.onAll)
		self.allButton_3.Bind(wx.EVT_BUTTON,self.onAll)
		self.clearButton_1.Bind(wx.EVT_BUTTON,self.onClear)
		self.clearButton_2.Bind(wx.EVT_BUTTON,self.onClear)
		self.clearButton_3.Bind(wx.EVT_BUTTON,self.onClear)
		self.runButton.Bind(wx.EVT_BUTTON,self.runReports)
		self.exportButton.Bind(wx.EVT_BUTTON,self.exportReports)
		self.userBox.Bind(wx.EVT_COMBOBOX, self.userSelect)
		self.userBox.Bind(wx.EVT_TEXT_ENTER, self.singleUserChoice)
		self.startCheckbox.Bind(wx.EVT_CHECKBOX,self.toggleCal)
		self.endCheckbox.Bind(wx.EVT_CHECKBOX,self.toggleCal)
		self.hourBox.Bind(wx.EVT_CHECKBOX, self.toggleHour)
		self.weeklyBox.Bind(wx.EVT_CHECKBOX, self.toggleWeekly)
		self.startDate.Bind(wx.EVT_DATE_CHANGED, self.SetDate)
		self.endDate.Bind(wx.EVT_DATE_CHANGED, self.SetDate)
		self.notebook.Bind(wx.EVT_MIDDLE_DOWN, self.onMClick)

		# end wxGlade

	def onMClick(self,event):
		mousePos = event.GetPosition()
		print mousePos
		pageID, flags = self.notebook.HitTest(mousePos)
		print pageID
		if pageID >= 0:
			self.notebook.DeletePage(pageID)
		if self.notebook.GetPageCount() == 0:
			self.exportButton.Disable()
	
	def singleUserChoice(self,event):
		choice = event.GetEventObject().GetValue()
		self.user = choice
		self.singleUser = True
		
	def userSelect(self,event):
		choice = event.GetEventObject().GetStringSelection()
		self.user = choice
		self.singleUser = False
	
	def __do_layout(self):
		# begin wxGlade: MyFrame.__do_layout
		self.sizer_1 = wx.BoxSizer(wx.VERTICAL)
		sizer_2 = wx.StaticBoxSizer(wx.StaticBox(self.panel_1, wx.ID_ANY, _("EnVision UMS Log")), wx.VERTICAL)
		sizer_21 = wx.BoxSizer(wx.VERTICAL)
		sizer_15 = wx.BoxSizer(wx.HORIZONTAL)
		sizer_19 = wx.BoxSizer(wx.VERTICAL)
		sizer_20 = wx.BoxSizer(wx.VERTICAL)
		sizer_18 = wx.BoxSizer(wx.VERTICAL)
		sizer_check = wx.BoxSizer(wx.VERTICAL)
		sizer_17 = wx.BoxSizer(wx.VERTICAL)
		sizer_16 = wx.BoxSizer(wx.VERTICAL)
		sizer_3 = wx.BoxSizer(wx.HORIZONTAL)
		sizer_12 = wx.BoxSizer(wx.VERTICAL)
		sizer_14 = wx.BoxSizer(wx.HORIZONTAL)
		sizer_27 = wx.BoxSizer(wx.VERTICAL)
		sizer_11 = wx.BoxSizer(wx.VERTICAL)
		sizer_13 = wx.BoxSizer(wx.HORIZONTAL)
		sizer_26 = wx.BoxSizer(wx.VERTICAL)
		sizer_10 = wx.BoxSizer(wx.VERTICAL)
		sizer_25 = wx.BoxSizer(wx.VERTICAL)
		sizer_9 = wx.BoxSizer(wx.VERTICAL)
		sizer_24 = wx.BoxSizer(wx.VERTICAL)
		sizer_8 = wx.BoxSizer(wx.VERTICAL)
		sizer_23 = wx.BoxSizer(wx.VERTICAL)
		sizer_7 = wx.BoxSizer(wx.VERTICAL)
		sizer_22 = wx.BoxSizer(wx.VERTICAL)
		sizer_4  = wx.BoxSizer(wx.HORIZONTAL)
		sizer_5  = wx.BoxSizer(wx.HORIZONTAL)
		sizer_6  = wx.BoxSizer(wx.HORIZONTAL)
		sizerNB = wx.BoxSizer(wx.HORIZONTAL)
		
		label_2 = wx.StaticText(self.panel_1, wx.ID_ANY, _("USER"), style=wx.ALIGN_CENTER)
		sizer_22.Add(label_2, 0, wx.ALIGN_CENTER | wx.EXPAND, 0)
		sizer_7.Add(sizer_22, 0, wx.EXPAND, 0)
		sizer_7.Add(self.userBox, 0, wx.ALL | wx.EXPAND, 10)
		sizer_3.Add(sizer_7, 1, wx.ALIGN_CENTER | wx.ALL | wx.EXPAND, 10)
		label_3 = wx.StaticText(self.panel_1, wx.ID_ANY, _("MAJOR"), style=wx.ALIGN_CENTER)
		sizer_23.Add(label_3, 0, wx.ALIGN_CENTER | wx.EXPAND, 0)
		
		
		
		sizer_8.Add(sizer_23, 0, wx.EXPAND, 0)
		sizer_8.Add(self.majorListBox, 0, wx.ALIGN_CENTER | wx.ALL | wx.EXPAND, 10)
		
		sizer_4.AddStretchSpacer()
		sizer_4.Add(self.allButton_1, 0, wx.EXPAND, 0)
		sizer_4.AddStretchSpacer()
		sizer_4.Add(self.clearButton_1, 0, 0, 0)
		sizer_4.AddStretchSpacer()
		sizer_8.Add(sizer_4, 0, wx.ALIGN_CENTER | wx.EXPAND, 0)
		sizer_3.Add(sizer_8, 1, wx.ALIGN_CENTER | wx.ALL | wx.EXPAND, 10)
		
		
		label_4 = wx.StaticText(self.panel_1, wx.ID_ANY, _("LEVEL"), style=wx.ALIGN_CENTER)
		sizer_24.Add(label_4, 0, wx.ALIGN_CENTER | wx.EXPAND, 0)
		sizer_9.Add(sizer_24, 0, wx.EXPAND, 0)
		sizer_9.Add(self.levelListBox, 0, wx.ALIGN_CENTER | wx.ALL | wx.EXPAND, 10)
		
		sizer_5.AddStretchSpacer()
		sizer_5.Add(self.allButton_2, 0, wx.EXPAND, 0)
		sizer_5.AddStretchSpacer()
		sizer_5.Add(self.clearButton_2, 0, 0, 0)
		sizer_5.AddStretchSpacer()
		sizer_9.Add(sizer_5, 0, wx.ALIGN_CENTER | wx.EXPAND, 0)
		sizer_3.Add(sizer_9, 1, wx.ALIGN_CENTER | wx.ALL | wx.EXPAND, 10)

		label_5 = wx.StaticText(self.panel_1, wx.ID_ANY, _("MACHINE"), style=wx.ALIGN_CENTER)
		sizer_25.Add(label_5, 0, wx.ALIGN_CENTER | wx.EXPAND, 0)
		sizer_10.Add(sizer_25, 0, wx.EXPAND, 0)
		sizer_10.Add(self.machineListBox, 0, wx.ALIGN_CENTER | wx.ALL | wx.EXPAND, 10)
		
		sizer_6.AddStretchSpacer()
		sizer_6.Add(self.allButton_3, 0, wx.EXPAND, 0)
		sizer_6.AddStretchSpacer()
		sizer_6.Add(self.clearButton_3, 0, 0, 0)
		sizer_6.AddStretchSpacer()
		sizer_10.Add(sizer_6, 0, wx.ALIGN_CENTER | wx.EXPAND, 0)
		sizer_3.Add(sizer_10, 1, wx.ALIGN_CENTER | wx.ALL | wx.EXPAND, 10)
		
		
		calSizer = wx.BoxSizer(wx.HORIZONTAL)
		timeSizer = wx.BoxSizer(wx.VERTICAL)
		
		label_6 = wx.StaticText(self.panel_1, wx.ID_ANY, _("START"), style=wx.ALIGN_CENTER)
		sizer_26.Add(label_6, 0, wx.ALIGN_CENTER | wx.EXPAND, 0)
		sizer_11.Add(sizer_26, 0, wx.EXPAND, 0)
		sizer_13.Add(self.startCheckbox, 0, 0, 0)
		sizer_13.Add(self.startDate, 0, 0, 0)
		sizer_11.Add(sizer_13, 1, wx.EXPAND | wx.TOP, 10)
		#sizer_3.Add(sizer_11, 1, wx.ALIGN_CENTER | wx.ALL | wx.EXPAND, 10)
		#calSizer.Add(sizer_11,1,wx.ALIGN_CENTER | wx.EXPAND, 0)
		label_7 = wx.StaticText(self.panel_1, wx.ID_ANY, _("END"), style=wx.ALIGN_CENTER)
		sizer_27.Add(label_7, 0, wx.ALIGN_CENTER | wx.EXPAND, 0)
		sizer_12.Add(sizer_27, 0, wx.EXPAND, 0)
		sizer_14.Add(self.endCheckbox, 0, 0, 0)
		sizer_14.Add(self.endDate, 0, 0, 0)
		sizer_12.Add(sizer_14, 1, wx.EXPAND | wx.TOP, 10)
		#sizer_12.AddStretchSpacer()
		# sizerHour = wx.BoxSizer(wx.HORIZONTAL)
		# sizerHour.Add(self.hourBox, 0, wx.EXPAND, 0)
		# sizer_12.Add(sizerHour, 0, wx.EXPAND, 0)
		#sizer_12.Add(self.hourBox, 0, wx.EXPAND, 0)
		#sizer_3.Add(sizer_12, 1, wx.ALIGN_CENTER | wx.ALL | wx.EXPAND, 10)
		calSizer.Add(sizer_11,1,wx.ALIGN_CENTER | wx.EXPAND | wx.ALL, 10)
		calSizer.Add(sizer_12,1,wx.ALIGN_CENTER | wx.EXPAND | wx.ALL, 10)
		timeSizer.Add(calSizer,0,wx.ALIGN_CENTER | wx.EXPAND, 0)
		#timeSizer.AddStretchSpacer()
		timeSizer.Add(self.hourBox, 0, wx.ALIGN_LEFT, 0)
		timeSizer.Add(self.weeklyBox,0, wx.ALIGN_LEFT,0)
		timeSizer.Add(self.timedBox,0,wx.ALIGN_LEFT,0)
		sizer_3.Add(timeSizer,1, wx.ALIGN_CENTER | wx.ALL | wx.EXPAND, 10)
		sizer_2.Add(sizer_3, 0, wx.ALIGN_CENTER | wx.ALL | wx.EXPAND, 10)
		
		#sizer_16.Add((20, 20), 0, 0, 0)
		sizer_16.AddStretchSpacer()
		sizer_15.Add(sizer_16, 1, wx.EXPAND, 0)
		sizer_17.Add(self.runButton, 0, wx.ALIGN_CENTER | wx.ALL | wx.EXPAND, 10)
		sizer_15.Add(sizer_17, 1, wx.EXPAND, 0)
		#sizer_18.Add((20, 20), 0, 0, 0)
		sizer_18.AddStretchSpacer()
		sizer_15.Add(sizer_18, 1, wx.EXPAND, 0)
		sizer_15.Add(self.appendBox, 0, wx.EXPAND,0)
		sizer_check.AddStretchSpacer()
		sizer_15.Add(sizer_check, 1, wx.EXPAND, 0)
		sizer_20.Add(self.exportButton, 0, wx.ALIGN_CENTER | wx.ALL | wx.EXPAND, 10)
		sizer_15.Add(sizer_20, 1, wx.EXPAND, 0)
		sizer_19.AddStretchSpacer()
		#sizer_19.Add((20, 20), 0, 0, 0)
		sizer_15.Add(sizer_19, 1, wx.EXPAND, 0)
		
		sizer_2.Add(sizer_15, 0, wx.EXPAND, 0)
		label_1 = wx.StaticText(self.panel_1, wx.ID_ANY, _("RESULTS"), style=wx.ALIGN_CENTER | wx.ST_NO_AUTORESIZE)
		sizer_21.Add(label_1, 1, wx.ALIGN_CENTER | wx.EXPAND, 0)
		sizer_2.Add(sizer_21, 0, wx.ALIGN_CENTER | wx.EXPAND, 0)
		
		sizerNB.Add(self.notebook,1,wx.ALIGN_CENTER | wx.EXPAND,0)
		sizer_2.Add(sizerNB,1,wx.ALIGN_CENTER | wx.EXPAND, 0)
		
		self.panel_1.SetSizer(sizer_2)
		self.sizer_1.Add(self.panel_1, 1, wx.EXPAND, 0)
		self.SetSizer(self.sizer_1)
		self.sizer_1.Fit(self)
		self.Layout()
		# end wxGlade
	
	def threadFinished(self,threadDict):
		self.reportDict = threadDict
		listControls = []
		if self.appendBox.IsChecked() == False:
			self.notebook.DeleteAllPages()
		for machine in self.reportDict.iterkeys():
			win = wx.Panel(self.notebook, -1)
			sizer = wx.BoxSizer(wx.HORIZONTAL)
			columnLabel = machine+" ("+self.user[0]+")"
			if self.hourReports:
				columnLabel += "{H}"
			if self.weeklyReports:
				columnLabel += "{W}"
			columnLabel += "<"+self.startDateSelection+"-"+self.endDateSelection+">"
			self.notebook.AddPage(win, columnLabel)
			listControls.append(wx.ListCtrl(win, style=wx.LC_REPORT | wx.LC_HRULES | wx.LC_VRULES))
			listControls[-1].Bind(wx.EVT_LIST_COL_CLICK, self.OnColClick, listControls[-1])
			if self.singleUser:
				listControls[-1].InsertColumn(0, "USER")
				listControls[-1].InsertColumn(1, "USES")
				listControls[-1].InsertStringItem(0, self.reportDict[machine]["USER"])
				listControls[-1].SetStringItem(0,1, self.reportDict[machine]["USES"])
			else:
				listControls[-1].InsertColumn(0, "MAJOR")	
				for i, level, in enumerate(self.reportDict[machine].iterkeys()):
					listControls[-1].InsertColumn(i+1, level)
					for j,major in enumerate(self.reportDict[machine][level].iterkeys()):
						if i == 0:
							listControls[-1].InsertStringItem(j, major)
							if j == len(self.majorListBox.GetCheckedStrings())-1:
								listControls[-1].InsertStringItem(j+1, "TOTALS")
								listControls[-1].SetItemBackgroundColour(j+1, "yellow")
								listControls[-1].SetItemTextColour(j+1, "red")
						if j % 2:
							listControls[-1].SetItemBackgroundColour(j, "light gray")
						listControls[-1].SetStringItem(j,i+1, self.reportDict[machine][level][major])
						#listControls[-1].SetItemData(j,i+1)
				listControls[-1].InsertColumn(listControls[-1].GetColumnCount(),"TOTAL")
				self.getTotals(listControls[-1])
				self.getPercent(listControls[-1])
				# listmix.ColumnSorterMixin.__init__(self, 3)
				# self.Bind(wx.EVT_LIST_COL_CLICK, self.OnColClick, listControls[-1])
			#self.reportDict[machine]["listControl"].SetItemBackgroundColour(j, i+2,"yellow")
			sizer.Add(listControls[-1],1,wx.EXPAND,0)
			win.SetSizer(sizer)
			win.Layout()
		self.panel_1.Enable()
		self.gaugeDialog.EndModal(0)
		self.gaugeDialog.Destroy()
		self.exportButton.Enable()
		# self.notebook.Layout()
		# self.Layout()
		# self.panel_1.Layout()
		# self.notebook.GetParent().Layout()
		# self.SetSizerAndFit(self.sizer_1)
		# self.sizer_1.Layout()
		# #self.sizer_1.Refresh()
		# self.Refresh()
		
		#self.gauge.Destroy()
	
	def OnColClick(self,event):
		thisList = event.GetEventObject()
		column = event.GetColumn()
		print "column clicked %i" % column
		#thisList = event.GetItem().GetRefData()
		print thisList
		# resortedDict = dict(self.reportDict)
		# for machine in resortedDict.iterkeys():
			# resortedDict[machine]=dict(resortedDict[machine])
			# for level in resortedDict[machine].iterkeys():
				# resortedDict[machine][level]=dict(resortedDict[machine][level])
		# print resortedDict
		
	
	def SetGauge(self,total):
		self.gaugeDialog = 	wx.Dialog(self,style= wx.STAY_ON_TOP, title = "WAITING...", size = (300,100))
		panel = wx.Panel(self.gaugeDialog,size=(300,100))
		#sizer = wx.BoxSizer(wx.HORIZONTAL)
		dw, dh = panel.GetSize()
		gSize = (dw-dw//10,dh//3)
		location = (dw/2 - gSize[0]/2, dh/2 - gSize[1]/2)
		self.gauge = wx.Gauge(panel, wx.ID_ANY, total, size=gSize, pos=location)
		#sizer.Add(self.gauge,0,wx.EXPAND,0)
		#panel.SetSizer(sizer)
		self.gauge.SetRange(total)
		dw, dh = wx.DisplaySize()
		w, h = self.gaugeDialog.GetSize()
		x = dw/2 - w/2
		y = dh/2 - h/2
		#self.gaugeDialog.ShowModal()
		self.gaugeDialog.SetPosition((x,y))
		

		self.gaugeDialog.ShowModal()
		#self.panel_1.Disable()
	def updateGauge(self,num):
		self.gauge.SetValue(num)
	
	def runReports(self,event):
		self.threadReady = False
		self.reportThread = RunReportThread(self)
		self.reportThread.start()
	
	def exportReports(self,event):
		
		
		book = xlwt.Workbook()
		machine = " "
		for page in range(self.notebook.GetPageCount()):
			self.notebook.ChangeSelection(page)
			sheet = self.notebook.GetPageText(page)
			if sheet.split(' ')[0] != machine:
				machine = sheet.split(' ')[0]
				book.sheet = book.add_sheet(machine)
			sheet = sheet.split(' ')[1]
			book.sheet = book.add_sheet(sheet)
			thisList = self.notebook.GetChildren()[page].GetChildren()[0]
			rows = thisList.GetItemCount()
			columns = thisList.GetColumnCount()
			for column in range(columns):
				header = thisList.GetColumn(column).GetText()
				book.sheet.write(0,column,header)
				for row in range(rows):
					if column > 0 and column < columns-1:
						book.sheet.write(row+1,column,int(thisList.GetItemText(row,column)))
					else:
						book.sheet.write(row+1,column,thisList.GetItemText(row,column))
		saveDlg = wx.FileDialog(self,message = "Save Workbook as...", style=wx.FD_SAVE)
		if saveDlg.ShowModal()== wx.ID_OK:
			path = saveDlg.GetPath()
			book.save(path)
			wx.MessageBox("Workbook SAVED as: %s"% path,"SUCCESS")
			
	def getPercent(self,crtl):
		lastColumn = crtl.GetColumnCount()
		lastRow = crtl.GetItemCount() - 1
		crtl.InsertColumn(lastColumn,"PERCENT")
		total = int(crtl.GetItemText(lastRow,lastColumn-1))
		for i in range (lastRow):
			val = int(crtl.GetItemText(i,lastColumn-1))
			if total == 0:
				percent = 0
			else:
				percent = float(val) / float(total) * 100.0
			percentStr = ("%.2f" % percent)+" %"
			crtl.SetStringItem(i,lastColumn, percentStr)
				
			
	
	def getTotals(self,crtl):
		for j in range (crtl.GetColumnCount()-1):
			if j == 0:
				continue
			totalNum = 0
			for k in range (crtl.GetItemCount()-1):
				totalNum+=int(crtl.GetItemText(k,j))
			crtl.SetStringItem(k+1,j, str(totalNum))

		for j in range(crtl.GetItemCount()):
			totalNum = 0
			for k in range(crtl.GetColumnCount()-1):
				if k == 0:
					continue
				totalNum+=int(crtl.GetItemText(j,k))
			crtl.SetStringItem(j,k+1, str(totalNum))
	
	
	def toggleWeekly(self,event):
		box = event.GetEventObject()
		if box.IsChecked():
			self.levelListBox.Disable()
			self.hourReports = False
			self.weeklyReports = True
			self.hourBox.SetValue(False)
			self.hourBox.Disable()
		else:
			self.weeklyReports = False
			self.levelListBox.Enable()
			self.hourBox.Enable()
	
	def toggleHour(self,event):
		box = event.GetEventObject()
		if box.IsChecked():
			self.levelListBox.Disable()
			self.hourReports = True
			self.weeklyReports = False
			self.weeklyBox.SetValue(False)
			self.weeklyBox.Disable()
		else:
			self.hourReports = False
			self.levelListBox.Enable()
			self.weeklyBox.Enable()

	def reSort(self, event):
		reSortedDict = dict(self.reportDict)
		print reSortedDict
	
	def toggleCal(self,event):
		box = event.GetEventObject()
		calendar = box.GetContainingSizer().GetChildren()[1].GetWindow()
		if box.IsChecked():
			calendar.Enable()
		else:
			calendar.Disable()
		if not self.startCheckbox.IsChecked():
			self.startDateSelection = "%"
		if not self.endCheckbox.IsChecked():
			self.endDateSelection = wx.DateTime.Today().__add__(wx.DateSpan(days=1)).FormatISODate().replace('-',"")
			


	def SetDate(self,event):
		if self.startCheckbox.IsChecked():
			self.startDateSelection = self.startDate.GetValue().FormatISODate().replace('-',"")
			#self.endDate.SetRange(self.startDate.GetValue(),self.startDate.GetValue().__add__(wx.DateSpan(years=5)))
			#self.endDate.SetRange(self.startDate.GetValue().__add__(wx.DateSpan(days=1)),wx.DateTime.Today().__add__(wx.DateSpan(days=1)))
			#self.endDate.SetValue(wx.DateTime.Today().__add__(wx.DateSpan(days=1)))
		if self.endCheckbox.IsChecked():
			self.endDateSelection = self.endDate.GetValue().FormatISODate().replace('-',"")

	def onAll(self,event):
		catergory = event.GetEventObject().cat
		if catergory == "MAJOR":
			for i,_ in enumerate(self.majorList):
				self.majorListBox.Check(i,True)
		elif catergory == "LEVEL":
			for i,_ in enumerate(self.levelList):
				self.levelListBox.Check(i,True)
		elif catergory == "MACHINE":
			for i,_ in enumerate(self.machineList):
				self.machineListBox.Check(i,True)
	
	def onClear(self,event):
		catergory = event.GetEventObject().cat
		if catergory == "MAJOR":
			for i,_ in enumerate(self.majorList):
				self.majorListBox.Check(i,False)
		elif catergory == "LEVEL":
			for i,_ in enumerate(self.levelList):
				self.levelListBox.Check(i,False)
		elif catergory == "MACHINE":
			for i,_ in enumerate(self.machineList):
				self.machineListBox.Check(i,False)
# end of class MyFrame
class MyApp(wx.App):
	def OnInit(self):
		if os.path.isfile(PASSFILE):
		#check that the password file exists
			with open(PASSFILE,'r') as dataFile:
			#load the json file into a dict
				self.passDict = json.load(dataFile) # load json info into a list of dicts
		else:
			try:
				raise OSError ('\"PassList\" File is Corrupt or Missing')
			except OSError as error:
				print error
				sys.exit(1)
		
		self.frame = MyFrame(None, wx.ID_ANY, "")
		self.SetTopWindow(self.frame)
		self.frame.Show()
		return True

# end of class MyApp

if __name__ == "__main__":
	gettext.install("app") # replace with the appropriate catalog name
	app = MyApp(0)
	#wx.lib.inspection.InspectionTool().Show()
	app.MainLoop()


