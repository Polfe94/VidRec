# import os
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
t0 = time.time()
tEnd = t0 + 10

cams = []
for c in range(12):
    cam = SingleCam(config.CamArray[c], mode = 'BW')
    cam.fps = 10
    cam.tREC = 20
    cam = cam.start()
    cams.append(cam)

while cams[0].finis_time >= time.time():
    next
# c.init_cam()
# c.is_recording = True
# c.cam.BeginAcquisition()
# c.outVid = cv2.VideoWriter(c.vidPath + c.vidName,
#         cv2.VideoWriter_fourcc('X','V','I','D'), 15, config.vidRes)

print(cam.frame_counter)

for c in cams:
    c.stop()
    del c.cam

del cams

# del cam
cam_list.Clear()
system.ReleaseInstance()


'''
c.start()
while(time.time() <= tEnd):
    c.update()
c.stop()
'''