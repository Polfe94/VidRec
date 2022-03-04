# -*- coding: utf-8 -*-
# microTracking cpu version (01/10/2002)

import kivy

from kivy.app import App
from kivy.lang import Builder

from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.properties import ObjectProperty
from kivy.uix.button import Button
from src.kivy_matplotlib import MatplotFigure
#from filebrowser import FileBrowser

from kivy.uix.gridlayout import GridLayout
from kivy.uix.colorpicker import ColorPicker
from kivy.clock import Clock
from kivy.uix.popup import Popup
from kivy.graphics.texture import Texture

from kivy.config import Config
Config.set('graphics','minimum_width','1280')
Config.set('graphics','minimum_height','720')
Config.set('graphics','width','1440')
Config.set('graphics','height','800')
Config.write()

import os
import cv2
import numpy as np
import math, time
from threading import Thread
from queue import Queue
from datetime import timedelta
from time import sleep

from matplotlib import style
import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties
import matplotlib.cm as cm

import spinCam
import videoWriter
import dataWriter
import runTracker

import configparser

'''
Image to kivy texture conversion
'''

def img2Texture(img):
    #frm = frm.astype(np.uint8)
    texture1 = Texture.create(size = (img.shape[1], img.shape[0]), colorfmt = 'bgr')
    texture1.blit_buffer(img.tostring(), colorfmt = 'bgr', bufferfmt = 'ubyte')
    return texture1

'''
mainGUI Controller
'''

class MainGUI(BoxLayout):

    def setup(self):

        self.icon = 'lib/ICONA_WINKOMS.ico'

        self.ids.sliderexp.value = _camExp
        self.ids.slidergain.value = _camGain
        self.ids.slidergamma.value = _camGamma
        self.ids.sliderThreshold.value = _thrVal
        
        self.ids.sliderMaxC.value = _cMax
        self.ids.sliderMinC.value = _cMin

        self.maxC = int(_cMax *_tracker.microns2Px)
        self.minC = int(_cMin *_tracker.microns2Px)

        self.fig_widget = self.ids['figDim']
        self.blnkPlot()

        self.showBlob = False
        self.showContour = False

        self.tStart = time.time()

    def readQ(self):
        try:
            if not _spinCam.running:
                print('+++ Please, start cam !!')
            else:
                while not _spinCam.mainQ.qsize() > 0:
                    time.sleep(0.01)    # Att!! critical value, do NOT change
                while _spinCam.mainQ.qsize() > 0:
                    qGet = _spinCam.mainQ.get()
                return qGet
        except:
            print('+++ main.readQ(): Error')

    def update(self, dt):
        
        elapseTime, frm, blobContour, contour, centroid, trackerX, trackerY, trackerZ = self.readQ()

        self.ids.txtTime.text = str(timedelta(seconds = elapseTime))[:9]

        self.ids.txtX.text = str(trackerX)
        self.ids.txtY.text = str(trackerY)
        self.ids.txtZ.text = str(trackerZ)
        
        self.ids.cam_frmRate.text = str(_spinCam.fRate)
        self.ids.trk_frmRate.text = str(_tracker.fRate)
        
        self.ids.vWrt_frmRate.text = str(_vWriter.fRate)
        self.ids.dWrt_frmRate.text = str(_dWriter.fRate)

        if _tracker.running:
            self.updateScatter(trackerX, trackerY)

        img = frm.get().astype(np.uint8)
        self.showHistogram(img)
            
        if centroid != (-1, -1):
            cv2.circle(img, centroid, 5, (0, 0, 255), -1)

        if self.showBlob and blobContour.shape[0]:
            cv2.drawContours(img, [blobContour], -1, (0, 255, 0), 2)

        if self.showContour and contour.shape[0]:
            cv2.drawContours(img, [contour], -1, (0, 255, 255), 2)

        img = cv2.circle(img, (_imgHalfW, _imgHalfH), self.maxC, (255, 0, 128), 1)
        img = cv2.circle(img, (_imgHalfW, _imgHalfH), self.minC, (255, 128, 0), 1)
        img = cv2.line(img, (_imgHalfW, _imgHalfH -self.minC //2), (_imgHalfW, _imgHalfH +self.minC //2), (128, 128, 0), 2)
        img = cv2.line(img ,(_imgHalfW -self.minC //2, _imgHalfH), (_imgHalfW +self.minC //2, _imgHalfH), (128, 128, 0), 2)

        self.ids.imViewer.texture = img2Texture(img)

    '''
    trajectory plot
    '''

    def blnkPlot(self):

        style.use('seaborn')
        self.fig= plt.figure(figsize = (1, 1), constrained_layout = True)
        self.axes = self.fig.add_subplot(111)

        self.axes.grid(True)
        self.axes.set_xlabel('mm',fontsize='small')
        self.axes.set_title('path',fontsize='small')
        self.axes.set_xlim(_tracker.xMin //1000, _tracker.xMax //1000)
        self.axes.set_ylim(_tracker.yMin //1000, _tracker.yMax //1000)

        x0, y0 = (_tracker.xMax-_tracker.xMin) //2000, (_tracker.yMax-_tracker.yMin) //2000
        circle = plt.Circle((x0, y0), x0, fill = False, ls = '--')
        self.axes.add_artist(circle)

        self.pltAdd = 121
        self.updateScatter(x0, y0)
        self.plotUpdate()

    def updateScatter(self, trackerX, trackerY):

        if self.pltAdd > 120:
            self.axes.scatter(trackerX /1000, trackerY /1000, s = 0.5, c ='b')
            self.pltAdd = 0
        else:
            self.pltAdd += 1

    def plotUpdate(self):
        self.fig.canvas.draw()
        self.fig_widget.figure = self.fig
        

    '''
    tracking control
    '''

    def Track(self):

        if not _tracker.running:
            _tracker.BCKSUB = self.ids.sliderBksub.value
            _tracker.start()
            _dWriter.start()
            _vWriter.tracking = True
            self.blnkPlot()
            self.ids.btnTrack.background_color = 1,0,1,1
        else:
            _dWriter.stop()
            _vWriter.tracking = False
            _tracker.stop()
            self.ids.btnTrack.background_color = 1,1,1,1
            if self.showBlob:
                self.showBlob = not self.showBlob
                self.ids.btnShowBlob.background_color = 1,1,1,1

    def ShowBlob(self):

        self.showBlob = not self.showBlob
        if self.showBlob:
            self.ids.btnShowBlob.background_color = 1,0,1,1
        else:
            self.ids.btnShowBlob.background_color = 1,1,1,1

    def ShowContour(self):

        self.showContour = not self.showContour
        _spinCam.showContour = not _spinCam.showContour
        if self.showContour:
            self.ids.btnShowContour.background_color = 1,0,1,1
        else:
            self.ids.btnShowContour.background_color = 1,1,1,1

    '''
    video writer control
    '''

    def Rec(self):

        if not _vWriter.running:
            _vWriter.start(_tracker.running)
            self.ids.btnRec.background_color = 1,0,1,1
        else:
            _vWriter.stop()
            self.ids.btnRec.background_color = 1,1,1,1


    '''
    camera color histogram
    '''

    def showHistogram(self, frm):

        hImg = np.zeros((150, 275, 3))
        bins = np.arange(256).reshape(256,1)

        for chn, col in enumerate([(255, 0, 0), (0, 255, 0), (0, 0, 255)]):
            hItem = cv2.calcHist([frm], [chn], None, [256], [0, 255])
            cv2.normalize(hItem, hItem, 0, 150, cv2.NORM_MINMAX)
            hist = np.int8(np.around(hItem))
            pts = np.column_stack((bins, hist))
            cv2.polylines(hImg, [pts], False, col, thickness = 1)

        self.ids.histViewer.texture = img2Texture(cv2.resize(hImg, (800, 200)).astype(np.uint8))

    '''
    tune camera parameters
    '''

    def setExp(self, *args):
        exp = int(args[1])
        self.ids.text = str(exp) +' ms'
        _spinCam.setExp(exp)

    def setGain(self, *args):
        gain = float(args[1])
        _spinCam.setGain(gain)

    def setGamma(self, *args):
        gamma = float(args[1])
        _spinCam.setGamma(gamma)

    '''
    tune tracking parameters
    '''

    def setThrVal(self, *args):
        _spinCam.thrVal = int(args[1])
        self.ids.sliderThreshold.value = _spinCam.thrVal

    def setMaxC(self, *args):
        self.maxC = int(args[1] *_tracker.microns2Px)
        _tracker.maxC = int(args[1] *_tracker.microns2Px)
        _spinCam.maxC = int(args[1] *_spinCam.microns2Px)

    def setMinC(self, *args):
        self.minC = int(args[1] *_tracker.microns2Px)
        _tracker.minC = int(args[1] *_tracker.microns2Px)
        _spinCam.minC = int(args[1] *_spinCam.microns2Px)

    def setBksub(self, *args):
        _spinCam.bkgUpd = int(args[1])
        self.ids.sliderBksub.value = _spinCam.bkgUpd

    '''
    manual cam movement
    '''

    def moveRight(self):
        try:
            _tracker.currX = min(_tracker.currX +_xStp, _xMax)
            _tracker.motor.move2(_tracker.currX, _tracker.currY, _tracker.currZ)
            _tracker.updXYZ()
        except:
            pass
        
    def moveLeft(self):
        try:
            _tracker.currX = max(_tracker.currX -_xStp, _xMin)
            _tracker.motor.move2(_tracker.currX, _tracker.currY, _tracker.currZ)
            _tracker.updXYZ()
        except:
            pass

    def moveUP(self):
        try:
            _tracker.currY = min(_tracker.currY +_yStp, _yMax)
            _tracker.motor.move2(_tracker.currX, _tracker.currY, _tracker.currZ)
            _tracker.updXYZ()
        except:
            pass

    def moveDOWN(self):
        try:
            _tracker.currY = max(_tracker.currY -_yStp, _yMin)
            _tracker.motor.move2(_tracker.currX, _tracker.currY, _tracker.currZ)
            _tracker.updXYZ()
        except:
            pass

    def moveZU(self):
        try:
            # manual focus on the fly (tracking on)
            _tracker.currZ = min(_tracker.currZ +_zStp, _zMax)
            if not _tracker.running:
                # manual focus on stop (tracking of)
                _tracker.motor.moveZ(_tracker.currZ)
                _tracker.updXYZ()
        except:
            pass

    def moveZD(self):
        try:
            # manual focus on the fly (tracking on)
            _tracker.currZ = max(_tracker.currZ -_zStp, _zMin)
            if not _tracker.running:
                # manual focus on stop (tracking of)
                _tracker.motor.moveZ(_tracker.currZ)
                _tracker.updXYZ()
        except:
            pass

    '''
    capture a single image
    '''

    def SaveSingleIm(self):
        pass

    '''
    choose folder
    '''

    def select(self):
        pass

    def iniFile(self):
        pass

    def outFile(self):
        pass

    '''
    ?
    '''

    def startRun(self):
        pass
        # _tracker.RUNTRACK = True


class MainGUIApp(App):

    def build(self):

        self.load_kv('./mainGUI.kv')

        mainGUI = MainGUI()
        mainGUI.setup()

        Clock.schedule_interval(mainGUI.update, 1/60)  # GUI refresh rate

        return mainGUI

if __name__ == '__main__':
    
    # project setup    
    projectConfig = configparser.ConfigParser()
    projectConfig.read('./projectSetup.ini')
     
    # cam settings
    _camExp = int(projectConfig.get('CAM','exp'))
    _camGain = int(projectConfig.get('CAM','gain'))
    _camGamma = float(projectConfig.get('CAM','gamma'))
    # cam movement area
    _xMax = int(projectConfig.get('TRACKER','_xMax'))
    _xMin = int(projectConfig.get('TRACKER','_xMin'))
    _yMax = int(projectConfig.get('TRACKER','_yMax'))
    _yMin = int(projectConfig.get('TRACKER','_yMin'))
    _zMax = int(projectConfig.get('TRACKER','_zMax'))
    _zMin = int(projectConfig.get('TRACKER','_zMin'))
    # cam movement steps
    _xStp = int(projectConfig.get('MOT','_xStp'))
    _yStp = int(projectConfig.get('MOT','_yStp'))
    _zStp = int(projectConfig.get('MOT','_zStp'))
    # image size
    _imgW = int(projectConfig.get('CAM', '_imgW'))
    _imgH = int(projectConfig.get('CAM', '_imgH'))
    _imgHalfW = _imgW //2
    _imgHalfH = _imgH //2
    # circle max./min radius (microns)
    _cMax = int(projectConfig.get('TRACKER','_cMax'))
    _cMin = int(projectConfig.get('TRACKER','_cMin'))
    _thrVal = int(projectConfig.get('TRACKER','_thrVal'))

    # setting for run/test (realCam /video)
    spinCam._realCam = True
 
    # go
    _spinCam = spinCam.SpinCam(projectConfig, queueSize = 48)
    _tracker = runTracker.RunTracker(projectConfig, _spinCam)   
    _dWriter = dataWriter.DataWriter(projectConfig, _spinCam)
    _vWriter = videoWriter.VideoWriterQR(projectConfig, _spinCam)
 
    _spinCam.start()
    MainGUIApp().run()
 
    if _vWriter.running: _vWriter.stop()
    if _dWriter.running: _dWriter.stop()
    if _tracker.running:
        _tracker.motor.stop()
        _tracker.stop()
    if _spinCam.running: _spinCam.stop()
     
    del _vWriter
    del _dWriter
    del _tracker
    del _spinCam
    spinCam.instanceRelease()
