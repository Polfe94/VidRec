#import PyCapture2
import flycapture2 as fc2
import cv2
import numpy as np
from time import sleep
from threading import Thread
import time
from datetime import timedelta
import sys


DEBUG = False

imsY,imsX = 3000,4000#3000,4000

FRMCAM = 2.0
actExp = 150
genGain = 14

vA = 710
vB = 674

TRIGGER = False
RGB = True

#ordreCam = {17215409:2,17215408:9}

ordreCam = { 17179427:4,#0
17215394:6,#1
17215382:9,#2
17215390:0,#3
17215392:3,#4
17215395:5,#5
17215421:8,#6
17215425:1,#7
17215423:7,#8
17179428:2,#9
17215424:11,#10
17215420:10,#11
17215409:12,
17215408:13
}


class FlyCapThreaded:

    maxExp = 225
    minExp = 1
    maxGain = 24
    maxA = 1024
    maxB = 1024
    vA = vA
    vB = vB
    ga = genGain

    BACKSETTED = False

    REALCAM = True
    COLOR = True
    nmock=1
    Tini = time.time()
    font = cv2.FONT_HERSHEY_SIMPLEX
    CamPreview = False

    folderA = ''

    nEvent = 1
    RECEVENT = False
    '''
    ordreSER = {4:17179427,#0
                6:17215394,#1
                9:17215382,#2
                0:17215390,#3
                3:17215392,#4
                5:17215395,#5
                8:17215421,#6
                1:17215425,#7
                7:17215423,#8
                2:17179428,#9
                11:17215424,#10
                10:17215420#11
                }
    '''

    def __init__(self, nCam, triggerTH, qPreview):
        """
        Initialize Dummy Camera
        :param nCam: Asign ID to cameras
        :returns: None
        :raises ValueError: None
        """
        self.n = nCam
        self.exp = actExp
        self.GAIN = genGain
        self.valorA = vA
        self.valorB = vB
        self.stopped = False
        self.c = fc2.Context()
        self.outframe = np.zeros((imsY,imsX),dtype=np.uint8)
        self.bkg = np.zeros((imsY,imsX),dtype=np.uint8)
        self.msk = np.zeros((imsY,imsX),dtype=np.uint8)
        self.ctfr = 0
        self.nWindowPreview = 0

        self.triggerTH = triggerTH
        self.qPreview = qPreview

        print ('nCam=',nCam)
        self.c.connect(*self.c.get_camera_from_index(nCam))

        #Configuracio Properties Camera
        frate = self.c.get_property(fc2.FRAME_RATE)
        frate['auto_manual_mode'] = False
        frate['abs_control'] = True
        frate['on_off']= True
        frate['abs_value']= FRMCAM
        self.c.set_property(**frate)

        ex = self.c.get_property(fc2.AUTO_EXPOSURE)
        ex['auto_manual_mode'] = False
        ex['abs_control'] = False
        ex['on_off']= False
        self.c.set_property(**ex)

        su = self.c.get_property(fc2.SHUTTER)
        su['auto_manual_mode'] = False
        su['abs_control'] = True
        su['abs_value'] = self.exp
        self.c.set_property(**su)

        gain = self.c.get_property(fc2.GAIN)
        gain['auto_manual_mode'] = False
        gain['abs_control'] = True
        gain['abs_value'] = self.GAIN
        self.c.set_property(**gain)

        self.sn =int (self.c.get_camera_info()['serial_number'])
        print (self.sn)

        format7 = self.c.get_format7_configuration()
        format7['pixel_format']=4194304#mode color
        self.c.set_format7_configuration(**format7)

        self.sizeCam = (4000,3000)#(2000,1500)
        self.fps = FRMCAM
        #nomVideo = 'vidTest-'+str(self.sn)+'.avi'
        #print(nomVideo)
        self.outVid = None#cv2.VideoWriter(nomVideo,cv2.VideoWriter_fourcc('X','2','6','4'), fps, self.sizeCam)

        self.nWindowPreview = ordreCam[self.sn]#nCam

        triggerMode = self.c.get_trigger_mode()
        triggerMode['mode'] = 0
        triggerMode['on_off'] = False
        triggerMode['polarity'] = 0
        triggerMode['source'] = 2
        self.c.set_trigger_mode(**triggerMode)

        self.setWB(self.vA, self.vB)
        self.setExp(self.exp)
        self.setGain(self.ga)

        print ('quasi Fi init camera')
        self.c.start_capture()
        print ('Fi init camera')

    def start(self):

        Thread(target=self.update,args=()).start()
        return self

    def newIm(self):

        im = fc2.Image()
        self.c.retrieve_buffer(im)
        ar = np.array(im)
        return cv2.cvtColor(ar,cv2.COLOR_BAYER_BG2BGR)

    def update(self):

        while True:
            if self.stopped:
                return

            self.outframe = self.newIm()

            if self.CamPreview:
                im = self.outframe #REDUIR IM ABANS DE ENVIAR AL QUEUE
                pcktQ= (cv2.resize(im,(240,195)),self.nWindowPreview)
                self.qPreview.put(pcktQ)

            CAPTFLAG = self.triggerTH.empty()

            if CAPTFLAG == False:
                CAPTFLAG = self.triggerTH.get()

                if self.outVid is None and self.RECEVENT:
                    nomVideo = self.folderA+'cam'+str(self.sn)+'_EVT'+str(self.nEvent)+'.avi'
                    print('Nom Video = '+nomVideo)
                    self.outVid = cv2.VideoWriter(nomVideo,cv2.VideoWriter_fourcc('X','V','I','D'), FRMCAM, self.sizeCam)

                if self.RECEVENT is False and self.outVid is not None:

                    self.outVid.release()
                    self.outVid = None
                    self.nEvent +=1
                    print('Video '+str(self.sn)+' Parat')

                if self.outVid is not None and self.RECEVENT is True:
                    #self.outVid.write(cv2.resize(self.outframe,self.sizeCam))
                    self.outVid.write(self.outframe)
                self.ctfr +=1


    def setExp(self,exposure):
        su = self.c.get_property(fc2.SHUTTER)
        su['auto_manual_mode'] = False
        su['abs_control'] = True
        su['abs_value'] = exposure
        self.c.set_property(**su)

    def getExp(self):
        su = self.c.get_property(fc2.SHUTTER)
        su['auto_manual_mode'] = False
        su['abs_control'] = True
        exp = su['abs_value']
        return exp

    def setGain(self,ga):
        gain = self.c.get_property(fc2.GAIN)
        gain['auto_manual_mode'] = False
        gain['abs_control'] = True
        gain['abs_value'] = ga
        self.c.set_property(**gain)

    def getGain(self):
        gain = self.c.get_property(fc2.GAIN)
        ga = gain['abs_value']
        return ga

    def setWB (self,vA,vB):
        global valorA,valorB
        valorA = vA
        valorB = vB
        if RGB:
            wb = self.c.get_property(fc2.WHITE_BALANCE)
            wb['value_a'] = valorA
            wb['value_b'] = valorB
            self.c.set_property(**wb)

    def getWB(self):
        wb = self.c.get_property(fc2.WHITE_BALANCE)
        valorA = wb['value_a']
        valorB = wb['value_b']
        return (valorA,valorB)

    def read(self):
        return self.outframe

    def stop(self):
        self.stopped = True
        print ('stop cam=',self.n)


    def mockIM(self):

        font = cv2.FONT_HERSHEY_SIMPLEX
        w,h = 320,240#Una mida superior triga molt a crear el array sense CUDA
        im = np.ones((h,w,3),dtype=np.uint8)
        im = im*200
        cv2.putText(im,str(self.nmock),(int(w//3),int(h//2)), font,1,(128,0,255),5,cv2.LINE_AA)
        self.nmock +=1
        if self.nmock>99999:self.nmock=0
        return im
