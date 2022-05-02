# from tokenize import Single
import PySpin
import sys
import numpy as np
from PIL import Image

import cv2
# from vidgear.gears import WriteGear

from queue import Queue
from threading import Thread
import time

from multiprocessing.pool import Pool

sys.path.append('/home/bigtracker/VidRec/')

import config
from argparser import argparse

# system = PySpin.System.GetInstance()
# cam_list = system.GetCameras()


# def clear_cams():
#     cam_list.Clear()
#     system.ReleaseInstance()

''' ARGUMENT PARSER '''
# mods = argparse(sys.argv[1:])

# for i in mods:
#     setattr(config, i, mods[i])

''' SINGLE CAMERA'''
class SingleCam:

    def __init__(self, serial_number, fps = 15):

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
        self.frame_counter = 0
        self.is_recording = False
        # self.q = Queue(100) # Queue(30)
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
        self.frame_counter += 1
        result = im.GetNDArray()
        im.Release()
        return self.sn, result, t

    # def toQ(self):

    #     # self.fps = self.set_fps()

    #     # wait until all cameras are ready
    #     time.sleep(self.tStart - time.time())

    #     while self.is_recording:

    #         if self.q.full():
    #             foo = self.q.get(1000)

    #         self.q.put(self.get_frame(), 1000)

    # def fromQ(self, queue):

    #     while self.is_recording:

    #         try:
    #             result = self.q.get(1000)
    #             queue.put(result)

    #         except:
    #             continue

    
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

        self.outVid = cv2.VideoWriter(self.vidPath + self.vidName,
        cv2.VideoWriter_fourcc('X','V','I','D'), self.fps, config.vidRes, 0)

        print('Cam %s initialized' % self.sn)
        # Thread(target = self.toQ, args = (), daemon = True).start()

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

    def __init__(self, cam_list = [], time = 10, fps = 15, params = {}):

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

        # self.frame_dict = dict(zip([c.sn for c in self.cam_list], [0] * len(self.cam_list)))

        # clock: last time difference, frame
        # self.times_dict = dict(zip([c.sn for c in self.cam_list], [[-1, -1, -1, -1]] * len(self.cam_list)))
        self.frame_counter = 0
        self.fps = fps
        self.vidPath = config.vidPath
        self.q = Queue(500)
        # self.frames = Queue(100)
        self.tREC = time

    def trigger(self, cam):
        result = self.cam_list[cam].get_frame()
        return self.frame_counter, result
        # self.q.put((self.frame_counter, result))

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
        tStart = time.time() +15 # 30
        for c in self.cam_list:
            c.fps = self.fps
            c.tStart = tStart
            c.start()
            # Thread(target = c.fromQ, args = (self.q, ), daemon = True).start()
            # Thread(target = self.choose_frame, args = (), daemon = True).start()
            for i in range(10):
                Thread(target = self.store_frames, args = (), daemon = True).start()

        return tStart


    # def choose_frame(self):

    #     while True:
    #         if not self.running and self.q.empty():
    #             break

    #         try:
    #             sn, im, t = self.q.get(1000)
    #             # self.frames.put((sn, im, t))
            
    #         except:
    #             continue


    #         last_dif = self.times_dict[sn][0]
    #         frame, ref = self.times_dict[sn][1]
    #         last_im = self.times_dict[sn][2]
    #         last_t = self.times_dict[sn][3]


    #         dif = t - ref

    #         if abs(dif) < abs(last_dif):
    #             self.times_dict[sn] = (dif, (frame, ref), im, t)

    #         else:

    #             try:
    #                 frame, ref = self.nextframe[sn].pop(0)

    #             except:
    #                 break

    #             self.frames.put((sn, last_im, frame, last_t))
    #             self.times_dict[sn] = (dif, (frame, ref), im, t) 

    def store_frames(self):
        while True:
            if not self.running and self.q.empty():
                break

            try:
                # idx = index of the frame (i.e. frame number)
                # result = serial number, image, time
                idx, result = self.q.get(1000)

                # self.frame_dict[sn] += 1
                # frame = self.frame_dict[sn].get()
                # self.frame_dict[sn].put(frame + 1)
                
                a = Image.fromarray(result[1])
                a.save(self.vidPath + 'cam_%s_frame_%s_t_%s.tif' % (result[0], idx, result[2]))
            
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

        self.pool = Pool(len(self.cam_list))

        tStart = self.start_cams()

        print('Warming up capture threads. Recording starts in %s seconds' % round(tStart - time.time()))

        tEnd = tStart + self.tREC

        # clock = list(np.arange(tStart, tEnd, 1/ self.fps)) 
        # clock = list(zip(range(len(clock)), clock))


        # self.nextframe = dict(zip([c.sn for c in self.cam_list], [clock] * len(self.cam_list)))
        # for k in self.times_dict:
        #     self.times_dict[k][1] = self.nextframe[k].pop(0)

        self.nextframe = tStart

        # stop main thread until cams are finished recording
        while tEnd > time.time():
            
            if time.time() > self.nextframe or self.nextframe - time.time() < 0.0001:
                result = self.pool.map(self.trigger, list(range(len(self.cam_list))))
                self.q.put(result)
                self.nextframe += 1/ self.fps
                self.frame_counter += 1

            
            # if time.time() < self.nextframe:
            #     continue

            # else:
            #     self.nextframe += 1/ self.fps

        # de-init system
        time.sleep(0.2)
        self.running = False

        self.stop_video()
        time.sleep(0.2)

        self.stop_cams()

        # time.sleep(1)
        # self.stop()

# if __name__ == '__main__':
#     m = MultiCam()
#     m.main()

#     time.sleep(10)

#     m.stop_cams()
#     m.stop()
