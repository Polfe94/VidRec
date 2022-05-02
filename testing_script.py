import PySpin
from multiprocessing import Queue
from multiprocessing import Pool
from threading import Thread
import time
import sys

system = PySpin.System.GetInstance()
cL = system.GetCameras()


q = Queue()
cam_list = [cL.GetByIndex(i) for i in range(4)]
for cam in cam_list:
    cam.Init()
    cam.BeginAcquisition()
    cam.q = q



# _in_list = [Queue()] * 4
# _IN_Q = Queue()
# _out_list = [Queue()] * 4

print('Queues created')

# def trigger(cam):
#     tend = time.time() + 10
#     while True:

#         try:
#             rdy = IN_Q.get(timeout = 1)
        
#         except:
#             if time.time() > tend:
#                 break
#             else:
#                 continue

#         if rdy == False:
#             break

#         else:
#             print('Getting Image')
#             im = cam_list[cam].GetNextImage()
#             result = im.GetNDArray()
#             OUT_Q.put(result)
#             im.Release()

def trigger(cam):

    im = cam_list[cam].GetNextImage()
    print('Image retrieved!')
    
    result = im.GetNDArray()
    print('Array converted')

    im.Release()
    print('Pointer released!')
    
    trigger.q.put(result)
    return time.time()

def _init(queue):
    trigger.q = queue

# def shot(value):
#     shot.IN_Q.put(value)
#     return ['Done!']

# def _init(IN_Q):
#     shot.IN_Q = IN_Q

pool = Pool(4, _init, [q])

print('Pool created')

result = pool.map(trigger, list(range(4)))
print(result)


for cam in cam_list:
    cam.EndAcquisition()
    cam.DeInit()
    time.sleep(0.2)

del cam_list

cL.Clear()
system.ReleaseInstance()


input()
sys.exit(0)
    
threads = []
for i in range(4):
    _in_list[i].put(True)
    t = Thread(target = trigger, args = [_in_list[i], _out_list[i], i], daemon = True)
    t.start()
    threads.append(t)

print('Threads and Pool created... entering loop')

tEnd = time.time() + 10

result = pool.imap(shot, _in_list)
print(result)
time.sleep(1)
print('Size of queue = %s' % _out_list[0].qsize())


for cam in cam_list:
    cam.EndAcquisition()
    del cam

cL.Clear()
system.ReleaseInstance()

[print(i.qsize()) for i in _in_list]

for i in _in_list:
    while True:
        if i.empty():
            i.put(False)
            break
        else:
            i.get()

        

time.sleep(0.5)

cam.EndAcquisition()
del cam

cL.Clear()
system.ReleaseInstance()

input()
sys.exit(0)


'''
# from multiprocessing.pool import Pool
from pathos.multiprocessing import ProcessingPool as Pool
import time
import numpy as np
from threading import Thread
from queue import Queue

import PySpin

import sys
sys.path.append('/home/bigtracker/VidRec')


system = PySpin.System.GetInstance()
cL = system.GetCameras()

def clear_cams():
    cL.Clear()
    system.ReleaseInstance()

def trigger(cam):
    im = cam_list[cam].GetNextImage()
    result = im.GetNDArray()
    im.release()

    return time.time()

import config
# from script import *

cam_list = []
for cam in config.CamArray:
    k = cL.GetBySerial(config.CamArray[cam])
    k.Init()
    k.BeginAcquisition()
    cam_list.append(k)


# cam_list = [SingleCam(config.CamArray[i]) for i in range(12)]
# for c in cam_list:
#     c.start()

pool = Pool(12)
print('Got here')

try:
    t0 = time.time()
    result = pool.map(trigger, list(range(12)))
    print('Time expended = %s seconds' % str(round(time.time() - t0, 5)))

    print(result)
    input()
    sys.exit(0)

except:
    for c in cam_list:
        c.EndAcquisition()
        del c
    
    clear_cams()
    sys.exit(1)
        

# def lol(i):
#     return time.time()

# class mc:
#     def __init__(self, cam_list):

#         self.cam_list = cam_list
#         self.q = Queue(100)


#     def start(self):

#         self.running = True
#         tStart = time.time() +15 # 30
#         for c in self.cam_list:
#             c.tStart = tStart
#             c.start()
#         return tStart

#     def stop_cams(self):
#             for c in self.cam_list:
#                 c.stop()

#     def stop(self):

#         for c in self.cam_list:
#             del c.cam

#         del self.cam_list
#         clear_cams()

#     def main(self):

#         pool = Pool(12)
#         # self.start()

#         self.results = []



#         for i in range(10):
#             print('Iter = %s' % i)
#             result = pool.map(trigger, list(range(12)))
#             self.results.append(result)
#             print(len(self.results))

#         print('Finished, length of result = %s' % len(self.results))
#         input()


# m = mc(cam_list)

# m.main()

# sys.exit(0)


























class Cam:
    def __init__(self, sn):
        self.sn = sn
        self.im = np.random.rand(4000, 3000, 3)

    def get_frame(self):

        t = time.time()
        # return self.sn, self.im, t
        return t


cam_list = [Cam(i) for i in range(12)]

def trigger(cam, cam_list = cam_list):
    r = cam_list[cam].get_frame()
    return r

t0 = time.time()
print('Opening pool')
p = Pool(12)
print('Done ! (time expended %s seconds)' % str(round(time.time() - t0,2)))

# q = Queue(12)

# result = []
# t = []
# for i in range(12):
#     t.append(Thread(target = getter, args = (q)).start())


# results = []
# def collect_results(result):
#     results.append(result)

t0 = time.time()
result = p.map(trigger, list(range(12)))
print('Time expended = %s seconds' % str(round(time.time() - t0, 5)))

t0 = time.time()
# result = list(result)
print('Time to retrieve results = %s seconds' % str(round(time.time() - t0, 5)))

# print([i[2] for i in result])
print(result)

input()

'''