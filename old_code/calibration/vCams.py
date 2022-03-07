
import os
from datetime import datetime, time, timedelta
import numpy as np
import cv2
from time import sleep

from math import floor, sqrt
import json

import Ants18S as settings
from Ants18S import _nCams, _camLayout, _nCols, _nRows, _fRate
from Ants18S import _tblSzmm, _tblImgSz, _mm2px
from Ants18S import _rawImgSz, _vwrImgSz
from Ants18C import Loc
from Ants18S import f2t, t2s

# cv2.VideoCapture() properties
# (note that the sufix CV_ specified in the documentation must be removed for opencv version 4.0.0 !!!)
#  0. CAP_PROP_POS_MSEC Current position of the video file in milliseconds.
#  1. CAP_PROP_POS_FRAMES 0-based index of the frame to be decoded/captured next.
#  2. CAP_PROP_POS_AVI_RATIO Relative position of the video file
#  3. CAP_PROP_FRAME_WIDTH Width of the frames in the video stream.
#  4. CAP_PROP_FRAME_HEIGHT Height of the frames in the video stream.
#  5. CAP_PROP_FPS Frame rate.
#  6. CAP_PROP_FOURCC 4-character code of codec.
#  7. CAP_PROP_FRAME_COUNT Number of frames in the video file.
#  8. CAP_PROP_FORMAT Format of the Mat objects returned by retrieve() .
#  9. CAP_PROP_MODE Backend-specific value indicating the current capture mode.
# 10. CAP_PROP_BRIGHTNESS Brightness of the image (only for cameras).
# 11. CAP_PROP_CONTRAST Contrast of the image (only for cameras).
# 12. CAP_PROP_SATURATION Saturation of the image (only for cameras).
# 13. CAP_PROP_HUE Hue of the image (only for cameras).
# 14. CAP_PROP_GAIN Gain of the image (only for cameras).
# 15. CAP_PROP_EXPOSURE Exposure (only for cameras).
# 16. CAP_PROP_CONVERT_RGB Boolean flags indicating whether images should be converted to RGB.
# 17. CAP_PROP_WHITE_BALANCE Currently unsupported
# 18. CAP_PROP_RECTIFICATION Rectification flag for stereo cameras (note: only supported by DC1394 v 2.x backend currently)

# +++ _Cam Worker functions

def wrkr_init(key, run, imgSz, bufferSz):

	global _Cam
	_Cam = Cam(key, run)

	_Cam.start()
	_Cam.homography(imgSz)
	_Cam.setBff(bufferSz, _rawImgSz)
	if len(run.dtaPth): _Cam.readData()

	_Cam.imgWndw = _Cam.getCrop(_vwrImgSz, _camLayout)
	_Cam.imgSize = (_Cam.imgWndw[1] -_Cam.imgWndw[0], _Cam.imgWndw[3] -_Cam.imgWndw[2])

def wrkr_setRes(imgSz):
	sleep(.003)
	_Cam.homography(imgSz)
	return _Cam.key

def wrkr_adjust(imgSz, info):
	sleep(.003)
	_Cam.info = info[_Cam.key]
	_Cam.homography(imgSz)
	return _Cam.key

def wrkr_ffwd(s, bufferSz):
	_Cam.setBff(bufferSz, _rawImgSz)
	frame = _Cam.ffwd(s)
	return frame

def wrkr_wrtBff(key):
	sleep(.003)
	ok = _Cam.wrtBff()
	return (_Cam.key if ok else -1)

def wrkr_bffFrm(f):
	sleep(.003)
	return (_Cam.hCrop, _Cam.readBff(f = f))

def wrkr_clrFrm(f):
	sleep(.003)
	return (_Cam.hCrop, _Cam.readBff(f = f, color = True))

def wrkr_rawFrm(key):
	return (_Cam.key, _Cam.vid.read())

def wrkr_getFrm(key):
	ok = _Cam.wrtBff()
	return (cv2.resize(_Cam.readBff(), _Cam.imgSize), _Cam.imgWndw)
	# else:
	# 	return (np.zeros(_Cam.imgSize, dtype = 'uint8'), _Cam.imgWndw)

def wrkr_getDta(fKey):
	# track-data given in mm relative to _vwrImgSz
	sleep(.003)
	return(_Cam.key, _Cam.getLocs(fKey))

def wrkr_evTime(at):
	# time of first outBound() event
	sleep(.003)
	return (_Cam.key, _Cam.evTime(at))

def wrkr_stop(key):
	sleep(.003)
	_Cam.stop()
	return _Cam.key

# +++ video-stream class

class Cam():

	def __init__(self, key, run):

		self.key = key							# cam array number
		self.expPth = run.expPth				# video path
		self.dtaPth = run.dtaPth

		self.info = run.info[self.key]
		self.mm2px = run.info[99]

		self.sn = str(self.info[0])
		self.fila = (int)(self.info[9])
		self.col = (int)(self.info[10])

		print ('+++ Cam %02i %s, initialized' % (self.key, self.sn))

	def __repr__(self):

		camInfo = '\n'
		camInfo += '+++ Cam %s \n' % str(self.key).zfill(2)
		camInfo += '    serialNumber ... %s \n' % self.sn
		camInfo += '    fila ........... %02i \n' % self.fila
		camInfo += '    col ............ %02i \n' % self.col

		return camInfo

	def fileName(self):

		try:
			for fname in os.listdir(self.expPth):
				if self.sn in fname: break
			return self.expPth +fname
		except:
			print ('+++ Cam %02i %s, ' % (self.key, self.sn), end='')
			print('NO video file found !!!')

	def homography(self, imgSz = _tblImgSz):

		pts_src = np.array(self.info[3:7])	# tl, tr, bl, br

		w, h  = int(self.info[7] *self.mm2px), int(self.info[8] *self.mm2px)
		pts_dst = np.array([[0, 0], [w, 0], [0, h], [w, h]], dtype = 'float64')

		xOff, yOff = int(self.info[1] *self.mm2px), int(self.info[2] *self.mm2px)
		pts_dst += np.array([xOff, yOff])

		# homography image-size factor
		hFctr = np.array([imgSz[0]/_tblImgSz[0], imgSz[1]/_tblImgSz[1]])
		pts_dst *= hFctr

		try:
			self.hMtx, status = cv2.findHomography(pts_src, pts_dst)
			self.hSize = imgSz
			self.hCrop = self.getCrop(self.hSize, _camLayout)
		except:
			print ('+++ Cam %02i %s, ' % (self.key, self.sn), end='')
			print('Error in findHomography()')
			print(pts_src)
			print(pts_dst)

	def start(self):
		self.frame = -1
		try:
			self.vid = cv2.VideoCapture(self.fileName())
		except:
			print ('+++ Cam %02i %s, ' % (self.key, self.sn), end='')
			print('Error starting Capture !!')

	def ffwd(self, s, fback = 0):
		f = s *_fRate -fback -1
		# cam time in milliseconds: self.vid.get(cv2.CAP_PROP_FPS) = 600 !!!
		msec = f /self.vid.get(cv2.CAP_PROP_FPS) * 1000
		# set cam position
		self.vid.set(cv2.CAP_PROP_POS_MSEC, msec)
		# get cam frame
		self.frame = self.vid.get(cv2.CAP_PROP_POS_FRAMES)
		return int(f)

	def stop(self):
		if self.vid.isOpened(): self.vid.release()

	def getCrop(self, fullSz, layout):
		f, c = np.where(layout == self.key)[0][0], np.where(layout == self.key)[1][0]
		a = int(round(fullSz[0] /_nCols *c, 0))
		b = int(round(fullSz[0] /_nCols *(c +1), 0))
		c = int(round(fullSz[1] /_nRows * f, 0))
		d = int(round(fullSz[1] /_nRows *(f +1), 0))
		return (a, b, c, d)

	def setBff(self, bufferSz, bffImgSz):
		self.bufferSz, self.bffImgSz = bufferSz, bffImgSz
		self.iBuffer = [np.zeros((self.bffImgSz[1], self.bffImgSz[0])), 3] * self.bufferSz
		# self.iBuffer = [np.zeros((self.bffImgSz[1], self.bffImgSz[0]))] * self.bufferSz
		self.bffPntr = -1

	def wrtBff(self):
		ok, frm = self.vid.read()
		self.bffPntr = (self.bffPntr +1) %self.bufferSz
		if ok:
			self.iBuffer[self.bffPntr] = frm
			# self.iBuffer[self.bffPntr] = cv2.cvtColor(frm, cv2.COLOR_BGR2GRAY)
		else:
			self.iBuffer[self.bffPntr] = np.zeros((self.bffImgSz[1], self.bffImgSz[0], 3))
			# self.iBuffer[self.bffPntr] = np.zeros((self.bffImgSz[1], self.bffImgSz[0]))
		return ok

	def readBff(self, f = 0, color = False):
		bffPntr = (self.bffPntr - f) %self.bufferSz
		a, b, c, d = self.hCrop
		if not color:
			return cv2.warpPerspective(cv2.cvtColor(self.iBuffer[bffPntr], cv2.COLOR_BGR2GRAY), self.hMtx, self.hSize)[c:d, a:b]
		else:
			return cv2.warpPerspective(self.iBuffer[bffPntr], self.hMtx, self.hSize)[c:d, a:b, :]
		# return cv2.warpPerspective(self.iBuffer[bffPntr], self.hMtx, self.hSize)[c:d, a:b]

	def readData(self):
		self.tData = {}
		a, b, c, d = self.getCrop(_tblSzmm, _camLayout)
		fName = self.dtaPth + 'Cam%02d.txt' % self.key
		if os.path.exists(fName):
			with open(fName) as f:
				for line in f:
					tStamp, frame, t, xpx, ypx, xmm, ymm = line.split(',')
					loc = Loc(int(frame), xmm, ymm)
					if (a < loc.xmm < b and c < loc.ymm < d):
						if loc.frm not in self.tData.keys(): self.tData[loc.frm] = []
						self.tData[loc.frm].append(loc)

		self.tNObs = sum([len(time) for time in self.tData.values()])
		print('+++ Read cam%02d %6d' % (self.key, self.tNObs))

	def getLocs(self, frm):
		if frm in self.tData.keys():
			return self.tData[frm]
		else:
			return []

	def evTime(self, at = 0):

		evTime = 0
		frmLst = sorted(self.tData.keys())
		if at == -1:
			frmLst.reverse()
		for frm in frmLst:
			for _Loc in self.tData[frm]:
				if _Loc.beyond():
					evTime = frm
					break
			if evTime: break

		return evTime
