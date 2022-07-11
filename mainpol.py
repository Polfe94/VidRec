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

    def __init__(self, camNum, Q1, Q2, Q3):

        self.sn = config.CamArray[camNum]
        self.camNum = camNum
        self.Q1, self.Q2, self.Q3 = Q1, Q2, Q3
        self.mode = config.mode

        self.exposure = config.exposure
        self.gain = config.gain

        self.frameTimes = []

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

    def start(self):
        
        self.ptr = _cam_list.GetBySerial(self.sn)
        try:
            self.ptr.Init()
        except:
            print('+++ Cam %s NOT inited' % self.sn)
        
        # nodemap = self.ptr.GetNodeMap()

        # """ Camera acquisition mode """
        # node_acquisition_mode = PySpin.CEnumerationPtr(nodemap.GetNode("AcquisitionMode"))
        # node_acquisition_mode_continuous = node_acquisition_mode.GetEntryByName("Continuous")
        # acquisition_mode_continuous = node_acquisition_mode_continuous.GetValue()
        # node_acquisition_mode.SetIntValue(acquisition_mode_continuous)

        # try:
        #     if self.ptr.PixelFormat.GetAccessMode() == PySpin.RW:
        #         if self.mode == 'COLOR':
        #             self.ptr.PixelFormat.SetValue(PySpin.PixelColorFilter_BayerBG) #COLOR RGB
        #         else:
        #             self.ptr.PixelFormat.SetValue(PySpin.PixelFormat_Mono8)

        # except PySpin.SpinnakerException as ex:
        #     print("Error: %s" % ex)


        # """ Buffer Handling """
        # nodemap_TLSdevice = self.ptr.GetTLStreamNodeMap()
        # ptrHandlingMode = PySpin.CEnumerationPtr(nodemap_TLSdevice.GetNode("StreamBufferHandlingMode"))
        # ptrHandlingModeEntry = ptrHandlingMode.GetEntryByName("NewestOnly")
        # ptrHandlingMode.SetIntValue(ptrHandlingModeEntry.GetValue())

        # """Exposure Time"""
        # self.ptr.ExposureAuto.SetValue(PySpin.ExposureAuto_Off)
        # self.setExp(self.exposure)

        # """Gain"""
        # self.ptr.GainAuto.SetValue(PySpin.GainAuto_Off)
        # self.setGain(self.gain)
        
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
                time.sleep(0.001)
            
            try:
                imgPtr = self.ptr.GetNextImage()
                self.frameTimes.append(time.perf_counter())
                frame = imgPtr.GetNDArray()
                imgPtr.Release()
                self.Q1.put(frame[:1000, :])
                self.Q2.put(frame[1000:2000:, :])
                self.Q3.put(frame[2000:, :])
                self.trigger = False
            
            except:
                time.sleep(0.001)

class Vid():

    def __init__(self, vidNum, Q):

        self.vidNum = vidNum
        self.camNum = self.vidNum //3
        self.sn = config.CamArray[self.camNum]
        self.vidSize = (config.vidRes[0], int(config.vidRes[1] /3))

        self.Q = Q

        self.fps = 15
        self.videoName = '%s/%s_%s%s.avi' %(_videoPath, _videoName, str(self.camNum).zfill(2), str(self.vidNum).zfill(2))
        self.outVid = cv2.VideoWriter(self.videoName, cv2.VideoWriter_fourcc('X','V','I','D'), self.fps, self.vidSize, 0)

    def start(self):
                
        self.trigger = False
        self.running = True

        t = Thread(target = self.update, args = (), daemon = True)
        t.start()

        return self

    def stop(self):

        self.running = False
        time.sleep(0.5)

        self.outVid.release()

    def getFrame(self):
        self.trigger = True

    def update(self):

        while self.running:
            # if not self.trigger:
            if self.Q.empty():
                time.sleep(0.001)
            else:
                img = self.Q.get()
                self.outVid.write(img)
                # self.trigger = False


class MainProcess():

    def __init__(self, nCams = 12):

        self.nCams, self.nVids = nCams, nCams *3
        self.camList, self.vidList = [], []

        self.vidsQ = [Queue(20) for k in range(self.nVids)]

    def start(self):

        self.camList = [Cam(k, self.vidsQ[3 *k], self.vidsQ[3 *k +1], self.vidsQ[3 *k +2]).start() for k in range(self.nCams)]
        self.vidList = [Vid(v, self.vidsQ[v]).start() for v  in range(self.nVids)]

    def rec(self, recTime = 900):

        time.sleep(5)

        frameNumber = 0
        self.startTime = time.perf_counter()
        currTime = time.perf_counter() - self.startTime
        while currTime <= recTime:

            [_Cam.getFrame() for _Cam in self.camList]
            print('Frame = %s' % frameNumber)
            while any([_Cam.trigger for _Cam in self.camList]):
                time.sleep(0.001)

            time.sleep(0.001)
            
            frameNumber += 1
            currTime = time.perf_counter() - self.startTime
            
        print('Finished recording, mean FPS = %s' % str(frameNumber / recTime))
        frameTimes = np.array([_Cam.frameTimes for _Cam in self.camList])
        print(frameTimes.shape[1] /recTime)
        print(np.mean(np.max(frameTimes, axis = 0) -np.min(frameTimes, axis = 0)))

    def stop(self):

        [_Cam.stop() for _Cam in self.camList]
        [_Vid.stop() for _Vid in self.vidList]
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
