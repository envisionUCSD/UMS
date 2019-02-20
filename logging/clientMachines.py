#!/usr/bin/env python
# -*- coding: UTF-8 -*-

import wx, threading, csv, os
from wx.lib.pubsub import pub 
import subprocess, time, datetime

#platform check, useful for GUI layout
if wx.Platform == "__WXMSW__":
	MSW = True
	GTK = False
else:
	GTK = True
	MSW = False

#hardcoded number of machines, that I should probably tie to /etc/hosts
NUMMACHINES = 16

#threaded instance that pings a machine and checks for a response
#if the machine does/not reply, the GUI is updated accordingly with a CallAfter
#output from subprocess is piped to dev/null
class PingThread(threading.Thread):
	def __init__(self,machine):
	#machine is an element in the list of machines (includes status, bitmap, etc). I should turn this into an object.
		self.machine=machine
		threading.Thread.__init__(self)
		self.runFlag = True #run Flag indicates the thread is still running. Can be called externally to end the thread
		
	#required function called by start()
	def run(self):
		ip = self.machine.box.GetLabel()
		i=0 #counter for pings, I don't want more than three attempts
		#pipe all output to dev/null
		with open(os.devnull, 'w') as blackHole:
			while self.runFlag:
			#run until timer expires or kill flag is set
				response = subprocess.call(['ping', '-c', '1', ip],stdout=blackHole, stderr=blackHole)
				#ping return is 0 for a success, 2 for machine didn't respond, >0 for everything else
				if response == 0:
					if self.machine.status!="UP":
						self.machine.status="UP"
					self.stop()
				else:
					if i>=3:
						if self.machine.status!="DOWN":
							self.machine.status="DOWN"
						self.stop()
					else:
						i+=1
		#we let the GUI handle all of the GUI work. We simply change the machine status based on the ping result
		#and then send to updateFromThread
		wx.CallAfter(app.frame.updateFromThread, self.machine)		

	def stop(self):
	#Set the run flag to end the thread. Usefull for terminating a thread from somewhere else
		self.runFlag = False

class MainWindow(wx.Frame):
	def __init__(self):
		styleFlags = wx.DEFAULT_FRAME_STYLE# | wx.NO_BORDER# | wx.FRAME_NO_TASKBAR
		if GTK:
			styleFlags = wx.DEFAULT_FRAME_STYLE# | wx.STAY_ON_TOP
		wx.Frame.__init__(self, None, title = "EnVision Client Machines", style=styleFlags)
		self.panel_1 = wx.Panel(self, wx.ID_ANY)
		self.sizer4 = wx.BoxSizer(wx.VERTICAL)
		self.grid_sizer1 = wx.GridSizer(app.grids, app.grids, app.grid_gap, app.grid_gap)
		self.infoSizer = wx.BoxSizer(wx.HORIZONTAL)
		updateTime = "Last Updated @ xxxx" #+ now.strftime("%H:%M")
		self.updateText=(wx.StaticText(self,-1,updateTime,style = wx.ALIGN_CENTER_HORIZONTAL))
		updateFont = wx.Font(12,wx.FONTFAMILY_SWISS,wx.FONTSTYLE_ITALIC,wx.FONTWEIGHT_NORMAL)
		self.updateText.SetFont(updateFont)
		printerInfoFont = wx.Font(app.printerFontSize,wx.FONTFAMILY_SWISS,wx.FONTSTYLE_NORMAL,wx.FONTWEIGHT_NORMAL)
		self.statusLight=[]
		self.clientDict = {}
		with open("/etc/hosts",'r') as hostsFile:
			ipReader = csv.reader(hostsFile,delimiter='\t')
			for hosts in ipReader:
				if hosts[0].startswith("192"):
					self.clientDict[hosts[1]]=hosts[0]
		self.pingNum = 0
		clientList = []
		for host in self.clientDict:
			clientList.append((host,self.clientDict[host]))
		self.sortedClients = sorted(clientList,key = lambda x: x[0].upper())
		for i in xrange(NUMMACHINES):
			if i < len(self.sortedClients):
				self.statusLight.append(wx.StaticBitmap(self.panel_1, wx.ID_ANY, app.bitmaps["machineDown"], style = wx.NO_BORDER))
				machineLabel = self.sortedClients[i][0]
				machineIP = self.sortedClients[i][1]
				status = "DOWN"
			else:
				self.statusLight.append(wx.StaticBitmap(self.panel_1, wx.ID_ANY, app.bitmaps["noMachine"], style = wx.NO_BORDER))
				machineLabel = "---"
				machineIP = "XXX.XXX.XXX"
				status = None 
			
			this = self.statusLight[-1]
			this.status = status
			this.machineName = wx.StaticText(self.panel_1, label=machineLabel,style=wx.ALIGN_CENTRE_HORIZONTAL|wx.ST_NO_AUTORESIZE)
			this.machineName.SetFont(printerInfoFont)
			this.sizer = (wx.StaticBoxSizer(wx.StaticBox(self.panel_1, wx.ID_ANY, machineIP), wx.VERTICAL))
			this.box = this.sizer.GetStaticBox()
			this.pingWorker = PingThread(this)
			#this.Bind(wx.EVT_BUTTON, self.onClick)
		
		
		self.Bind(wx.EVT_SIZE,self.onResize)
		#set the timer as a wx Timer
		self.pingTimer = wx.Timer(self)
		#and bind it to a function
		self.Bind(wx.EVT_TIMER,self.ping,self.pingTimer)
		self.__do_layout()
		#start a oneshot one minute timer
		self.pingTimer.Start(5000,oneShot=True)
	def updateFromThread(self,machine):
		if machine.status=="UP":
			machine.SetBitmap(app.bitmaps["machineUp"])
		elif machine.status=="DOWN":
			machine.SetBitmap(app.bitmaps["machineDown"])
		else:
			machine.SetBitmap(app.bitmaps["noMachine"])
		machine.pingWorker = PingThread(machine)
		self.Layout()
		self.Refresh()
		if self.pingNum >= len(self.clientDict)-1:
			now = datetime.datetime.now()
			self.updateText.SetLabel("Last Updated @ " + now.strftime("%H:%M"))
			self.pingNum=0
		else:
			self.pingNum+=1
	def ping(self,event):
		print "in timer"
		with open("/etc/hosts",'r') as hostsFile:
			ipReader = csv.reader(hostsFile,delimiter='\t')
			for hosts in ipReader:
				if hosts[0].startswith("192"):
					name = hosts[1]
					ip = hosts[0]
					if name in self.clientDict:
						if ip == self.clientDict[name]:
							pass
						else:
							self.clientDict[name]=ip
							for machine in self.statusLight:
								if machine.machineName.GetLabel() == name:
									machine.box.SetLabel(ip)
									break
					else:
						self.clientDict[name] = ip
						for machine in self.statusLight:
							if machine.status == None:
								machine.status = "machineDown"
								machine.SetBitmap(app.bitmaps["machineDown"])
								machine.machineName.SetLabel(name)
								machine.box.SetLabel(ip)
								break
		for machine in self.statusLight:
			if machine.status != None:
				machine.pingWorker.start()
				time.sleep(0.5)
		self.pingTimer.Start(60000,oneShot=True)
	def onResize(self,newSize):
		winWidth = newSize.GetSize()[0]
		winHeight = newSize.GetSize()[1]
		app.__set_bitmaps__(winWidth,winHeight)
		for light in self.statusLight:
			if light.status == "DOWN":
				light.SetBitmap(app.bitmaps["machineDown"])
			elif light.status is None:
				light.SetBitmap(app.bitmaps["noMachine"])
			else:
				light.SetBitmap(app.bitmaps["machineUp"])
		self.Layout()
	def __set_properties(self):
		# begin wxGlade: MyFrame.__set_properties
		self.SetTitle(_("frame"))
		for light in self.statusLight:
			light.SetSize(light.GetBestSize())
			light.SetBitmapDisabled(self.bitmaps["machineDown"])

	def __do_layout(self):
		for light in self.statusLight:
			light.sizer.Add(light, 1, wx.ALL | wx.EXPAND, 0)
			light.sizer.Add(light.machineName,0,wx.CENTER)
			self.grid_sizer1.Add(light.sizer, 1, wx.ALL | wx.EXPAND, app.gridSizerBorder)
		self.panel_1.SetSizer(self.grid_sizer1)
		self.sizer4.Add(self.panel_1, 1, wx.EXPAND, 0)
		self.infoSizer.AddStretchSpacer(prop=1)
		self.infoSizer.Add(self.updateText,0,wx.EXPAND | wx.ALIGN_CENTER | wx.ALIGN_CENTER_HORIZONTAL | wx.CENTRE)
		self.infoSizer.AddStretchSpacer(prop=1)
		self.sizer4.Add(self.infoSizer,0,wx.TOP | wx.BOTTOM | wx.EXPAND,10)
		self.SetSizer(self.sizer4)
		self.sizer4.Fit(self)
		self.SetMinSize((650,500))
		self.Layout()
class MyApp(wx.App):
	def OnInit(self):
		self.bitmaps = {}
		self.gridSizerBorder = 5
		self.grid_gap = 5
		self.grids = 4
		self.printerFontSize = 10
		self.buttonSize = 60
		self.__set_bitmaps__()
		return True
	
	def __set_bitmaps__(self,dw=400,dh=800):
		imageDir = "/home/e4ms/job_tracking/images/"
		imageList = ["red_button.png","green_button.png","gray_button.png"]
		bitmaps = []
		bitmap_padding = 10
		bitmapWidth = (dw - 2 * self.gridSizerBorder - self.grid_gap)/self.grids - 2 * bitmap_padding
		bitmapHeight = (dh - 2*self.gridSizerBorder - self.grid_gap) / self.grids - 2 * bitmap_padding - self.buttonSize
		bitmapScale = bitmapHeight if bitmapHeight < bitmapWidth else bitmapWidth
		for image in imageList:
			bitmap = wx.Image(imageDir + image)
			W, H = bitmap.GetSize()
			proportion = float(W) / float(H)
			scaleH = bitmapScale
			scaleW = scaleH * proportion
			bitmap = bitmap.Scale(scaleW, scaleH, wx.IMAGE_QUALITY_HIGH)
			bitmaps.append(wx.BitmapFromImage(bitmap))
			mask = wx.Mask(bitmaps[-1], wx.WHITE)
			bitmaps[-1].SetMask(mask)
		self.bitmaps = {"machineUp":bitmaps[1], "machineDown":bitmaps[0], "noMachine":bitmaps[2]}
# end of class MyApp

if __name__ == "__main__":
	app = MyApp(0)
	app.frame = MainWindow()
	app.frame.Show()
	app.MainLoop()