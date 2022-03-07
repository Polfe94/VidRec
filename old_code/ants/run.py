# Programa test per optimitzar els FPS maxims 
# 2018 F Xavier Gomez <fxgomezco@microscopiaoberta.com>

"""
ATENCIO ASIGNAR 3000MB AL USB O NO AGUANTA TOTES LES 12 CAMERES ALHORA!!!!
"""

import cv2
import time
import gettext
import sys
import wx
import os
import numpy as np
import flycapture2 as fc2

from pFlyCapThreaded import FlyCapThreaded as PtThreaded

from time import sleep
from threading import Thread
from numpy import float32
from Queue import Queue


actExp = 60
genGain = 8
FOut = False #Show print outputs for debug
EXIT = False

BINNIG = True

FRMCAM = 10.0
serialStrobe = 17179428
RGB = False

_runPath = "/home/bigtracker/tracking/runs/"

class ControlArrayGUI(wx.Frame):
    
    fps = FRMCAM
    iniCaptime=0
    actCaptime=0
    capturing = False
    TRACK = False
    
    resizeX = 240
    resizeY = 195
    
    
    folderA =''
    
    sizeApp = (1300, 800)
    
    nEvents = 1
    timeBetEvents = 5
    secondsPerEvents = 10800
    
    CamPreview = False
    compt = 0
    
    def __init__(self,*args,**kwds):
        
        colPreview = 3
        filesPreview = 4
        
        wx.Frame.__init__(self,*args,**kwds)
        
        panel = wx.Panel(self,pos= (0,0),size=self.sizeApp)
        
        style = self.GetWindowStyle()
        
        self.CamPreview = False
       
        self.panoViewer = []
    
        iniPos = (425,10)
        sizeCam = (self.resizeX,self.resizeY)
        actCam = 0
        for y in range(filesPreview):
            for x in range(colPreview):
                if actCam<12:
                    posx = iniPos[0]+sizeCam[0]*x
                    posy = iniPos[1]+sizeCam[1]*y
                    self.panoViewer.append(wx.StaticBitmap(panel,pos=(posx,posy),size=sizeCam, style = wx.RAISED_BORDER ))
                actCam +=1
        
        self.panoViewer.append(wx.StaticBitmap(panel,pos=(1200,100),size=sizeCam, style = wx.RAISED_BORDER ))
        self.panoViewer.append(wx.StaticBitmap(panel,pos=(1200,400),size=sizeCam, style = wx.RAISED_BORDER ))

        '''Creo Botons'''
        midaBotons = (200,30)
        sizeTxt = (100,20)
        self.botStartCam = wx.Button(panel,label="Start Cameras",pos = (10,10),size= midaBotons)
        self.botStopCam = wx.Button(panel,label=("Stop Cameras"),pos = (10,50),size= midaBotons)

        
        self.botExpUp = wx.Button(panel,label=("Incr Exposure"),pos = (10,170),size= midaBotons)
        self.botExpDown = wx.Button(panel,label=("Decr Exposure"),pos = (10,210),size= midaBotons)
        
        self.botDirSel = wx.Button(panel,label=("Select Folder"),pos = (10,250),size= midaBotons)
        
        self.lblExp = wx.StaticText(panel,-1,"Exp",(240,180))
        self.lblDirSelA = wx.StaticText(panel,-1,"FolderA",(240,260))
        self.cbIm = wx.CheckBox(panel,label ="Save Images",pos = (240,100))
        
        self.botExit= wx.Button(panel,label=("Sortir"),pos = (10,590),size= (200,60))
        
        self.lblIntervalometer = wx.StaticText(panel,label="Intervalometer Parameters",pos = (20,330))
        
        self.lblnSec = wx.StaticText(panel,label="Seconds to capture",pos=(240,60))
        self.nSec = wx.TextCtrl(panel,pos=(240,10),size=(100,20),style = wx.TE_RIGHT)
        self.nSec.SetValue('10')
        
        self.lblnEvents = wx.StaticText(panel,label="N Events",pos = (10,370))
        self.txtnEvents = wx.TextCtrl(panel,pos = (240,370),size=sizeTxt,style= wx.TE_RIGHT)
        self.txtnEvents.SetValue(str(self.nEvents))
        
        
        self.lblnTimebetEvents = wx.StaticText(panel,label="Wait time between Events",pos = (10,410))
        self.txtTimebetEvents = wx.TextCtrl(panel,pos = (240,410),size=sizeTxt,style= wx.TE_RIGHT)
        self.txtTimebetEvents.SetValue(str(self.timeBetEvents))
        
        self.lblsecondsPerEvents = wx.StaticText(panel,label="N Seconds for Events",pos = (10,450))
        self.txtsecondsPerEvents = wx.TextCtrl(panel,pos = (240,450),size=sizeTxt,style= wx.TE_RIGHT)
        self.txtsecondsPerEvents.SetValue(str(self.secondsPerEvents))
        
        self.botStartEventCapt = wx.Button(panel,label="Start Event Capture",pos=(10,490),size= (200,60))
        self.botStartEventCapt.Disable()
        
        self.__set_properties()

        '''Asigno Events'''
        self.Bind(wx.EVT_BUTTON,self.initPreview,self.botStartCam)
        self.Bind(wx.EVT_BUTTON,self.StopCameras,self.botStopCam)
        self.Bind(wx.EVT_BUTTON,self.ExitPrograma,self.botExit)
        self.Bind(wx.EVT_BUTTON,self.expUp,self.botExpUp)
        self.Bind(wx.EVT_BUTTON,self.expDown,self.botExpDown)
        self.Bind(wx.EVT_BUTTON,self.selecFolder,self.botDirSel)
        self.Bind(wx.EVT_BUTTON,self.launchCapEvent,self.botStartEventCapt)
        self.Bind(wx.EVT_CLOSE,self.ExitPrograma)
        
        self.__close_callback = None
        self.Bind(wx.EVT_CLOSE, self._when_closed)
        
        self.counter = 0
        
        '''Inicio temporitzador per controlar Events'''
        self.fpstimer = wx.Timer(self)
        self.fpstimer.Start(1000)
        self.Bind(wx.EVT_TIMER,self.onNextFrame,self.fpstimer)
        
        #Thread(target=self.refreshPreview,args=()).start()
        
    
    def __set_properties(self):    
        self.SetTitle(_("Control Array CAM LEOV"))
        self.SetSize(self.sizeApp)
        self.SetPosition((0,0))
    
    def launchCapEvent(self,evt):
        self.StopCameras(evt)
        sleep(1)
        startCapEv = Thread ( target=self.captureEvent,args=())
        startCapEv.start()
        evt.Skip()
        return
    
    def captureEvent(self):
        
        for i in range(len(AcoCAMArray.cameras)):
            AcoCAMArray.cameras[i].CamPreview = False

        timeBetEvents = int(self.txtTimebetEvents.GetValue())
        secondsPerEvents = int(self.txtsecondsPerEvents.GetValue())
        
        
        self.nEvents =int(self.txtnEvents.GetValue()) 
        
        iniTime = time.time()
        MaxTime = iniTime+(self.nEvents*(timeBetEvents+secondsPerEvents))
        
        actCaptime =time.time()
        nEventsCpt = 1
        
        config= str(iniTime)+'\n'+self.txtnEvents.GetValue()+'\n'+self.txtTimebetEvents.GetValue()+'\n'+self.txtsecondsPerEvents.GetValue()                         
        with open (self.folderA+'configExp.txt','a') as file_object: #FX : EL ARXIU DE SORTIDA ES GUARDA EN LA MATEIXA CARPETA ON SON LES IMATGES A TRACTAR
            file_object.write(config)
        
        for t in range(self.nEvents):
            self.saveTh(secondsPerEvents)
            sleep(timeBetEvents)
        
        #self.saveTh(secondsPerEvents)
        '''
        while(actCaptime<MaxTime):
            if (actCaptime>=(self.nEvents*timeBetEvents+iniTime)):
                print('inicio captura event num=',nEventsCpt)
                self.saveTh(secondsPerEvents)
                nEventsCpt += 1
                if(self.EXIT):
                    break                
            actCaptime =time.time()
        '''
            
        print('FINAL captureEvent')
        self.botStartEventCapt.SetBackgroundColour((0,255,0))
        
        return
        
    def selecFolder(self,evt):
        
        selectorA = wx.DirSelector("Choose a folderA", default_path=_runPath)
        if selectorA.strip():
            print (selectorA)
            self.folderA = selectorA+os.sep
            self.lblDirSelA.SetLabelText(self.folderA)
        self.botStartEventCapt.Enable()
        evt.Skip()
        return
            
    def SaveIMG(self,evt):
        
        for i in range(len(AcoCAMArray.cameras)):
            AcoCAMArray.cameras[i].CamPreview = False

        Thread(target=self.saveTh,args=(self.nSec.GetValue(),)).start()
       
        evt.Skip()
        return
    
    def saveTh(self,secondsToCapture):
        
        print('Entro saveTh')
                
        iniCaptime = time.time()
        t2Cap = int(secondsToCapture)
        actCaptime =time.time()
        
        self.CamPreview = False
        for i in range(len(AcoCAMArray.cameras)):
            AcoCAMArray.cameras[i].CamPreview = False
        
        for i in range(len(AcoCAMArray.cameras)):
            AcoCAMArray.cameras[i].folderA = self.folderA
        
        for i in range(len(AcoCAMArray.cameras)):
                AcoCAMArray.cameras[i].RECEVENT = True
        
        actT = time.time()
        while((actT-iniCaptime)<=t2Cap):
            for c in range (AcoCAMArray.nCam):
                AcoCAMArray.triggerTH[c].put(True)
            actT = time.time()
        
        for i in range(len(AcoCAMArray.cameras)):
            AcoCAMArray.cameras[i].RECEVENT = False      
        sleep(0.5)            
            
        print ('Surto saveTh')

    
    def StopCameras(self,evt):
        
        self.CamPreview = False 
        
        for i in range(len(AcoCAMArray.cameras)):
            AcoCAMArray.cameras[i].CamPreview = self.CamPreview
        
        evt.Skip()
        return
    
    def initPreview(self,evt):        
        
        self.CamPreview = True
        
        for i in range(len(AcoCAMArray.cameras)):
            AcoCAMArray.cameras[i].CamPreview = self.CamPreview
        
        txtExp = str(actExp)+' ms'
        self.lblExp.SetLabelText(txtExp)
        evt.Skip()
        return
    
    def expUp(self,event):
        global actExp
        actExp = actExp+5
        if actExp>3000:
            actExp = 3000
                
        for i in range(len(AcoCAMArray.cameras)):
            AcoCAMArray.cameras[i].setExp(actExp)
            print ("Boto aumento Exp",actExp)
            txtExp = str(actExp)+' ms'
            self.lblExp.SetLabelText(txtExp)
        event.Skip()
        
    def expDown(self,event): 
        global actExp
        actExp = actExp-5
        if actExp <5:
            actExp = 5
            
        for i in range(len(AcoCAMArray.cameras)):
            #actexp = cameras[1].getExp()
            txtExp = str(actExp)+' ms'
            AcoCAMArray.cameras[i].setExp(actExp)
            
            print ("Boto disminueixo Exp")
            self.lblExp.SetLabelText(txtExp)
        event.Skip()
   
    
    def setIMG(self):
        
       # print('Entro en setIMG')
        for t in range (AcoCAMArray.nCam):
            try:
                img = AcoCAMArray.q[t].get()[0][...,::-1]
                npr = AcoCAMArray.q[t].get()[1]
                #print('npr ='+str(npr))
                img = img#cv2.resize(img,(self.resizeX,self.resizeY))
                h, w = img.shape[:2]
                
                #print('img shape = '+str(img.shape))
                wxbmp = wx.Image(w,h)
                wxbmp.SetData(img.tostring())
                
                #wxbmp = wx.Bitmap.FromBuffer(w,h,img)
                self.panoViewer[npr].SetBitmap(wxbmp.ConvertToBitmap())
            except:
                print('Error nCam '+ str(t))
            
        #print('Surto setIMG')
        return
        
    def onNextFrame(self,evt):
         
        #print (self.CamPreview)
         
        if self.CamPreview:
            self.setIMG()
        evt.Skip()
        
        return
    
    def refreshPreview(self):
        print (self.CamPreview)
        if self.CamPreview:
            self.setIMG()
        return
    
    def ExitPrograma(self,evt):
        
        self.EXIT = True
        
        self.rmvQelements()
        
        self.StopCameras(evt)
        
        for i in range(len(AcoCAMArray.cameras)):
            AcoCAMArray.cameras[i].stopped = True
            
        sys.exit(0)
    
    def register_close_callback(self, callback):
        self.__close_callback = callback

    def _when_closed(self, event):
        doClose = True if not self.__close_callback else self.__close_callback()
        if doClose:
            event.Skip()
            
    def rmvQelements(self):
        
        for t in range (AcoCAMArray.nCam):
            while not AcoCAMArray.q[t].empty():
                try:
                    AcoCAMArray.q[t].get(False)
                except Empty:
                    continue
                    AcoCAMArray.q[t].task_done()
                AcoCAMArray.q[t].task_done()
        
        for t in range (AcoCAMArray.nCam):
            while not AcoCAMArray.triggerTH[t].empty():
                try:
                    AcoCAMArray.triggerTH[t].get(False)
                except:
                    continue
                    AcoCAMArray.triggerTH[t].task_done()
                AcoCAMArray.triggerTH[t].task_done()         
       

class AcoCAMArray (wx.App):
    
    nCam = 12   
    q = []
    triggerTH = []
    cameras = []

    ''' INICI THREADS CAMERAS'''
    for i in range (nCam):
        q.append(Queue(1))
        triggerTH.append(Queue(1))
    
    for i in range(nCam):
        cam = PtThreaded(i, triggerTH[i], q[i]).start()
        cameras.append(cam)
        print ('object cam Initialized',cam)
    
    def OnInit(self):
        frame = ControlArrayGUI(None,wx.ID_ANY,"")
        frame.Show()
        return True

if __name__ == "__main__":
	
    gettext.install("app")
    app=AcoCAMArray(0)
    app.MainLoop()
