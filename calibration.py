import os
from math import cos, sin, pi
import numpy as np
import cv2
from time import sleep
import json
from PIL import Image
import psutil
from copy import deepcopy
from multiprocessing import Pool



''' GLOBAL VARIABLES '''
_nCams, _nRows, _nCols = 12, 4, 3
_camLayout = np.arange(_nCams).reshape(_nRows, _nCols)
_tblSzmm = (2000, 2000)
_vwrImgSz = (900, 900)
_px2mm = 0.17857 ## NEED TO CALCULATE "DE NOVO"
_mm2px = 1 /_px2mm
#_mm2px = 5.68
_tblImgSz = (int(_tblSzmm[0] *_mm2px), int(_tblSzmm[1] *_mm2px))
_rawImgSz = (4000, 3000)
_bffImgSz = (800, 600)
_bufferSz = 10 # 120	
_cellSzmm = 50
_bordermm = 5



''' CONFIGURATION PATHS '''
_expPth = '/home/bigtracker/tracking/runs' + os.sep
_calPth = '/home/bigtracker/tracking/cals' + os.sep



''' CAM WORKER FUNCTIONS '''
def wrkr_init(key, run, imgSz, bufferSz):
	global _Cam
	_Cam = Cam(key, run)

	_Cam.start()
	_Cam.homography(imgSz)
	_Cam.setBff(bufferSz, _rawImgSz)

	_Cam.imgWndw = _Cam.getCrop(_vwrImgSz, _camLayout)
	_Cam.imgSize = (_Cam.imgWndw[1] - _Cam.imgWndw[0],
					_Cam.imgWndw[3] - _Cam.imgWndw[2])

def wrkr_setRes(imgSz):
	sleep(.003)
	_Cam.homography(imgSz)
	return _Cam.key

def wrkr_adjust(imgSz, info):
	sleep(.003)
	_Cam.info = info[_Cam.key]
	_Cam.homography(imgSz)
	return _Cam.key

def wrkr_clrFrm(f):
	sleep(.003)
	return (_Cam.hCrop, _Cam.readBff(f=f, color=True))

def wrkr_getFrm(key):
	ok = _Cam.wrtBff()
	return (cv2.resize(_Cam.readBff(), _Cam.imgSize), _Cam.imgWndw)

def wrkr_stop(key):
	sleep(.003)
	_Cam.stop()
	return _Cam.key



''' CAM CLASS '''
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

		print('+++ Cam %02i %s, initialized' % (self.key, self.sn))

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
			return self.expPth + fname
		except:
			print('+++ Cam %02i %s, ' % (self.key, self.sn), end='')
			print('NO video file found !!!')

	def homography(self, imgSz=_tblImgSz):
		pts_src = np.array(self.info[3:7])  # tl, tr, bl, br

		w, h = int(self.info[7] * self.mm2px), int(self.info[8] * self.mm2px)
		pts_dst = np.array([[0, 0], [w, 0], [0, h], [w, h]], dtype='float64')

		xOff, yOff = int(self.info[1] * self.mm2px), int(self.info[2] * self.mm2px)
		pts_dst += np.array([xOff, yOff])

		# homography image-size factor
		hFctr = np.array([imgSz[0]/_tblImgSz[0], imgSz[1]/_tblImgSz[1]])
		pts_dst *= hFctr

		try:
			self.hMtx, status = cv2.findHomography(pts_src, pts_dst)
			self.hSize = imgSz
			self.hCrop = self.getCrop(self.hSize, _camLayout)
		except:
			print('+++ Cam %02i %s, ' % (self.key, self.sn), end='')
			print('Error in findHomography()')
			print(pts_src)
			print(pts_dst)

	def start(self):
		self.frame = -1
		try:
			self.vid = cv2.VideoCapture(self.fileName())
		except:
			print('+++ Cam %02i %s, ' % (self.key, self.sn), end='')
			print('Error starting Capture !!')

	def stop(self):
		if self.vid.isOpened(): self.vid.release()

	def getCrop(self, fullSz, layout):
		f, c = np.where(layout == self.key)[0][0], np.where(layout == self.key)[1][0]
		a = int(round(fullSz[0] / _nCols * c, 0))
		b = int(round(fullSz[0] / _nCols * (c + 1), 0))
		c = int(round(fullSz[1] / _nRows * f, 0))
		d = int(round(fullSz[1] / _nRows * (f + 1), 0))
		return (a, b, c, d)

	def setBff(self, bufferSz, bffImgSz):
		self.bufferSz, self.bffImgSz = bufferSz, bffImgSz
		self.iBuffer = [
			np.zeros((self.bffImgSz[1], self.bffImgSz[0])), 3] * self.bufferSz
		# self.iBuffer = [np.zeros((self.bffImgSz[1], self.bffImgSz[0]))] * self.bufferSz
		self.bffPntr = -1

	def readBff(self, f=0, color=False):
		bffPntr = (self.bffPntr - f) % self.bufferSz
		a, b, c, d = self.hCrop
		if not color:
			return cv2.warpPerspective(cv2.cvtColor(self.iBuffer[bffPntr], cv2.COLOR_BGR2GRAY), self.hMtx, self.hSize)[c:d, a:b]
		else:
			return cv2.warpPerspective(self.iBuffer[bffPntr], self.hMtx, self.hSize)[c:d, a:b, :]
		# return cv2.warpPerspective(self.iBuffer[bffPntr], self.hMtx, self.hSize)[c:d, a:b]



''' PREVIOUS CALIBRATION CLASS '''
class calRun():

	def __init__(self, exp, expPth, calPth):

		if exp[-1] != os.sep: exp += os.sep
		if not os.path.exists(expPth + exp):
			print ('Experiment not found !!')
			return

		self.exp = exp
		self.expPth = expPth + exp
		self.dtaPth = ''
		
		self.info = {}
		self.calFile = ''
		for calFile in sorted(os.listdir(calPth)):
			if calFile[:9] <= self.exp[:9]: self.calFile = calFile

		with open(calPth + self.calFile) as f:
			for key, val in json.load(f).items():
				self.info[int(key)] = val

		self.cArray = []
		self.tags = {}
		self.N = 0

	def __repr__(self):
		return '+++ Run %s\n' % self.expPth



''' CALIBRATION CLASS '''
class vTuner():

	def __init__(self, exp='20200310M', expPth=_expPth, calPth=_calPth):

		self.run = calRun(exp, expPth, calPth)
		if not self.run: return

		self.viewer = 'vPlayer'
		self.w, self.h = _vwrImgSz

		self.x2px, self.y2px = self.w / _tblSzmm[0], self.h/_tblSzmm[1]

		self.info = self.run.info
		self.newInfo = deepcopy(self.info)

		self.mm2px = 0.0
		if 99 in self.info.keys(): self.mm2px = self.info[99]

		self.started = False
		self.inited = False
		self.setRes(1)

		print('+++ step 1. run self.setmm2px() to set the pixels/mm ratio if necessary;')
		print('+++ step 2. run self.calCam(camkey) to calibrate cams one-by-one.')

	def start(self):
		self.pool = Pool(processes=_nCams)
		outQ = [self.pool.apply(wrkr_init, args=(
			k, self.run, self.imgSz, self.bufferSz)) for k in range(_nCams)]

		self.frame, self.started = -1, True

	def setRes(self, r):
		self.bffImgSz = (_bffImgSz[0] * r, _bffImgSz[1] * r)
		self.bufferSz = _bufferSz
		self.imgSz = (self.bffImgSz[0] * _nCols, self.bffImgSz[1] * _nRows)
		self.mrkSz = 4

		if self.started:
			outQ = self.pool.map(wrkr_setRes, [self.imgSz] * _nCams)
			if sum(outQ) != sum(range(_nCams)):
				print('+++ (_setRes) pool mapping error !!')

	def init(self):
		cv2.namedWindow(self.viewer, cv2.WINDOW_NORMAL)
		cv2.resizeWindow(self.viewer, self.w, self.h)
		cv2.moveWindow(self.viewer, 1750, 100)
		# img. numpy.shape is (h,w)
		self.img = np.zeros((self.h, self.w, 3), dtype='uint8')
		self.img[:, :, :] = 160

		self.frame += 1
		self.inited = True

		outQ = self.pool.map_async(wrkr_getFrm, range(_nCams)).get()
		for img, (a, b, c, d) in outQ:
			for q in [0, 1, 2]: self.img[c:d, a:b, q] = img

		self.strtImg = np.copy(self.img)

		cv2.imshow(self.viewer, self.img)
		cv2.waitKey(1)

	def stop(self):
		if self.started:
			outQ = self.pool.map(wrkr_stop, range(_nCams))
			self.pool.terminate()

		if self.inited:
			cv2.destroyWindow(self.viewer)

		self.frame = -1
		self.started, self.inited = False, False

	def camInfo(self, cam):
		print('+++ Cam%02d: ' % cam)
		print(' tl (%4d, %4d) ... tr (%4d, %4d)' % (
			self.newInfo[cam][3][0], self.newInfo[cam][3][1], self.newInfo[cam][4][0], self.newInfo[cam][4][1]))
		print(' bl (%4d, %4d) ... br (%4d, %4d)' % (
			self.newInfo[cam][5][0], self.newInfo[cam][5][1], self.newInfo[cam][6][0], self.newInfo[cam][6][1]))

	def setmm2px(self):
		'''
		This is the first necessary step:
		- ask for the x-coordinates of the top-left and top-right corners
		of one of the squares in the image.
		- knowing the size of a square (_cellSzmm = 50 mm), the pixels/mm ratio is:
			 (top-left -top-right) /_cellSzmm;
		'''

		# open Cam 0 (could be anyone, we assume all of them at the same height)
		_Cam = Cam(0, self.run)
		_Cam.vid = cv2.VideoCapture(_Cam.fileName())
		ok, frm = _Cam.vid.read()
		Image.fromarray(frm).show()

		print('+++ Enter reference coordinates to set the px/mm ratio:')
		print('(x-coordinates of the top-left and top-right corners of one of the squares)')

		xRefs = input('     x1, x2 :')
		xRefs = [int(pix) for pix in xRefs.split(',')]
		self.mm2px = (xRefs[1] - xRefs[0]) / _cellSzmm
		self.newInfo[99] = self.mm2px
		print(' +++ Current ratio : %6.4f px./mm ' % self.mm2px)

		for proc in psutil.process_iter():
			if proc.name() == "display":
				proc.kill()

		_Cam.vid.release()
		_Cam.stop()

	def focusCrop(self, fx, fy):
		a, b = int(fx -_vwrImgSz[0] /2), int(fx +_vwrImgSz[0] /2)
		c, d = int(fy -_vwrImgSz[1] /2), int(fy +_vwrImgSz[1] /2)
		if a < 0:
			a, b = 0, _vwrImgSz[0]
		elif b > self.imgSz[0]:
			a, b = self.imgSz[0] -_vwrImgSz[0], self.imgSz[0]
		if c < 0:
			c, d = 0, _vwrImgSz[1]
		elif d > self.imgSz[1]:
			c, d = self.imgSz[1] -_vwrImgSz[1], self.imgSz[1]
		return (a, b, c, d)

	def getCamInfo(self, key, frm):
		cellCols = ['A','B','C','D','E','F','G','H','I','J','K','L','M','N','O','P','Q','R','S','T']

		Image.fromarray(frm).show()
		srcCoords = np.zeros(8).reshape(4, 2)
		camRows, camCols = [], []

		for c, name in enumerate(['--- top-left', '--- top-rght', '--- btm-left', '--- btm-rght']):

			# reference Cell
			while True:
				refCell = input(name + ' Cell (xnn): ')
				if len(refCell) == 3 and refCell[0].isalpha() and refCell[1:].isnumeric(): break

			cellCol = cellCols.index(refCell[0].upper()) *2
			cellRow = (int(refCell[1:]) -1) *2
			camCols.append(cellCol)
			camRows.append(cellRow)

			# image corners' coordinates (pixels)
			while True:
				refCoords = input(name + ' (x, y) coords.: ')
				if all([x.strip(' ').isnumeric() for x in refCoords.split(',')]): break
			srcCoords[c] = refCoords.split(',')

		for proc in psutil.process_iter():
			if proc.name() == "display":
				proc.kill()

		info = []
		if camRows[0] != camRows[1]:
			print('+++ Calibration error, select top-cells from same row !')
		elif camRows[2] != camRows[3]:
			print('+++ Calibration error, select bottom-cells from same row !')
		elif camCols[0] != camCols[2]:
			print('+++ Calibration error, select left-cells from same col.!')
		elif camCols[1] != camCols[3]:
			print('+++ Calibration error, select right-cells from same col.!')
		else:
			# Cam offSet (mm)
			xOffSet = camCols[0] *_cellSzmm +_bordermm
			yOffSet = camRows[0] *_cellSzmm +_bordermm
			info = [int(xOffSet), int(yOffSet)]
			# image corners' coordinates (pixels)
			for c in range(4): info.append([int(p) for p in srcCoords[c]])
			# image reference-size (mm)
			xSize = (camCols[1] -camCols[0]) *_cellSzmm
			ySize = (camRows[2] -camRows[0]) *_cellSzmm
			info.append(int(xSize))
			info.append(int(ySize))

		return info

	def calCam(self, key):
		'''
		One-by-one calibration of the cams. New calibration parameters are saved in self.newInfo
		'''

		_Cam = Cam(key, self.run)
		self.newInfo[key].append(_Cam.sn)
		_Cam.vid = cv2.VideoCapture(_Cam.fileName())
		ok, frm = _Cam.vid.read()

		if ok:
			info = self.getCamInfo(key, frm)
			if len(info):
				if key in self.newInfo.keys():
					del self.newInfo[key]
				self.newInfo[key] = [_Cam.sn]
				for v in info:
					self.newInfo[key].append(v)
				self.newInfo[key].append(_Cam.fila)
				self.newInfo[key].append(_Cam.col)

		_Cam.vid.release()
		_Cam.stop()

	def refPattern(self, pattern = 1):
		''' +++ draw reference pattern '''

		x2px, y2px = self.imgSz[0] /_tblSzmm[0], self.imgSz[1] /_tblSzmm[1]

		if pattern == 1:
			# 1.lines
			w, h = 2 *(50 *cos(pi /6)), (50 + 50 *sin(pi /6))
			x0, y0 = self.info[0][1:3]
			x1, y1 = x0 + w* 22, y0 +h *26
			for l in range(28):
				p1 = (int(x0 *x2px), int((y0 +h *l) *y2px))
				p2 = (int(x1 *x2px), int((y0 +h *l) *y2px))
				cv2.line(self.img, p1, p2, (0, 0, 255), 1)
			for l in range(24):
				p1 = (int((x0 +w *l) *x2px), int(y0 *y2px))
				p2 = (int((x0 +w *l) *x2px), int(y1 *y2px))
				cv2.line(self.img, p1, p2, (0, 0, 255), 1)

		elif pattern == 2:
			# 2.hexagons
			w, h = 50 *cos(pi /6), 50 *(1 +sin(pi /6))
			y0 = self.info[0][2] -h
			for i in range(26):
				y0 += h
				if not i %2:
					x0 = self.info[0][1] -2 *w
				else:
					x0 = self.info[0][1] -w
				for j in range(22):
					x0 += 2 *w
					x1, y1 = x0 + 50 *cos(pi /6), y0 - 50 *sin(pi /6)
					x2, y2 = x0 +2 *w, y0
					x3, y3 = x0, y0 + 50
					cv2.line(self.img, (int(x0 *x2px), int(y0 *y2px)), (int(x1 *x2px), int(y1 *y2px)), (124, 0, 0), 1)
					cv2.line(self.img, (int(x1 *x2px), int(y1 *y2px)), (int(x2 *x2px), int(y2 *y2px)), (124, 0, 0), 1)
					cv2.line(self.img, (int(x0 *x2px), int(y0 *y2px)), (int(x3 *x2px), int(y3 *y2px)), (124, 0, 0), 1)

	def tune(self, pattern = 0):
		if not self.started: self.start()
		if not self.inited: self.init()

		cam, corner = -1, 0
		kAdjust = [113, 119, 101, 114, 116, 121, 117, 105, 97, 115, 100, 102, 103, 104, 106, 107]

		while True:

			self.img = np.zeros((self.imgSz[1], self.imgSz[0], 3), dtype = 'uint8')
			x2px, y2px = self.imgSz[0] /_tblSzmm[0], self.imgSz[1] /_tblSzmm[1]

			# +++ get frame image
			imgQ = self.pool.map_async(wrkr_clrFrm, [0] *_nCams).get()
			for (a, b, c, d), img in imgQ: self.img[c:d, a:b, :] = img

			self.refPattern(pattern = pattern)

			# +++ crop focus area
			if cam > -1:

				camInfo = self.info[cam]
				if not corner:
					xmm, ymm = camInfo[1] +camInfo[7] /2, camInfo[2] +camInfo[8] /2
				elif corner == 1:
					xmm, ymm = camInfo[1], camInfo[2]
				elif corner == 2:
					xmm, ymm = camInfo[1] +camInfo[7] /2, camInfo[2]
				elif corner == 3:
					xmm, ymm = camInfo[1] +camInfo[7], camInfo[2]
				elif corner == 4:
					xmm, ymm = camInfo[1] +camInfo[7], camInfo[2] +camInfo[8]
				elif corner == 5:
					xmm, ymm = camInfo[1] +camInfo[7] /2, camInfo[2] +camInfo[8]
				elif corner == 6:
					xmm, ymm = camInfo[1], camInfo[2] +camInfo[8]
				ctxt = ['c.', 'tl', 'tc', 'tr', 'br', 'bc', 'bl'][corner]

				cv2.putText(self.img, 'C%02d.%s' % (cam, ctxt), (int(xmm *x2px), int(ymm *y2px)), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 0), 1, cv2.LINE_AA)

				fx, fy = xmm *x2px, ymm *y2px
				a, b, c, d = self.focusCrop(fx, fy)
				cv2.imshow(self.viewer, self.img[c:d, a:b, :])
			else:
				cv2.imshow(self.viewer, self.img)

			wk = cv2.waitKey(0)
			if wk == 32:						# quit (spacebar)
				break
			elif wk in [186, 49, 50, 51, 52, 53, 54, 55, 56, 57, 48, 39]:
				cam = [186, 49, 50, 51, 52, 53, 54, 55, 56, 57, 48, 39].index(wk)
				self.camInfo(cam)
			elif wk == 99:						# focus on corner (c)
				corner = (corner +1) %7
			elif wk == 120:						# zoomIn (x)
				r = int(self.bffImgSz[0] / 800)
				if r < 4: self.setRes(r +1)
			elif wk == 122:						# zoomOut (z)
				r = int(self.bffImgSz[0] / 800)
				if r > 1: self.setRes(r -1)
				elif r == 1: cam = -1
			elif wk in kAdjust:
				if cam > -1:
					self.hAdjust(cam, wk)		# adjust homography
					self.hSet()
					self.camInfo(cam)

		self.setRes(1)
		self.stop()

	def hAdjust(self, cam, wk):
		tl, tr, bl, br = self.info[cam][3:7]
		# horizontal (x) adjustment
		if   wk == 113: self.info[cam][3] = (tl[0] -1, tl[1])	# q, move top-left left
		elif wk == 119: self.info[cam][3] = (tl[0] +1, tl[1])	# w, move top-left right
		elif wk == 101: self.info[cam][4] = (tr[0] -1, tr[1])	# e, move top-rght left
		elif wk == 114: self.info[cam][4] = (tr[0] +1, tr[1])	# r, move top-rght right
		elif wk == 116: self.info[cam][5] = (bl[0] -1, bl[1])	# t, move btm-left left
		elif wk == 121: self.info[cam][5] = (bl[0] +1, bl[1])	# y, move btm-left right
		elif wk == 117: self.info[cam][6] = (br[0] -1, br[1])	# u, move btm-right left
		elif wk == 105: self.info[cam][6] = (br[0] +1, br[1])	# i, move btm-right right
		# vertical (y) adjustment
		elif wk ==  97: self.info[cam][3] = (tl[0], tl[1] -1)	# a, move top-left down
		elif wk == 115: self.info[cam][3] = (tl[0], tl[1] +1)	# s, move top-left up
		elif wk == 100: self.info[cam][4] = (tr[0], tr[1] -1)	# d, move top-rght down
		elif wk == 102: self.info[cam][4] = (tr[0], tr[1] +1)	# f, move top-rght up
		elif wk == 103: self.info[cam][5] = (bl[0], bl[1] -1)	# g, move btm-left down
		elif wk == 104: self.info[cam][5] = (bl[0], bl[1] +1)	# h, move btm-left up
		elif wk == 106: self.info[cam][6] = (br[0], br[1] -1)	# j, move btm-rght down
		elif wk == 107: self.info[cam][6] = (br[0], br[1] +1)	# k, move btm-rght up

	def calSet(self):
		outQ = [self.pool.apply(wrkr_adjust, args = (self.imgSz, self.info)) for k in range(_nCams)]
		if sum(outQ) != sum(range(_nCams)):
			print('+++ (_adjust) pool mapping error !!')

	def calSave(self, cal):
		if cal:
			with open(_calPth + '%s.json' % cal , 'w') as f: json.dump(self.info, f)
			print('+++ saved %s' % (_calPth + '%s.json' % cal))

	def newCalSave(self, cal):
		self.newInfo[99] = self.mm2px
		self.info = self.newInfo
		self.calSave(cal)
