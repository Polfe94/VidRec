# -*- coding: utf-8 -*-

import cv2
import numpy as np
from skimage.morphology import skeletonize

from threading import Thread
import json
import time

# import configparser


class DataWriter:

    def __init__(self, projectConfig, spinCam):

        self.imgW = int(projectConfig.get('CAM', '_imgW'))
        self.imgH = int(projectConfig.get('CAM', '_imgH'))
        
        _fieldX = int(projectConfig.get('TRACKER','fieldX'))
        self.px2mm = _fieldX /self.imgW /1000
        
        self.dtaPth = projectConfig.get('DATA','_dta')

        self.spinCam = spinCam
        
        self.jsonQ = {} 
        self.jsonTimer = time.time()

        self.fRate = 0
        self.fRateCounter = 0
        self.fRateTimer = time.time()
        
        self.running = False

    def start(self):

        fName = '%s/run_%s_%s' %(self.dtaPth, time.strftime("%y%m%d"), time.strftime("%H%M"))

        self.jsonFile = fName +'.json'
        
        self.dataFile = open(fName +'.txt', 'w')
        self.dataFile.write('time, frame, camX, camY, cntrX, cntrY \n')
        
        print('+++ start %s' % fName)

        self.fRate = 0
        self.fRateCounter = 0
        self.fRateTimer = time.time()

        self.jsonQ = {}
        self.jsonTimer = time.time()
        self.running = True

        t = Thread(target = self.update, args=())
        t.daemon =True
        t.start()

        return self

    def stop(self):

        self.fRate = 0
        self.running = False
        time.sleep(0.1)
        
        self.dataFile.close()
        if len(self.jsonQ):
            with open(self.jsonFile, 'a') as f:
                json.dump(self.jsonQ, f)

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
                while not self.spinCam.dWriterQ.qsize() > 0:
                    time.sleep(0.01)    # Att!! critical value, do NOT change
                qGet = self.spinCam.dWriterQ.get()
                return qGet
        except:
            print('+++ dWriter.readQ(): Error')

    def update(self):

        while self.running:

            elapseTime, frmNmb, contour, centroid, currX, currY = self.readQ()

            currX = round(currX /1000, 3)                         
            currY = round(currY /1000, 3)
                                     
            Cx = round((centroid[0] -self.imgW //2) *self.px2mm + currX, 3)
            Cy = round((centroid[1] -self.imgH //2) *self.px2mm + currY, 3) 
            
            # skeleton
            skeleton = np.zeros(1)
            if contour.shape[0]:
                bx, by, bw, bh = cv2.boundingRect(contour)
                cMtx = np.zeros((bh, bw), np.uint8)
                cv2.drawContours(cMtx, [contour - np.array([bx, by])], -1, 1, thickness = cv2.FILLED)
                cSkl = np.where(skeletonize(cMtx, method = 'lee') != 0)
                skeleton = np.array([cSkl[1], cSkl[0]], np.int32).transpose() + np.array([bx, by])
            
            self.dataFile.write('%8.4f, %6d, %9.3f, %9.3f, %9.3f, %9.3f \n' % (elapseTime, frmNmb, currX, currY, Cx, Cy))
            
            if (time.time() -self.jsonTimer) > 1.0:            
                self.jsonQ[frmNmb] = {'t': elapseTime, 'cam': (currX, currY), 'centroid': (Cx, Cy), 'contour': contour.tolist(), 'skeleton': skeleton.tolist()}
                self.jsonTimer = time.time()
                
            if len(self.jsonQ) > 600:
                with open(self.jsonFile, 'a') as f:
                    json.dump(self.jsonQ, f)
                self.jsonQ = {}
            else:
                time.sleep(0.02)
                
            self.frameRate()
            
