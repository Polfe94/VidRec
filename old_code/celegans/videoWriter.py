# -*- coding: utf-8 -*-

import cv2
import numpy as np
from math import sqrt

import segno
import time
import io

from threading import Thread
from queue import Queue
from datetime import timedelta

class VideoWriterQR:

    def __init__(self, projectConfig, spinCam):

        # cam image size (pixels)        
        self.camImgW = int(projectConfig.get('CAM', '_imgW'))
        self.camImgH = int(projectConfig.get('CAM', '_imgH'))

        # unit conversion
        _fieldX = int(projectConfig.get('TRACKER','fieldX'))
        self.microns2Px = self.camImgW /_fieldX
        self.px2microns = _fieldX /self.camImgW

        # video image size (pixels)
        self.vidImgW = int(projectConfig.get('VIDEO', '_vImgW'))
        self.vidImgH = int(projectConfig.get('VIDEO', '_vImgH'))
        self.fps = int(projectConfig.get('VIDEO', '_vfps'))
                
        # video save path
        self.aviPth = projectConfig.get('DATA', '_avi')
        
        self.spinCam = spinCam

        self.fRate = 0
        self.fRateCounter = 0
        self.fRateTimer = time.time()
                
        self.tracking = False
        self.running = False

    def start(self, tracker_running):

        fName = '%s/run_%s_%s.avi' % (self.aviPth, time.strftime("%y%m%d"), time.strftime("%H%M"))
        self.outVid = cv2.VideoWriter(fName, cv2.VideoWriter_fourcc('X','V','I','D'), self.fps, (self.vidImgW, self.vidImgH))
        print('+++ start %s' % fName)

        self.fRate = 0
        self.fRateCounter = 0
        self.fRateTimer = time.time()

        self.tracking = tracker_running
        self.running = True

        t = Thread(target = self.update, args=())
        t.daemon =True
        t.start()

        return self

    def stop(self):

        self.fRate = 0
        self.running = False
        time.sleep(0.01)
        self.outVid.release()

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
                while not self.spinCam.vWriterQ.qsize() > 0:
                    time.sleep(0.01)    # Att!! critical value, do NOT change
                qGet = self.spinCam.vWriterQ.get()
                return qGet
        except:
            print('+++ vWriter.readQ(): Error')

    def update(self):

        while self.running:
            
            elapseTime, frm, frmNmb, contour, centroid, currX, currY = self.readQ()
            
            img = self.stabImage(frm, centroid)

            if self.tracking:
                
                centroidX = round((centroid[0] -self.camImgW //2) *self.px2microns + currX, 0)
                centroidY = round((centroid[1] -self.camImgH //2) *self.px2microns + currY, 0)
                qrImg = self.getQR(frmNmb, centroidX, centroidY, elapseTime)            
                img[0:qrImg.shape[0], 0:qrImg.shape[1], :] = qrImg
            
            self.outVid.write(img)
            
            self.frameRate()
            time.sleep(0.02)

    def stabImage(self, frm, centroid):

        minX, minY = centroid[0] -self.vidImgW //2, centroid[1] -self.vidImgH //2
        maxX, maxY = centroid[0] +self.vidImgW //2, centroid[1] +self.vidImgH //2
        
        if not (minX > 0 and minY > 0 and maxX < self.camImgW and maxY < self.camImgH):
            minX, minY = self.vidImgW //2 -450, self.vidImgH //2 -300
            maxX, maxY = self.vidImgW //2 +450, self.vidImgH //2 +300
            
        return cv2.flip(cv2.UMat(frm, [minY, maxY], [minX, maxX]).get().astype(np.uint8), 0)
        
        
    def getQR(self, frmNmb, cX, cY, elapseTime):

        strQR  = 'X'  +str(cX).zfill(8)
        strQR += ',Y' +str(cY).zfill(8)
        strQR += ',F' +str(frmNmb).zfill(8)
        strQR += ',T' +(str(timedelta(seconds = elapseTime)).split(".")[0]).zfill(8)
        
        qrRaw = segno.make_qr(strQR)
        buff = io.StringIO()
        qrRaw.save(buff, kind = 'txt')
        strqr = buff.getvalue().replace('\n', '')
        npqr = np.fromiter(strqr, dtype = np.uint)
        npqr = 255 - (npqr *255)
        lqr = npqr.shape[0]
        a = int(sqrt(lqr))
        npqr = npqr.reshape((a, a))
        npqrBIG = np.repeat(npqr, 2, axis = 0)
        npqrBIG = np.repeat(npqrBIG, 2, axis = 1).astype(np.uint8)
        #ret = np.empty((a*2,a*2, 3), dtype=np.uint8)
        #ret[:, :, 0] = ret[:, :, 1] =  ret[:, :, 2] = npqrBIG
        ret = np.dstack([npqrBIG, npqrBIG, npqrBIG])
        return ret
    
        