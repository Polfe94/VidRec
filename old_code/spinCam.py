import PySpin
import cv2
import numpy as np
from math import exp, hypot

from scipy.signal import savgol_filter
#from skimage.morphology import medial_axis, skeletonize

from queue import Queue
from threading import Thread
import time

import configparser

""" instantiate PySpin.System """

try:
    _spinSystem = PySpin.System.GetInstance()
    _spinCamList = _spinSystem.GetCameras()
except:
    print('+++ PySpin.System.GetInstance() error !!!')

def instanceRelease():
    # Att.!! any created spinCam object must be removed before releasing _spinSystem, e.g.:
    # _spinCam = SpinCam()
    # del _spinCam.vStream # holds a pointer to the camera
    # del _spinCam
    _spinCamList.Clear()
    _spinSystem.ReleaseInstance()

# list of SpinCam nodes
# for name in sorted([node.GetName() for node in spinCam.GetNodeMap().GetNodes()]): print(name)

_camSerialNumber = '19269798'

""" instantiate video source """

_chkVid = '/home/tracker/leov/chkavi/vid_20_06_22_15-14-53.avi'
_realCam = True

_MaxEvents = 4
_bkgUpdate = 30
_k1 = 3
_k2 = 5
_smooth = 21

# circle to square factor (contour detection)
_c2sq = np.cos(np.pi /4)    # inner square
_c2sq = 1.0                 # outer square

def _bBoxOvl(bBox1, bBox2):
    x1, y1, w, h = bBox1
    x2, y2 = x1 +w, y1 +h
    Xbox1, Ybox1 = [x1, x2], [y1, y2]
    x3, y3, w, h = bBox2
    x4, y4 = x3 +w, y3 +h
    Xbox2, Ybox2 = [x3, x4], [y3, y4]
    X, Y = [x1, x2, x3, x4], [y1, y2, y3, y4]
    X.sort()
    Y.sort()
    # non-overlapping condition
    if X[: 2] == Xbox1 or X[: 2] == Xbox2 or Y[: 2] == Ybox1 or Y[: 2] == Ybox2:
        ovl = 0
    else:
        ovl = (X[2] -X[1]) *(Y[2] -Y[1])
    return ovl


class SpinCam:

    def __init__(self, projectConfig, camSerialNumber = _camSerialNumber, queueSize = 12):
        
        # LIMITS AREA PLATINA (microns)
        self.xMax = int(projectConfig.get('TRACKER','_xMax'))
        self.xMin = int(projectConfig.get('TRACKER','_xMin'))
        self.yMax = int(projectConfig.get('TRACKER','_yMax'))
        self.yMin = int(projectConfig.get('TRACKER','_yMin'))

        # image size        
        self.imgW = int(projectConfig.get('CAM', '_imgW'))
        self.imgH = int(projectConfig.get('CAM', '_imgH'))
        
        self.imgCntrX = self.imgW //2
        self.imgCntrY = self.imgH //2

        # unit conversion
        _fieldX = int(projectConfig.get('TRACKER','fieldX'))
        self.microns2Px = self.imgW /_fieldX
        self.px2microns = _fieldX /self.imgW
        
        # AREA DETECCIO MOVIMENT (px)
        # circle max./min radius (microns)
        _cMax = int(projectConfig.get('TRACKER','_cMax'))
        _cMin = int(projectConfig.get('TRACKER','_cMin'))
        self.maxC = int(_cMax *self.microns2Px)
        self.minC = int(_cMin *self.microns2Px)
        
        # contour detection threshold value        
        self.thrVal = int(projectConfig.get('TRACKER','_thrVal'))
        self.bkgUpd = _bkgUpdate

        self.frmNmb = 0
        self.bkgCount = 0

        self.fRate = 0
        self.fRateCounter = 0
        self.fRateTimer = time.time()

        self.tracking = False
        self.showContour = False
        self.running = False
        
        self.startTime = time.time()

        # initialize queues
        self.mainQ = Queue(maxsize = queueSize)
        self.trackerQ = Queue(maxsize = queueSize)
        self.dWriterQ = Queue(maxsize = 2 *queueSize)
        self.vWriterQ = Queue(maxsize = 4 *queueSize)
        
        # cam position queue (updated by _tracker)
        self.positionQ = Queue(maxsize = 2)
        self.currX, self.currY, self.currZ = (self.xMax -self.xMin) //2, (self.yMax -self.yMin) //2, 0
        
#         # since this version uses UMat to store the images to we need to initialize them beforehand
#         self.queueSize = queueSize
#         self.idx = 0
#         [self.Q.put((cv2.UMat(_imgH, _imgW, cv2.CV_8UC3), [], 0)) for i in range(queueSize)]

        self.kernelCLOSE = cv2.UMat(np.ones((9, 9), np.uint8))   #WARNING! CHANGES ON THIS KERNEL CAN DELETE ANY BLOB ON THRESHOLDED IMAGE
        self.kernelOPEN = cv2.UMat(np.ones((5, 5), np.uint8))    #WARNING! CHANGES ON THIS KERNEL CAN DELETE ANY BLOB ON THRESHOLDED IMAGE

        if _realCam:
            self.initReal(camSerialNumber)
        else:
            self.sn = 8888

        print("Serial Number = ",self.sn)

    def initReal(self, camSerialNumber):

        self.vStream = _spinCamList.GetBySerial(camSerialNumber)

        self.vStream.Init()

        nodemap = self.vStream.GetNodeMap()

        node_acquisition_mode = PySpin.CEnumerationPtr(nodemap.GetNode("AcquisitionMode"))
        node_acquisition_mode_continuous = node_acquisition_mode.GetEntryByName("Continuous")
        acquisition_mode_continuous = node_acquisition_mode_continuous.GetValue()
        node_acquisition_mode.SetIntValue(acquisition_mode_continuous)

        # set RGB mode
        try:
            if self.vStream.PixelFormat.GetAccessMode() == PySpin.RW:
                self.vStream.PixelFormat.SetValue(PySpin.PixelColorFilter_BayerBG) #COLOR RGB
                print("Pixel format set to %s..." % self.vStream.PixelFormat.GetCurrentEntry().GetSymbolic())
        except PySpin.SpinnakerException as ex:
            print("Error: %s" % ex)

        """ Buffer Handling """
        nodemap_TLSdevice = self.vStream.GetTLStreamNodeMap()
        ptrHandlingMode = PySpin.CEnumerationPtr(nodemap_TLSdevice.GetNode("StreamBufferHandlingMode"))
        ptrHandlingModeEntry = ptrHandlingMode.GetEntryByName("NewestOnly")
        ptrHandlingMode.SetIntValue(ptrHandlingModeEntry.GetValue())

        """Configuracio QuickSpin"""

        """Exposure Time"""
        if self.vStream.ExposureAuto is None or self.vStream.ExposureAuto.GetAccessMode() != PySpin.RW:
            print("Unable to disable automatic exposure. Aborting...")
            return False
        else:
            self.vStream.ExposureAuto.SetValue(PySpin.ExposureAuto_Off)
            # BalanceWhiteAuto_Continuos is default setting
            #self.vStream.BalanceWhiteAuto.SetValue(PySpin.BalanceWhiteAuto_Continuous, True)

        """Gain"""
        self.vStream.GainAuto.SetValue(PySpin.GainAuto_Off)

        # set BalanceWhiteAuto to False
        self.vStream.BalanceWhiteAuto.SetValue(PySpin.BalanceWhiteAuto_Off, False)
        # set BalanceWhiteAuto manually
        vA = 2.2799999713897705
        vB = 1.1799999475479126
        node_BR = PySpin.CFloatPtr(nodemap.GetNode("BalanceRatio"))
        self.vStream.BalanceRatioSelector.SetValue(PySpin.BalanceRatioSelector_Blue)
        node_BR.SetValue(vB, False)
        self.vStream.BalanceRatioSelector.SetValue(PySpin.BalanceRatioSelector_Red)
        node_BR.SetValue(vA, False)

        """Configuracio NodeMap"""
        """ GAMMA """
        # if (False):
        #     node_GammaEnabled = PySpin.CBooleanPtr(self.nodemap.GetNode("GammaEnabled"))
        #     node_GammaEnabled.SetValue(False)

        #self.vStream.Gamma.SetValue(1.0)

        """ FRAME RATE """

        if (True):  #True per camera Blanes
            node_frmrt = PySpin.CBooleanPtr(nodemap.GetNode("AcquisitionFrameRateEnabled"))
            node_frmrt.SetValue(False)

        '''
        self.vStream.AcquisitionFrameRate.SetValue(30)
        print(self.vStream.AcquisitionFrameRate.GetValue())
        '''

        self.sn = self.vStream.DeviceSerialNumber.GetValue()

    def __del__(self):
        pass

    def device_info(self):

        try:
            nodemap = self.vStream.GetTLDeviceNodeMap()
            node_device_information = PySpin.CCategoryPtr(nodemap.GetNode("DeviceInformation"))

            print("\n *** DEVICE INFORMATION *** ")

            if PySpin.IsAvailable(node_device_information) and PySpin.IsReadable(node_device_information):
                features = node_device_information.GetFeatures()
                for feature in features:
                    node_feature = PySpin.CValuePtr(feature)
                    print("%s: %s" % (node_feature.GetName(),
                                      node_feature.ToString() if PySpin.IsReadable(node_feature) else "Node not readable"))
            else:
                print("+++ Device control information not available.")

        except PySpin.SpinnakerException as ex:
            print("Error: %s" % ex.message)


    def frmGet(self):

        if _realCam:

            while True:
                img = self.vStream.GetNextImage()
                if not img.IsIncomplete(): break
            # send image to GPU memory
            frm = cv2.UMat(img.Convert(PySpin.PixelFormat_BGR8, PySpin.NEAREST_NEIGHBOR).GetNDArray())
            frm = cv2.flip(frm, 1)

        else:

            ok, frm = self.cap.read()
            if not ok:
                print('+++ check video end ')
                self.stop()
            else:
                # send image to GPU memory
                frm = cv2.flip(cv2.UMat(frm), -1)

        self.frmNmb += 1

        return frm


    def bkgSet(self, frm):

        self.bkg = cv2.cvtColor(frm, cv2.COLOR_BGR2GRAY)
        self.bkgCount = 1


    def start(self):

        self.frmNmb = 0
        self.bkgCount = 0
        
        self.fRate = 0
        self.fRateCounter = 0
        self.fRateTimer = time.time()

        self.tracking = False
        self.running = True # Att.! set True before launching thread
        self.startTime = time.time()
        
        if _realCam:
            self.vStream.BeginAcquisition()
        else:
            self.cap = cv2.VideoCapture(_chkVid)
            self.capWidth = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            self.capHeight = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            self.capLength = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))

        # start a thread to read frames from the file video stream
        t = Thread(target = self.update, args = ())
        t.daemon = True
        t.start()

        return self

    def stop(self):

        self.tracking = False
        self.running = False
        time.sleep(0.1)

        if _realCam:
            self.vStream.EndAcquisition()
        else:
            self.cap.release()

    def frameRate(self):
        
        elapseTime = time.time() -self.fRateTimer
        self.fRateCounter += 1
        if elapseTime > 2:
            self.fRate = round(self.fRateCounter /elapseTime, 2)
            self.fRateCounter = 0
            self.fRateTimer = time.time()


    def update(self):

        while self.running:
                    
            frm = self.frmGet()
            elapseTime = time.time() -self.startTime
            
            if self.positionQ.qsize() > 0:
                self.currX, self.currY, self.currZ = self.positionQ.get()
                self.bkgSet(frm)
            
            blobContour, blobCenter = self.getBlob(frm)            
            contour, centroid = self.getContour(frm)
            
            if self.trackerQ.full(): self.trackerQ.get()
            self.trackerQ.put(blobCenter)

            if self.mainQ.full(): self.mainQ.get()
            self.mainQ.put((elapseTime, frm, blobContour, contour, centroid, self.currX, self.currY, self.currZ))
            
            if self.vWriterQ.full(): self.vWriterQ.get()
            self.vWriterQ.put((elapseTime, frm, self.frmNmb, contour, centroid, self.currX, self.currY))
            
            if self.dWriterQ.full(): self.dWriterQ.get()
            self.dWriterQ.put((elapseTime, self.frmNmb, contour, centroid, self.currX, self.currY))
            
            self.frameRate()
        
    def getContour(self, frm):

        contour = np.array([], dtype = np.int32)
        centroid = (self.imgCntrX, self.imgCntrY)
        
        if not self.tracking and not self.showContour:
            return (contour, centroid)

        # I keep it here because self.maxC can change on the fly
        cropSize = int(self.maxC *_c2sq)
        minX, maxX = self.imgCntrX -cropSize, self.imgCntrX +cropSize   # top-left
        minY, maxY = self.imgCntrY -cropSize, self.imgCntrY +cropSize   # bottom-right
        gry = cv2.cvtColor(cv2.UMat(frm, [minY, maxY], [minX, maxX]), cv2.COLOR_BGR2GRAY)

        dff1 = cv2.threshold(gry, self.thrVal, 255, cv2.THRESH_BINARY)[1]
        contours1 = cv2.findContours(dff1, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)[0]
        
        contours2 = []
        cMain = []

        if len(contours1):
                        
            # filter by blob weight = Area *softmax(dist2ImgCenter)
            # works better than using dist2previousCentroid because
            # we might be following the wrong one
            
            blobArea = []
            blobDist = []
            for c in contours1:
                blobArea.append(cv2.contourArea(c))
                M = cv2.moments(c)
                if M["m00"]:
                    contourCentroid = (int(M["m10"] /M["m00"]), int(M["m01"] /M["m00"]))
                    sqDist = (contourCentroid[0] -cropSize)**2 + (contourCentroid[1] -cropSize)**2
                    blobDist.append(exp(-sqDist /20000))    # bandwidth kernel in the order of self.maxC (\sigma**2 = 100**2) 
                else:
                    blobDist.append(0)
             
            blobArea  = np.array(blobArea)
            if np.sum(blobArea): blobArea /= np.sum(blobArea)
            blobDist  = np.array(blobDist)
            if np.sum(blobDist): blobDist /= np.sum(blobDist)
             
            blobWeight = np.multiply(blobArea, blobDist)
            maxC = np.argmax(blobWeight)

            # draw filled blob over black image
            msk = np.zeros((2 *cropSize, 2 *cropSize), np.uint8)
            cv2.drawContours(msk, contours1, maxC, 255, -1)

            # fill gaps in the new blob (do NOT remove !!)
            msk = cv2.dilate(msk, self.kernelOPEN)
            msk = cv2.erode(msk, self.kernelOPEN)

            # find new contour
            contours2 = cv2.findContours(msk, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)[0]
            
        if len(contours2):
            
            # assume there will be only one contour, but check anyway
            maxC = 0
            if len(contours2) > 1:
                maxC = np.argmax(np.array([cv2.contourArea(c) for c in contours2]))

            # smooth new contour
            cX = savgol_filter([p[0][0] for p in contours2[maxC]], _smooth, 3, mode = 'mirror')
            cY = savgol_filter([p[0][1] for p in contours2[maxC]], _smooth, 3, mode = 'mirror')

            # get main contour
            # compute offSet relative to whole image (keep it here !!) 
            offX, offY = self.imgCntrX -cropSize, self.imgCntrY -cropSize
            cMain = [[cx +offX, cy +offY] for cx, cy in zip(cX, cY)]

        if len(cMain):

            # contour
            contour = np.array(cMain, dtype = np.int32)
            
            # centroid
            moments = cv2.moments(contour)
            if moments["m00"]:
                centroid = (int(moments["m10"] /moments["m00"]), int(moments["m01"] /moments["m00"]))

#         contours3 = []
#         if len(contours1):
#             xyOff = np.array([self.imgCntrX -cropSize, self.imgCntrY -cropSize])
#             for c in np.argsort(blobWeight)[-3: ]:
#                 contours3.append(contours1[c] +xyOff)
                                                
        return (contour, centroid)


    def getBlob(self, frm):

        mainBlobContour = np.array([], dtype = np.int32)
        mainBlobCenter = []
        
        if not self.tracking:
            return (mainBlobContour, mainBlobCenter)
        
        if not (self.bkgCount %self.bkgUpd): self.bkgSet(frm)

        else:
            
            self.bkgCount += 1
    
            msk = cv2.UMat(self.imgH, self.imgW, cv2.CV_8UC1)
            cv2.circle(msk, (self.imgCntrX, self.imgCntrY), self.maxC, (255, 255, 255), -1)
    
            dff = cv2.subtract(cv2.cvtColor(frm, cv2.COLOR_BGR2GRAY), self.bkg)
            dff = cv2.threshold(cv2.bitwise_and(dff, msk), 8, 255, cv2.THRESH_BINARY)[1]
            dff = cv2.morphologyEx(dff, cv2.MORPH_OPEN, self.kernelOPEN)       #ELIMINA SOROLL PETIT
            dff = cv2.morphologyEx(dff, cv2.MORPH_CLOSE, self.kernelCLOSE)     #TANCA EL BLOB
    
            nBlobs = 0
    
            blobContours = cv2.findContours(dff, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)[0]
            if len(blobContours): nBlobs = len(blobContours)
    
            if nBlobs > _MaxEvents: self.bkgCount = 0
    
            elif nBlobs > 0:
    
                Moments = [cv2.moments(bContour) for bContour in blobContours]
                Centers = [(int(m["m10"] / m["m00"]), int(m["m01"] / m["m00"])) for m in Moments]
    
                blobDistance = np.array([hypot((center[0] -self.imgCntrX), (center[1] -self.imgCntrY)) for center in Centers])
    
                blobAreas = np.array([cv2.contourArea(c) for c in blobContours])
                blobAreas /= np.sum(blobAreas)
    
    #                     blobWeights = blobAreas * 1 /(blobDistance /np.sum(blobDistance))
                if np.sum(blobDistance):
                    blobWeights = blobAreas *np.exp(- 1/2 * blobDistance /np.sum(blobDistance))
                else:
                    blobWeights = [1 for blob in blobDistance]
    
                mainBlob = np.argmax(blobWeights)
                blobBBox = cv2.minAreaRect(blobContours[mainBlob])[1]
                blobSize = max(blobBBox)
                blobDist = blobDistance[mainBlob]
    
                mainBlobContour = blobContours[mainBlob]
                if(blobSize > self.minC and blobDist < self.maxC):
                    mainBlobCenter = Centers[mainBlob]

        return (mainBlobContour, mainBlobCenter)


    def setExp(self, exposure):
        if _realCam:
            try:
                exposure = min(self.vStream.ExposureTime.GetMax(),(exposure *1000))
                if exposure < 20:
                    exposure = 20
                self.vStream.ExposureTime.SetValue(exposure)
            except PySpin.SpinnakerException as ex:
                print("Error: %s" % ex.what())


    def setGain(self,gain):
        if _realCam:
            try:
                gain = min(self.vStream.Gain.GetMax(),gain)
                self.vStream.Gain.SetValue(gain)
            except PySpin.SpinnakerException as ex:
                print("Error: %s" % ex.what())


    def setGamma(self,g):
        pass
#       # ims249 no te gamma !!!
#         if(self.REALCAM):
#             try:
#                 self.vStream.Gamma.SetValue(g)
#             except PySpin.SpinnakerException as ex:
#                 print("Error: %s" % ex)


def go(queueSize = 24, realCam = True):

    global _realCam, _thrVal

    _realCam = realCam

    _spinCam = SpinCam(queueSize = queueSize)
    _spinCam.start()

    cv2.namedWindow('viewer', cv2.WINDOW_NORMAL)
    cv2.resizeWindow('viewer', 800, 600)

    startTime = time.time()
    while _spinCam.running:

        frm, frmNmb, contour, centroid, skeleton, blobContour, blobCenter = _spinCam.readQ()
        cv2.imshow('viewer', frm)

        wky = cv2.waitKey(1)
        if wky == 32:
            _spinCam.stop()
            break
        elif wky == 109:
            _spinCam.thrVal += 1	# m
        elif wky == 110:
            _spinCam.thrVal -= 1	# n

        print("+++ frame: %8d, frameRate: %6.2f frms/sec., _thrVal %3d" % (frmNmb, frmNmb /(time.time() -startTime), _spinCam.thrVal), end = '\r')

    cv2.destroyWindow('viewer')
    del _spinCam
