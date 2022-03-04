# Programa CONTROL TRACKING C-ELEGANCE ONLINE
# 2017 F Xavier Gomez <fxgomezco@microscopiaoberta.com>

import numpy as np
import math
import time
from queue import Queue
from threading import Thread

from controlMot import ArduMot
from encoders import Encoder

import configparser

OVERCORR = 0.9

class RunTracker:

    def __init__(self, projectConfig, spinCam):

        # LIMITS AREA PLATINA (microns)
        self.xMax = int(projectConfig.get('TRACKER','_xMax'))
        self.xMin = int(projectConfig.get('TRACKER','_xMin'))
        self.yMax = int(projectConfig.get('TRACKER','_yMax'))
        self.yMin = int(projectConfig.get('TRACKER','_yMin'))
        self.zMax = int(projectConfig.get('TRACKER','_zMax'))
        self.zMin = int(projectConfig.get('TRACKER','_zMin'))

        # image size        
        self.imgW = int(projectConfig.get('CAM', '_imgW'))
        self.imgH = int(projectConfig.get('CAM', '_imgH'))

        # units conversion
        _fieldX = int(projectConfig.get('TRACKER','fieldX'))
        self.microns2Px = self.imgW /_fieldX
        self.px2microns = _fieldX /self.imgW
        
        # AREA DETECCIO MOVIMENT (px)
        # circle max./min radius (microns)
        _cMax = int(projectConfig.get('TRACKER','_cMax'))
        _cMin = int(projectConfig.get('TRACKER','_cMin'))
        self.maxC = int(_cMax *self.microns2Px)
        self.minC = int(_cMin *self.microns2Px)

        self.spinCam = spinCam
        
        self.currX, self.currY, self.currZ = self.xMax //2, self.yMax //2, 0

        _port = projectConfig.get('MOT', '_port')
        _baud = int(projectConfig.get('MOT', '_baud'))
        self.motor = ArduMot(_port, _baud, spinCam.positionQ)

        self.motor.start()            
        time.sleep(2.0) #Att!! DO NOT REMOVE (time to set the serial channel up and running >= 2 sec.)
        self.motor.reset()   
        self.motor.move2(self.currX, self.currY, self.currZ)
        print('init. position :', (self.currX, self.currY, self.currZ))
        print('motor position :', self.motor.position())

        self.fRate = 0
        self.fRateCounter = 0
        self.fRateTimer = time.time()

        self.running = False


    def start(self):

        self.fRate = 0
        self.fRateCounter = 0
        self.fRateTimer = time.time()

        self.spinCam.tracking = True
        self.running = True # Att.!! set True before launching thread

        t = Thread(target = self.update, args=())
        t.daemon = True
        t.start()

        return self


    def stop(self):

        self.spinCam.tracking = False
        self.running = False

#       self.motor.stop()     # Can NOT be done here, otherwise cam can not be manually moved once tracking is stop

    def frameRate(self):
        
        elapseTime = time.time() -self.fRateTimer
        self.fRateCounter += 1
        if elapseTime > 2:
            self.fRate = round(self.fRateCounter /elapseTime, 2)
            self.fRateCounter = 0
            self.fRateTimer = time.time()

    def readQ(self):
        try:
            if not self.spinCam.running:
                print('+++ Please, start cam !!')
            else:
                while not self.spinCam.trackerQ.qsize() > 0:
                    time.sleep(0.01)    # Att!! critical value, do NOT change
                while self.spinCam.trackerQ.qsize() > 0:
                    qGet = self.spinCam.trackerQ.get()
                return qGet
        except:
            print('+++ tracker.readQ(): Error')
        
    def update(self):

        while self.running:

            try:

                blobCenter = self.readQ()

                if len(blobCenter):

                    deltaX = blobCenter[0] - self.imgW//2
                    deltaY = blobCenter[1] - self.imgH//2

                    if (math.hypot(deltaX, deltaY) > self.minC):

                        self.currX = round(self.currX + deltaX *self.px2microns *OVERCORR, 0)
                        self.currY = round(self.currY + deltaY *self.px2microns *OVERCORR, 0)

                        self.motor.move2(self.currX, self.currY, self.currZ)
                        self.updXYZ()

            except Exception as e:
                print('+++ runTracker.update(): Error')
                print(e)
                
            self.frameRate()
    
    def updXYZ(self):
        
        try:
            currXYZ = self.motor.position()
            if len(currXYZ):
                self.currX, self.currY, self.currZ = currXYZ
        except:
            print('+++ _tracker.updXYZ(): Error in self.motor.position()')
        
        try:
            if self.spinCam.positionQ.full(): self.spinCam.positionQ.get()
            self.spinCam.positionQ.put((self.currX, self.currY, self.currZ))
        except:
            print('+++ _tracker.updXYZ(): Error in self.spinCam.positionQ.put()')
        
