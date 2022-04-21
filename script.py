import PySpin
import sys
import numpy as np

import cv2
# from vidgear.gears import WriteGear

from queue import Queue
from threading import Thread
import time


sys.path.append('/home/bigtracker/VidRec/')

import config

system = PySpin.System.GetInstance()
cam_list = system.GetCameras()


def clear_cams():
    cam_list.Clear()
    system.ReleaseInstance()


''' ARGUMENT PARSER '''
def arg_parse():
    pass

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
        self.frame_counter = 0
        self.is_recording = False
        self.t = []
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

    def get(self):
        im = self.cam.GetNextImage()
        t = time.time()
        im.Release()
        return im, t

    def toQ(self):

        while self.tStart < time.time():
            continue

        while self.is_recording:

            if self.q.full():
                foo = self.q.get()

            self.q.put(self.get())

    def fromQ(self):
        
        while self.is_recording:
            try:
                im, t = self.q.get()
                self.t.append(t)
            except:
                continue


    def getImg(self):
        img = self.cam.GetNextImage()
        self.t.append(time.time())
        self.frame_counter += 1
        result = img.GetNDArray()
        img.Release()
        return result

    def update(self):
        # warm up to wait for all cams to init
        while self.tStart > time.time():
            continue

        nextframe = self.tStart
        while self.is_recording:

            if nextframe <= time.time():
                img = self.getImg()
                self.outVid.write(img)

                nextframe += 1/self.fps

                t2sleep = nextframe - time.time()
                if t2sleep > 0:
                    time.sleep(t2sleep)


        # if hasattr(self, 'clock'):

        #     nextframe = self.tStart

        #     while self.is_recording:

        #         if time.time() > nextframe:

        #             # capture image
        #             img = self.getImg()
        #             self.outVid.write(img)
        #             # self.q.queue.appendright(img)
        #             del img

        #             # set next image timer
        #             nextframe += self.clock

        # else:

        #     while self.is_recording:
        #         self.ready = True

        #         try:
        #             flag = self.q.get()

        #         except:
        #             continue

        #         if flag:
        #             # capture image
        #             try:
        #                 img = self.getImg()
        #                 # self.outVid.write(img)
        #                 # self.q.queue.appendright(img)
        #                 del img
        #                 self.ready = False

        #             except:
        #                 continue
                

    # def update(self):

    #     # warm up to wait for all cams to init
    #     while self.tStart > time.time():
    #         continue

    #     self.videoThread()

    #     if hasattr(self, 'clock'):

    #         nextframe = self.tStart

    #         while self.is_recording:

    #             if time.time() > nextframe:

    #                 # capture image
    #                 img = self.getImg()
    #                 self.q.put(img)
    #                 # self.q.queue.appendright(img)
    #                 del img

    #                 # set next image timer
    #                 nextframe += self.clock

    #     else:

    #         while self.is_recording:

    #                 # capture image
    #                 try:
    #                     img = self.getImg()
    #                     self.q.put(img)
    #                     # self.q.queue.appendright(img)
    #                     del img

    #                 except:
    #                     continue


    def videoThread(self):

        Thread(target = self.vidREC, args = (), daemon = True).start()


    def save_img(self):

        img = self.q.get()
        cv2.imwrite('frame_%s_time_%s_cam_%s.tif' % (self.frame_counter, self.t[self.frame_counter], self.sn), img)
        self.frame_counter += 1



    def vidREC(self):

        while True:
            im = self.q.get()

            if im != -1:
                self.outVid.write(im)


        # while self.is_recording:


        #     try:
        #         frame = self.q.get()
        #         self.outVid.write(frame)
        #         del frame

        #     except:
        #         continue

            # try:
            #     frame = self.q.queue.pop(0)
            #     self.outVid.write(frame)
            #     del frame

            # except:
            #     continue

    def start(self):
    
        self.init_cam()
        self.is_recording = True
        self.cam.BeginAcquisition()

        print('Cam %s initialized' % self.sn)
        Thread(target = self.toQ, args = (), daemon = True).start()
        Thread(target = self.fromQ, args = (), daemon = True).start()

        self.outVid = cv2.VideoWriter(self.vidPath + self.vidName,
        cv2.VideoWriter_fourcc('X','V','I','D'), self.fps, config.vidRes, 0)
        # self.videoThread()

    # def start(self):

    #     self.init_cam()
    #     self.is_recording = True
    #     self.cam.BeginAcquisition()

    #     print('Cam %s initialized' % self.sn)

    #     self.outVid = cv2.VideoWriter(self.vidPath + self.vidName,
    #     cv2.VideoWriter_fourcc('X','V','I','D'), self.fps, config.vidRes, 0)
    #     self.videoThread()

        # output_params = {'-input_framerate': self.fps, '-preset': 'ultrafast',
        # '-vcodec': 'libx265', '-crf': 17}
        # self.outVid = WriteGear(self.vidPath + self.vidName, **output_params)
        # Thread(target = self.update, args = (), daemon = True).start()

    def stop(self):

        self.is_recording = False
        self.outVid.release()
        # self.outVid.close()
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

    def __init__(self, cam_list = [], time = {'for': 10, 'every': 0}, params = {}):

        ''' INITIALIZE CAMERAS '''
        self.cam_list = []

        if len(cam_list):

            if(all(type(c) == SingleCam for c in cam_list)):
                self.cam_list = cam_list

            if all(i in config.CamArray.values() for i in cam_list):

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

        ''' CAMERA PARAMETERS '''

        if type(params) is not dict:
            params = {}
        if 'exposure' not in params.keys():
            params['exposure'] = [config.exposure] * len(self.cam_list)
        if 'gain' not in params.keys():
            params['gain'] = [config.gain] * len(self.cam_list)
        if 'mode' not in params.keys():
            params['mode'] = [config.mode] * len(self.cam_list)

        self.params = params
        self.init_params()

        if time['every'] == 0:
            self.fps = 4 # // REPLACE

        else:
            self.fps = 1/time['every']

        self.vidPath = config.vidPath

        self.tREC = time
        self.trigger = [False] * len(self.cam_list)

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

        tStart = time.time() + 30
        for c in self.cam_list:
            c.fps = self.fps
            c.tStart = tStart
            c.start()
            # Thread(target = self.clock_trigger, args = (), daemon = True).start()
            # c.videoThread()

        return tStart

    # def start_cams(self):
    #     tStart = time.time() + 10
    #     for c in self.cam_list:
    #         c.start()

    #     return tStart

    # def grab_image(self, cam):
    #     im = cam.getImg()
    #     return im
        # self.cam_list[cam].outVid.write(im)

    # def clock_trigger(self):
    #     while self.running:
    #         for i in range(len(self.cam_list)):
    #             self.trigger[i] = self.cam_list[0].ready

    #         if all(self.trigger):
    #             for c in self.cam_list:
    #                 c.q.put(True)
    #             self.trigger = [False] * len(self.cam_list)

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

        # stop main thread until cams are finished recording
        while tEnd > time.time():
            continue

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
