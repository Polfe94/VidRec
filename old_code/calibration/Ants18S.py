# Common settings for Ants_2018

import os
from datetime import datetime, time, timedelta
import numpy as np


'''
+++ Paths
'''

_expPth = '/leov1/trackerleov/Ants_2018/'
_dtaPth = os.path.abspath('Ants_2018/data') + os.sep
_aviPth = os.path.abspath('Ants_2018/avi')  + os.sep
_calPth = os.path.abspath('Ants_2018/cal')  + os.sep

# set paths to local (dev-settings)
_expPth = os.path.abspath('Ants_2020/exp') + os.sep
_dtaPth = os.path.abspath('Ants_2020/data') + os.sep
_aviPth = os.path.abspath('Ants_2020/avi')  + os.sep
_calPth = os.path.abspath('Ants_2020/cal')  + os.sep

if os.path.exists(_expPth):
	_expLst = [exp for exp in sorted(os.listdir(_expPth)) if exp[:4] == '2018']
else:
	_expLst = []

'''
+++ Settings
'''

# with 12 cams with default layout (3,4)
_nCams, _nRows, _nCols = 12, 4, 3
_camLayout = np.arange(_nCams).reshape(_nRows, _nCols)

# frame rate
_fRate = 2

# raw frame size (pixels) per camera (w, h)
_rawImgSz = (4000, 3000)

# pixels/mm ratio 2018
# _px2mm = 0.19103
# pixels/mm ratio 2020
_px2mm = 0.17857
_mm2px = 1 /_px2mm
_mm2px = 5.68

# table size
_tblSzmm = (2000, 2000)
#_tblImgSz = (10468, 10468)

# operational table image size in pixels to speed-up tracking computation
_trkImgSz = (2000, 2000)

# max. table image size in pixels (10468, 10468); size given as cv2.size (w, h)
_tblImgSz = (int(_tblSzmm[0] *_mm2px), int(_tblSzmm[1] *_mm2px))

# vPlayer image Buffer
_bffImgSz = (800, 600)		# buffered image size (w, h) in pixels
_bufferSz = 120				# buffer queue size

# buffered full-image size in pixels
_imgSz = (_bffImgSz[0] *_nCols, _bffImgSz[1] *_nRows)

# viewer image size (default vPlayer viewer)
_vwrImgSz = (900, 900)

# +++ tracking parameters

# nest position in pixels
_nest = (_trkImgSz[0] //2, _trkImgSz[1] //2)

# _nestBound0 =  30	# mm
# _nestBound1 =  50	# mm
# _nestBound2 =  80	# mm

# _nestBound0 =  50	# mm
# _nestBound1 =  70	# mm
# _nestBound2 = 100	# mm

_nestBound0 = 100	# mm
_nestBound1 = 100	# mm
_nestBound2 = 150	# mm


# +++ tagging parameters

# position-change threshold (mm) for 1 sec
_threshold1 = 25 *_fRate
# max. non-controlled position-change allowed (mm)
_maxthrhld1 = 100
# overlapping positions threshold (mm)
_threshold2 = 3.6

# +++ cam parameters
_infoKey = ['sn', 'xOff', 'yOff', 'tl', 'tr', 'bl', 'br', 'wmm', 'hmm', 'fila', 'col']


# +++ frame to timeScore conversion

def f2t(f):
	return (datetime(1, 1, 1) + timedelta(milliseconds = max(f, 0) *1000 /_fRate +1)).time().isoformat()[:10]

# +++ timeScore to seconds conversion

def t2s(t):
	return np.sum(np.array(t.split(':'), dtype = 'int') *np.array([3600, 60, 1]))
