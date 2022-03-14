# import os
import PySpin
# import sys

import cv2
import numpy as np

from queue import Queue
from threading import Thread
import time

import config

system = PySpin.System.GetInstance()
cam_list = system.GetCameras()

''' THREADS (vPol)'''

class SingleCam:

    def __init__(self, serial_number, exposure = 40, gain = 1, mode = 'COLOR'):

        self.sn = serial_number
        self.exposure = exposure
        self.gain = gain

        self.video_name = config.vidName + '_' + str(self.sn)
        self.fps = 15 ## ??
        # self.fps_timer = 0
        # self.fps_counter = 0
        self.is_recording = False

        if mode == 'BW' or mode == 'BLACK_AND_WHITE':
            self.getImg = self.bwImg
        else:
            self.getImg = self.colImg

    def init_cam(self):

        self.cam = cam_list.GetBySerial(self.sn)
        self.cam.Init()

        nodemap = self.cam.GetNodeMap()

        node_acquisition_mode = PySpin.CEnumerationPtr(nodemap.GetNode("AcquisitionMode"))
        node_acquisition_mode_continuous = node_acquisition_mode.GetEntryByName("Continuous")
        acquisition_mode_continuous = node_acquisition_mode_continuous.GetValue()
        node_acquisition_mode.SetIntValue(acquisition_mode_continuous)

        # set RGB mode
        try:
            if self.cam.PixelFormat.GetAccessMode() == PySpin.RW:
                self.cam.PixelFormat.SetValue(PySpin.PixelColorFilter_BayerBG) #COLOR RGB
                print("Pixel format set to %s..." % self.cam.PixelFormat.GetCurrentEntry().GetSymbolic())
        except PySpin.SpinnakerException as ex:
            print("Error: %s" % ex)

        """ Buffer Handling """
        nodemap_TLSdevice = self.cam.GetTLStreamNodeMap()
        ptrHandlingMode = PySpin.CEnumerationPtr(nodemap_TLSdevice.GetNode("StreamBufferHandlingMode"))
        ptrHandlingModeEntry = ptrHandlingMode.GetEntryByName("NewestOnly")
        ptrHandlingMode.SetIntValue(ptrHandlingModeEntry.GetValue())

        """Configuracio QuickSpin"""

        """Exposure Time"""
        if self.cam.ExposureAuto is None or self.cam.ExposureAuto.GetAccessMode() != PySpin.RW:
            print("Unable to disable automatic exposure. Aborting...")
            return False
        else:
            self.cam.ExposureAuto.SetValue(PySpin.ExposureAuto_Off)
            # BalanceWhiteAuto_Continuos is default setting
            #self.cam.BalanceWhiteAuto.SetValue(PySpin.BalanceWhiteAuto_Continuous, True)

        """Gain"""
        self.cam.GainAuto.SetValue(PySpin.GainAuto_Off)

        '''
        # MANUAL WHITE BALANCE
        self.cam.BalanceWhiteAuto.SetValue(PySpin.BalanceWhiteAuto_Off, False)
        node_BR = PySpin.CFloatPtr(nodemap.GetNode("BalanceRatio"))
        self.cam.BalanceRatioSelector.SetValue(PySpin.BalanceRatioSelector_Blue)
        node_BR.SetValue(config._balanceBlue, False)
        self.cam.BalanceRatioSelector.SetValue(PySpin.BalanceRatioSelector_Red)
        node_BR.SetValue(config._balanceRed, False)
        '''

        self.exposure()
        self.gain()

    def bwImg(self):
        img = self.cam.GetNextImage()
        img.Convert(PySpin.PixelFormat_Mono8)

    def colImg(self):
        self.cam.GetNextImage()

    def update(self):

        while self.is_recording:

            img = self.imgGet()
            self.outVid.write(img)

    def start(self):
    
        self.is_recording = True
        self.cam.BeginAcquisition()

        # self.is_recording = True
        self.outVid = cv2.VideoWriter(self.vidPath + self.vidName,
        cv2.VideoWriter_fourcc('X','V','I','D'), self.fps, config.vidRes)

        t = Thread(target = self.update, args = ())
        t.daemon = True
        t.start()

        return self

    def stop(self):

        self.is_recording = False
        self.cam.EndAcquisition()
        self.outVid.release()

    def device_info(self):
    
        try:
            nodemap = self.cam.GetTLDeviceNodeMap()
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

    
    def setExp(self):

        try:
            exposure = min(self.cam.ExposureTime.GetMax(),(self.exposure *1000))
            if exposure < 20:
                exposure = 20
            self.cam.ExposureTime.SetValue(exposure)
        except PySpin.SpinnakerException as ex:
            print("Error: %s" % ex.what())


    def setGain(self):

        try:
            gain = min(self.cam.Gain.GetMax(),self.gain)
            self.cam.Gain.SetValue(gain)
        except PySpin.SpinnakerException as ex:
            print("Error: %s" % ex.what())


class MultiCam:

    def __init__(self, cam_list, time, recording_method = 'continuous'):

        self.cam_list = cam_list
        self.q = []
        for c in cam_list:
            self.q.append(Queue(1))
        self.vidPath = config.vidPath
        self.tREC = time
        self.method = recording_method
            
        # if recording_method == 'scheduled':
        #         self.record = self.scheduled_recording
        # else:
        #     self.record = self.continuous_recording

    def REC(self):

        if self.method == 'scheduled':
            self.scheduled_recording()
        
        else:
            self.continuous_recording()

        for c in cam_list:
            c.stop()


    def continuous_recording(self):
        t0 = time.time()
        while(time.time() - t0 <= self.tREC):
            for c in self.cam_list:
                c.put(True)


    def scheduled_recording(self):
        tf = self.tREC[0]
        freq = self.tREC[1]
        next_shot = time.time()
        t0 = time.time()

        while(time.time() - t0 <= tf):
            if time.time() >= next_shot:
                for c in self.cam_list:
                    c.put(True)
                    c.put(False)
                next_shot += freq


def SaveIMG(self,evt):
        
        for i in range(len(AcoCAMArray.cameras)):
            AcoCAMArray.cameras[i].CamPreview = False

        Thread(target=self.saveTh,args=(self.nSec.GetValue(),)).start()
       
        evt.Skip()
        return
    
