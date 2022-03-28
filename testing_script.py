# import os
from re import T
import PySpin
import sys

import cv2
# import numpy as np

from queue import Queue
from threading import Thread
import time

sys.path.append('/home/bigtracker/VidRec/')
import config

system = PySpin.System.GetInstance()
cam_list = system.GetCameras()

''' THREADS (vPol)'''

from script import SingleCam


config.vidPath = '/home/bigtracker/vid_test/'
tREC = 8
FPS = 15
NUM_FRAMES = tREC * FPS


cams = []

for c in range(len(config.CamArray)):
    cam = SingleCam(config.CamArray[c], mode = 'BW')
    cam.fps = FPS
    cam.tREC = tREC
    cam.resizeFactor = 1
    cam = cam.start()
    cam.videoThread()
    cams.append(cam)

flag = [0] * len(cams)
while True:
    for i in range(len(cams)):
        if cams[i].is_recording:
            flag[i] = 1

    if sum(flag) == len(cams):
        break

tfinish = time.time() + tREC

while tfinish > time.time():
    time.sleep(0.1)
    for c in cams:
        c.trigger.put(True)


print('Theoretical number of frames = %s' % NUM_FRAMES)

# cams.append(SingleCam(config.CamArray[0], mode = 'BW'))
# cams[0].fps = 15
# cams[0].tREC = 10
# cams[0].resizeFactor = 0.5
# cams[0] = cams[0].start()

flag = [0] * len(cams)
while True:
    for i in range(len(cams)):
        if cams[i].q.empty():
            flag[i] = 1

    if sum(flag) == len(cams):
        break

time.sleep(1)

for c in cams:
    print('Number of frames captured = %s' % c.frame_counter)
# c.init_cam()
# c.is_recording = True
# c.cam.BeginAcquisition()
# c.outVid = cv2.VideoWriter(c.vidPath + c.vidName,
#         cv2.VideoWriter_fourcc('X','V','I','D'), 15, config.vidRes)


for c in cams:
    del c.cam

del cams

# del cam
cam_list.Clear()
system.ReleaseInstance()

import sys

sys.exit(0)

'''
c.start()
while(time.time() <= tEnd):
    c.update()
c.stop()
'''