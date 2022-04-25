import sys

sys.path.append('G:/research/2022/VidRec/')

from script import *

system = PySpin.System.GetInstance()
cam_list = system.GetCameras()

sn = '17215408' # 25mm objective
sn = '17215422' # 75mm objective
sn = ['17215408', '17215422']

config.vidPath = 'G:/research/2022/vidtest/'
config.exposure = 20
config.gain = 10

tREC = 10
FPS = 15

# m = MultiCam([SingleCam(sn, fps = FPS)], fps = FPS, time = {'for': tREC, 'every': 0})
m = MultiCam([SingleCam(i, fps = FPS) for i in sn], fps = FPS, time = {'for': tREC, 'every': 0})