# from tokenize import Single
import PySpin
import sys
# import numpy as np
from PIL import Image

import cv2
# from vidgear.gears import WriteGear

from queue import Queue
from threading import Thread
import time


sys.path.append('/home/bigtracker/VidRec/')

import config
from argparser import argparse

system = PySpin.System.GetInstance()
cam_list = system.GetCameras()


def clear_cams():
    cam_list.Clear()
    system.ReleaseInstance()


''' ARGUMENT PARSER '''
mods = argparse(sys.argv[1:])

for i in mods:
    setattr(config, i, mods[i])

''' SINGLE CAMERA'''
class SingleCam:

    def __init__(self, serial_number, fps = 5):

        vidExtension = '.avi'
        # vidExtension = '.mp4'
        self.sn = serial_number

        self.vidPath = config.vidPath
        self.vidName = config.vidName + '_' + str(self.sn) + vidExtension

        # settings
        self.exposure = config.exposure
        self.gain = config.gain
        self.mode = config.mode
        self.resizeFactor = config.resize
        self.fps = fps

        # image obtention
        self.is_recording = False
        self.q = Queue(30)
        self.tStart = -1


    def init_cam(self):

        self.cam = cam_list.GetBySerial(self.sn)

        try:
            self.cam.Init()
        except:
            print('+++ Cam %s NOT inited' % self.sn)

        nodemap = self.cam.GetNodeMap()

        """ Camera acquisition mode """
        node_acquisition_mode = PySpin.CEnumerationPtr(nodemap.GetNode("AcquisitionMode"))
        node_acquisition_mode_continuous = node_acquisition_mode.GetEntryByName("Continuous")
        acquisition_mode_continuous = node_acquisition_mode_continuous.GetValue()
        node_acquisition_mode.SetIntValue(acquisition_mode_continuous)

        try:
            if self.cam.PixelFormat.GetAccessMode() == PySpin.RW:
                if self.mode == 'COLOR':
                    self.cam.PixelFormat.SetValue(PySpin.PixelColorFilter_BayerBG) #COLOR RGB
                else:
                    self.cam.PixelFormat.SetValue(PySpin.PixelFormat_Mono8)

        except PySpin.SpinnakerException as ex:
            print("Error: %s" % ex)


        """ Buffer Handling """
        nodemap_TLSdevice = self.cam.GetTLStreamNodeMap()
        ptrHandlingMode = PySpin.CEnumerationPtr(nodemap_TLSdevice.GetNode("StreamBufferHandlingMode"))
        ptrHandlingModeEntry = ptrHandlingMode.GetEntryByName("NewestOnly")
        ptrHandlingMode.SetIntValue(ptrHandlingModeEntry.GetValue())

        """Exposure Time"""
        self.cam.ExposureAuto.SetValue(PySpin.ExposureAuto_Off)
        self.setExp(self.exposure)

        """Gain"""
        self.cam.GainAuto.SetValue(PySpin.GainAuto_Off)
        self.setGain(self.gain)

        """Cam resolution"""
        # to be implemented

    def get_frame(self):
        im = self.cam.GetNextImage()
        t = time.time()
        im.Release()
        return self.sn, im, t

    def toQ(self):

        self.fps = self.set_fps()

        self.outVid = cv2.VideoWriter(self.vidPath + self.vidName,
        cv2.VideoWriter_fourcc('X','V','I','D'), self.fps, config.vidRes, 0)

        # wait until all cameras are ready
        time.sleep(self.tStart - time.time())

        while self.is_recording:

            if self.q.full():
                foo = self.q.get()

            self.q.put(self.get_frame())

    def fromQ(self, queue):

        while self.is_recording:

            try:
                result = self.q.get()
                queue.put(result)

            except:
                continue

    
    def set_fps(self):
        counter = 0
        tStart = time.time()
        t = 5
        while tStart + t > time.time():
            foo = self.get_frame()
            counter += 1

        return int(round(counter / t))

    def start(self):
    
        self.init_cam()
        self.is_recording = True
        self.cam.BeginAcquisition()

        print('Cam %s initialized' % self.sn)
        Thread(target = self.toQ, args = (), daemon = True).start()

    def stop(self):

        self.is_recording = False
        self.outVid.release()
        self.cam.EndAcquisition()

    def setExp(self, exposure):

        try:
            exposure = min(self.cam.ExposureTime.GetMax(),(exposure*1000))
            self.cam.ExposureTime.SetValue(exposure)
        except PySpin.SpinnakerException as ex:
            print("Error: %s" % ex.what())


    def setGain(self, gain):

        try:
            gain = min(self.cam.Gain.GetMax(),gain)
            self.cam.Gain.SetValue(gain)
        except PySpin.SpinnakerException as ex:
            print("Error: %s" % ex.what())



''' MULTI CAMERA CLASS '''
class MultiCam:

    def __init__(self, cam_list = [], fps = 15, time = {'for': 10, 'every': 0}, params = {}):

        ''' INITIALIZE CAMERAS '''
        self.cam_list = []

        if type(cam_list) == list:

            if len(cam_list):

                if all(hasattr(c, 'sn') for c in cam_list):
                    self.cam_list = cam_list

                elif all(i in config.CamArray.values() for i in cam_list):

                    for i in range(len(cam_list)):
                        cam = SingleCam(cam_list[i])
                        self.cam_list.append(cam)

                elif all(i < len(config.CamArray) for i in cam_list):

                    for i in range(len(cam_list)):
                        cam = SingleCam(config.CamArray[cam_list[i]])
                        self.cam_list.append(cam)

            else:

                for i in config.CamArray:
                    self.cam_list.append(SingleCam(config.CamArray[i]))

                print('+++ INITIALIZING ALL AVAILABLE CAMERAS +++')
        else:
            print('+++ ERROR: No valid cameras! +++')
            sys.exit(1)

        ''' CAMERA PARAMETERS '''

        if type(params) is not dict:
            params = {}
        if 'exposure' not in params.keys():

            if type(config.exposure) == list:
                if len(config.exposure) == len(self.cam_list):
                    params['exposure'] = config.exposure
                else:
                    params['exposure'] = [config.exposure[0]] * len(self.cam_list)
            else:
                params['exposure'] = [config.exposure] * len(self.cam_list)
        if 'gain' not in params.keys():
            
            if type(config.gain) == list:
                if len(config.gain) == len(self.cam_list):
                    params['gain'] = config.gain
                else:
                    params['gain'] = [config.gain[0]] * len(self.cam_list)
            else:
                params['gain'] = [config.gain] * len(self.cam_list)

        if 'mode' not in params.keys():

            if type(config.mode) == list:

                if config.mode[0] == 'COLOR':
                    params['mode'] = ['COLOR'] * len(self.cam_list)

                else:
                    params['mode'] = ['BW'] * len(self.cam_list)


        self.params = params
        self.init_params()

        # if time['every'] == 0:
        #     self.fps = 4 # // REPLACE

        # else:
        #     self.fps = 1/time['every']

        self.frame_dict = dict(zip([c.sn for c in self.cam_list], [0] * len(self.cam_list)))
        self.times_dict = dict(zip([c.sn for c in self.cam_list], [(-1, -1)] * len(self.cam_list)))
        self.fps = fps
        self.vidPath = config.vidPath
        self.q = Queue(150)
        self.frames = Queue(100)
        self.tREC = time

    def init_params(self):

        for i in range(len(self.cam_list)):
            for p in self.params:
                try:
                    setattr(self.cam_list[i], p, self.params[p][i])

                except:
                    print('+++ Index exception when trying to set param %s to cam %s +++ \n'+
                    'Length of parameter: %s; Length of cam array: %s' % (p, self.cam_list[i].sn, len(p), len(self.cam_list)))

                    print('Setting to a value of %s' % self.params[p][-1])
                    setattr(self.cam_list[i], p, self.params[p][-1])

    def start_cams(self):
        
        self.running = True
        tStart = time.time() + 10 # + 30
        for c in self.cam_list:
            c.fps = self.fps
            c.tStart = tStart
            c.start()
            Thread(target = c.fromQ, args = (self.q, ), daemon = True).start()
            Thread(target = self.choose_frame, args = (), daemon = True).start()
            for i in range(2):
                Thread(target = self.store_frames, args = (), daemon = True).start()

        return tStart


    def choose_frame(self):
        while True:
            if not self.running:
                break

            try:
                sn, im, t = self.q.get(1000)
                self.frames.put((sn, im, t))
            
            except:
                continue

            # if (abs(t - self.nextframe) < abs(self.times_dict[sn][0] - self.nextframe)):
            #     self.times_dict[sn] = (t, im)

            # else:
            #     if self.times_dict[sn][1] != -1:
            #         self.frames.put((sn, im, t))
            #         self.times_dict[sn] = (-1, -1)



    def store_frames(self):
        while True:
            if not self.running and self.frames.empty():
                break

            try:
                sn, im, t = self.frames.get(1000)
                self.frame_dict[sn] += 1
                a = Image.fromarray(im.GetNDArray())
                a.save(self.vidPath + 'cam_%s_frame_%s_t_%s.tif' % (sn, self.frame_dict[sn], t))
            
            except:
                continue

            
    def stop_video(self):
        for c in self.cam_list:
            c.is_recording = False

    def stop_cams(self):
        for c in self.cam_list:
            c.stop()

    def stop(self):

        for c in self.cam_list:
            del c.cam

        del self.cam_list
        clear_cams()


    def main(self):

        tStart = self.start_cams()

        print('Warming up capture threads. Recording starts in %s seconds' % round(tStart - time.time()))

        tEnd = tStart + self.tREC['for']

        self.nextframe = tStart

        # stop main thread until cams are finished recording
        while tEnd > time.time():
            if time.time() < self.nextframe:
                continue

            self.nextframe += 1 / self.fps


        self.running = False

        self.stop_video()

        time.sleep(2)

        self.stop_cams()

        # # time.sleep(5)
        # self.stop()

# if __name__ == '__main__':
#     m = MultiCam()
#     m.main()

#     time.sleep(10)

#     m.stop_cams()
#     m.stop()
