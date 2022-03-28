# import os
from copy import deepcopy
import PySpin
import sys

from PIL import Image
import cv2
# import numpy as np

from queue import Queue
from threading import Thread
import time

sys.path.append('/home/bigtracker/VidRec')
import config

system = PySpin.System.GetInstance()
cam_list = system.GetCameras()
''' THREADS (vPol)'''

class SingleCam:

    def __init__(self, serial_number, exposure = 40, gain = 2, mode = 'COLOR', resizeFactor = 1):

        self.sn = serial_number
        self.exposure = float(exposure)
        self.gain = float(gain)
        self.resizeFactor = resizeFactor
        
        self.im_count = 0

        self.vidPath = config.vidPath
        self.vidName = config.vidName + '_' + str(self.sn) + '.avi'
        self.fps = 15 ## ??
        # self.fps_timer = 0
        self.frame_counter = 0
        self.is_recording = False
        self.t = []
        self.tREC = 0
        self.q = Queue(1000)
        self.cams_ready = False
        self.trigger = Queue(1)
        # self.rdyQ.put(False)
        self.mode = mode

        # if mode == 'BW' or mode == 'BLACK_AND_WHITE':
        #     self.getImg = self.bwImg
        # else:
        #     self.getImg = self.colImg

    def init_cam(self):

        self.cam = cam_list.GetBySerial(self.sn)

        try:
            self.cam.Init()
        except:
            print('+++ Cam %s NOT inited' % self.sn) 

        nodemap = self.cam.GetNodeMap()

        node_acquisition_mode = PySpin.CEnumerationPtr(nodemap.GetNode("AcquisitionMode"))
        node_acquisition_mode_continuous = node_acquisition_mode.GetEntryByName("Continuous")
        acquisition_mode_continuous = node_acquisition_mode_continuous.GetValue()
        node_acquisition_mode.SetIntValue(acquisition_mode_continuous)

        # set RGB mode
        try:
            if self.cam.PixelFormat.GetAccessMode() == PySpin.RW:
                if self.mode == 'COLOR':
                    self.cam.PixelFormat.SetValue(PySpin.PixelColorFilter_BayerBG) #COLOR RGB
                else:
                    self.cam.PixelFormat.SetValue(PySpin.PixelFormat_Mono8)
                # print("Pixel format set to %s..." % self.cam.PixelFormat.GetCurrentEntry().GetSymbolic())
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

        """Cam resolution"""
        if self.cam.Width.GetAccessMode() == PySpin.RW and self.cam.Width.GetInc() != 0 and self.cam.Width.GetMax != 0:
            self.cam.Width.SetValue(int(self.resizeFactor * config.vidRes[0]))
        
        # node_offset_x = PySpin.CIntegerPtr(nodemap.GetNode('OffsetX'))
        # if PySpin.IsAvailable(node_offset_x) and PySpin.IsWritable(node_offset_x):

        #     node_offset_x.SetValue(node_offset_x.GetMin())

        # node_offset_y = PySpin.CIntegerPtr(nodemap.GetNode('OffsetY'))
        # if PySpin.IsAvailable(node_offset_y) and PySpin.IsWritable(node_offset_y):

        #     node_offset_y.SetValue(node_offset_y.GetMin())

        # if self.cam.Height.GetAccessMode() == PySpin.RW and self.cam.Height.GetInc() != 0 and self.cam.Height.GetMax != 0:
        #     self.cam.Height.SetValue(int(self.resizeFactor * config.vidRes[1]))


 


        def grab_next_image_by_trigger(nodemap):
            """
            This function retrieves a single image using the trigger. In this example,
            only a single image is captured and made available for acquisition - as such,
            attempting to acquire two images for a single trigger execution would cause
            the example to hang. This is different from other examples, whereby a
            constant stream of images are being captured and made available for image
            acquisition.

            :param nodemap: Device nodemap to retrieve images from.
            :type nodemap: INodeMap
            :return: True if successful, False otherwise
            :rtype: bool
            """
            try:
                result = True

                # Execute software trigger
                software_trigger_command = PySpin.CCommandPtr(nodemap.GetNode('TriggerSoftware'))
                if not PySpin.IsAvailable(software_trigger_command) or not PySpin.IsWritable(software_trigger_command):
                    print('Unable to execute trigger. Aborting...\n')
                    return False

                software_trigger_command.Execute()

            except PySpin.SpinnakerException as ex:
                print('Error: %s' % ex)
                result = False

            return result


        '''
        # MANUAL WHITE BALANCE
        self.cam.BalanceWhiteAuto.SetValue(PySpin.BalanceWhiteAuto_Off, False)
        node_BR = PySpin.CFloatPtr(nodemap.GetNode("BalanceRatio"))
        self.cam.BalanceRatioSelector.SetValue(PySpin.BalanceRatioSelector_Blue)
        node_BR.SetValue(config._balanceBlue, False)
        self.cam.BalanceRatioSelector.SetValue(PySpin.BalanceRatioSelector_Red)
        node_BR.SetValue(config._balanceRed, False)
        '''
        

        self.setExp(10)
        self.setGain(5)

    def getImg(self):
        img = self.cam.GetNextImage()
        result = img.GetNDArray()
        img.Release()
        self.frame_counter += 1
        return result

    def update(self):

        while self.cams_ready == False:
            next

        # self.frame = self.getImg()
        self.t0 = time.time()
        self.finish_time = self.t0 + self.tREC

        while self.is_recording:
            if self.trigger.full():
                ret = self.trigger.get()

                self.q.put(self.getImg())
            
            # self.vidREC()
            # img = self.q.get()
            # self.t.append(time.time() - self.t0) ## real "fps"
            # self.outVid.write(img)
        self.stop()

    def videoThread(self):
        for t in range(3):
            Thread(target = self.vidREC, args = (), daemon = True).start()
        # self.vidThread = Thread(target = self.vidREC, args = (), daemon = True)
        # self.vidThread.start()


    def vidREC(self):

        while self.cams_ready == False:
            next

        while True:

            # self.im_count += 1
            img = self.q.get()

            cv2.imwrite('Frame_%s_cam_%s.tif' % (self.frame_counter, self.sn), img)

            if self.is_recording == False and self.q.empty():
            # if self.is_recording == False and len(self.q) == 0:
                break

            # img.Save('Frame_%s_cam_%s.tif' % (self.im_count, self.sn))
            # img.save('Frame_%s_cam_%s.tif' % (self.im_count, self.sn))
            # cv2.imwrite('Frame_%s_cam_%s.png' % (self.im_count, self.sn), img, [cv2.IMWRITE_PNG_COMPRESSION, 0])

    def start(self):
    
        self.init_cam()
        self.is_recording = True
        self.cam.BeginAcquisition()

        print('Cam %s initialized' % self.sn)

        # self.fps = int(self.cam.AcquisitionFrameRate.GetValue()) ## replace fps!!
        # print('Cam FPS = %s ' % self.fps)

        self.outVid = cv2.VideoWriter(self.vidPath + self.vidName,
        cv2.VideoWriter_fourcc('X','V','I','D'), self.fps, config.vidRes, 0)

        t = Thread(target = self.update, args = (), daemon = True)
        # videoThread = Thread(target = self.vidREC, args = (), daemon = True)
        
        t.start()
        # videoThread.start()

        return self

    def stop(self):

        self.is_recording = False
        self.outVid.release()
        self.cam.EndAcquisition()


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

    
    def setExp(self, exposure):

        try:
            exposure = min(self.cam.ExposureTime.GetMax(),(exposure*1000))
            if exposure < 20:
                exposure = 20
            self.cam.ExposureTime.SetValue(exposure)
        except PySpin.SpinnakerException as ex:
            print("Error: %s" % ex.what())


    def setGain(self, gain):

        try:
            gain = min(self.cam.Gain.GetMax(),gain)
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

