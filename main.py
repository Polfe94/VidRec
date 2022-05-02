import sys
sys.path.append('/home/bigtracker/VidRec')
import time
import numpy as np

import PySpin
from queue import Queue
from threading import Thread
import cv2

import config
# from script import SingleCam

_system = PySpin.System.GetInstance()
_cam_list = _system.GetCameras()

_videoPath = './'
_videoName = 'prova'

def _cam_release():
    for cam in _cam_list:
        del cam
    _cam_list.Clear()
    _system.ReleaseInstance()


class Cam():

    def __init__(self, camNum, Q):

        self.sn = config.CamArray[camNum]
        self.camNum = camNum
        self.Q = Q
        self.mode = config.mode

        self.exposure = config.exposure
        self.gain = config.gain

    def start(self):
        
        self.ptr = _cam_list.GetBySerial(self.sn)
        try:
            self.ptr.Init()
        except:
            print('+++ Cam %s NOT inited' % self.sn)
        
        nodemap = self.ptr.GetNodeMap()

        """ Camera acquisition mode """
        node_acquisition_mode = PySpin.CEnumerationPtr(nodemap.GetNode("AcquisitionMode"))
        node_acquisition_mode_continuous = node_acquisition_mode.GetEntryByName("Continuous")
        acquisition_mode_continuous = node_acquisition_mode_continuous.GetValue()
        node_acquisition_mode.SetIntValue(acquisition_mode_continuous)

        try:
            if self.ptr.PixelFormat.GetAccessMode() == PySpin.RW:
                if self.mode == 'COLOR':
                    self.ptr.PixelFormat.SetValue(PySpin.PixelColorFilter_BayerBG) #COLOR RGB
                else:
                    self.ptr.PixelFormat.SetValue(PySpin.PixelFormat_Mono8)

        except PySpin.SpinnakerException as ex:
            print("Error: %s" % ex)


        """ Buffer Handling """
        nodemap_TLSdevice = self.ptr.GetTLStreamNodeMap()
        ptrHandlingMode = PySpin.CEnumerationPtr(nodemap_TLSdevice.GetNode("StreamBufferHandlingMode"))
        ptrHandlingModeEntry = ptrHandlingMode.GetEntryByName("NewestOnly")
        ptrHandlingMode.SetIntValue(ptrHandlingModeEntry.GetValue())

        """Exposure Time"""
        self.ptr.ExposureAuto.SetValue(PySpin.ExposureAuto_Off)
        self.setExp(self.exposure)

        """Gain"""
        self.ptr.GainAuto.SetValue(PySpin.GainAuto_Off)
        self.setGain(self.gain)
        
        self.ptr.BeginAcquisition()
        
        self.trigger = False
        self.running = True

        t = Thread(target = self.update, args = (), daemon = True)
        t.start()

        return self

    def stop(self):

        self.running = False
        time.sleep(0.5)

        self.ptr.EndAcquisition()

        del self.ptr

    def getFrame(self):
        self.trigger = True

    def update(self):
        
        while self.running:
            while not self.trigger:
                time.sleep(0.005)
            imgPtr = self.ptr.GetNextImage()
            self.Q.put((self.camNum, time.time(), imgPtr))
            self.trigger = False

    def setExp(self, exposure):
    
        try:
            exposure = min(self.ptr.ExposureTime.GetMax(),(exposure*1000))
            self.ptr.ExposureTime.SetValue(exposure)
        except PySpin.SpinnakerException as ex:
            print("Error: %s" % ex.what())

    def setGain(self, gain):

        try:
            gain = min(self.ptr.Gain.GetMax(),gain)
            self.ptr.Gain.SetValue(gain)
        except PySpin.SpinnakerException as ex:
            print("Error: %s" % ex.what())

class FrameWriter():

    def __init__(self, camNum, Q):

        self.sn = config.CamArray[camNum]
        self.camNum = camNum
        self.Q = Q

        self.fps = 15
        self.videoName = '%s/%s%2d.avi' %(_videoPath, _videoName, self.camNum)
        self.outVid = cv2.VideoWriter(self.videoName, cv2.VideoWriter_fourcc('X','V','I','D'), self.fps, config.vidRes, 0)
        # self.outVid = cv2.VideoWriter(self.videoName, 0, self.fps, config.vidRes, 0)

    def start(self):
                
        self.running = True

        t = Thread(target = self.update, args = (), daemon = True)
        t.start()

        return self

    def stop(self):

        self.running = False
        time.sleep(0.5)

        self.outVid.release()

    def update(self):

        while self.running:
            if self.Q.empty():
                time.sleep(0.001)
            else:
                img = self.Q.get()
                self.outVid.write(img)


class MainProcess():

    def __init__(self, nCams):

        self.nCams = nCams
        self.camList = []
        self.masterQ = [Queue(1) for k in range(self.nCams)]
        self.ptrQ = [Queue(100) for k in range(self.nCams)]

    def start(self):

        self.camList = [Cam(k, self.masterQ[k]).start() for k in range(self.nCams)]
        print(len(self.camList))
        self.frameWriterList = [FrameWriter(k, self.ptrQ[k]).start() for k in range(self.nCams)]

    def rec(self, recTime = 900):

        frameNumber = 1
        starttime = time.time()
        self.times = []

        while frameNumber <= recTime:

            [_Cam.getFrame() for _Cam in self.camList]

            while not all([q.qsize() for q in self.masterQ]):
                time.sleep(0.001)

            minTime, maxTime = time.time(), 0
            for Q in self.masterQ:
                camNum, frameTime, ptr = Q.get()
                self.ptrQ[camNum].put(ptr.GetNDArray())
                ptr.Release()
                if frameTime < minTime: minTime = frameTime
                if frameTime > maxTime: maxTime = frameTime
                self.times.append((frameNumber, camNum, frameTime, maxTime -minTime, self.ptrQ[camNum].qsize(), (time.time()-starttime)/frameNumber))
            
            time.sleep(0.019)
            
            frameNumber += 1

        print(1/np.mean([val[5] for val in self.times]))
        print(np.mean([val[4] for val in self.times]))

    def stop(self):

        [_Cam.stop() for _Cam in self.camList]
        [_FrameWriter.stop() for _FrameWriter in self.frameWriterList]
        _cam_release()

def go():

    # _system = PySpin.System.GetInstance()
    # _cam_list = _system.GetCameras()

    m = MainProcess(12)
    m.start()
    m.stop()

    # for cam in _cam_list:
    #     del cam
    # _cam_list.Clear()
    # _system.ReleaseInstance()
