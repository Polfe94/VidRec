
import os
from math import sqrt
import operator
import numpy as np
import cv2
from time import sleep
import json

from multiprocessing import Pool

# Att !!!
# pool.map() and pool.apply(), either in its _sync or _async version,
# present a potential risk of mapping the objective (worker) function
# several times to the same process in the pool, (instead of mapping
# the function respectively to each one and single process), particularly
# when the objective function is too fast, as it is the case here
# (thus we can have two times data from the same cam !!).
# I avoid this by adding a sleep() time to the worker functions ... :(
# but still a potential risk exists !!!

# for _async version method .get() ensures that code execution stops
# until the mapping result queue is ready (outQ.ready())
# example: outQ = self.pool.map_async(fvs.wrkr_getDta, [f] *_nCams).get()

from Ants18S import _expPth, _dtaPth, _aviPth, _expLst
from Ants18S import _nCams, _camLayout, _nCols, _nRows, _fRate
from Ants18S import _tblSzmm, _tblImgSz, _trkImgSz
from Ants18S import _rawImgSz, _bffImgSz, _bufferSz, _imgSz, _vwrImgSz
from Ants18S import _nest, _nestBound0, _nestBound1, _nestBound2
from Ants18S import _threshold2
from Ants18C import Ant, Loc, trkLoc

from cRun import Run
import vCams as fvs

# id's review
from scipy.spatial.distance import cdist

# fraction of neighbouring cams for zoom-cam view
_zb = 0.05
_zoomBrdr = (_zb, (8 *_zb +1) /6)	# don't change this !!

class vMachine():

	'''
	def __init__(self, exp = '20180726T', expPth = _expPth, dtaPth = _dtaPth)
	'''

	def start(self):

		self.pool = Pool(processes = _nCams)
		outQ = [self.pool.apply(fvs.wrkr_init, args = (k, self.run, self.imgSz, self.bufferSz)) for k in range(_nCams)]

		self.frame, self.started = -1, True

	def setRes(self, r):

		self.bffImgSz = (_bffImgSz[0] *r, _bffImgSz[1] *r)
		self.bufferSz = _bufferSz
		self.imgSz = (self.bffImgSz[0] *_nCols, self.bffImgSz[1] *_nRows)
		self.mrkSz = 4

		if self.started:
			outQ = self.pool.map(fvs.wrkr_setRes, [self.imgSz] *_nCams)
			if sum(outQ) != sum(range(_nCams)):
				print('+++ (_setRes) pool mapping error !!')

	def evTime(self, at = 0, show = True):

		if not self.started: return

		check = 0
		while check < 10:
			outQ = self.pool.map(fvs.wrkr_evTime, [at] *_nCams)
			if len(set([key for key, f in outQ])) == _nCams: break
			check += 1
		if check == 10:	print('+++ (_evTime) pool mapping error !!')

		if show:
			# show first/last outBound() event times
			for key, f in outQ:
				print('Cam%02d ... %s' % (key, fvs.f2t(f)))
		else:
			# return first/last frame
			if at == 0:
				return min([f for key, f in outQ])
			elif at == -1:
				return max([f for key, f in outQ])

	def tScore(self, frame, bounds = False, id = None):

		if id == None:
			cv2.rectangle(self.img, (0, 0), (145, 30), (160, 160, 160), -1)
			cv2.putText(self.img, fvs.f2t(frame), (5, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (210, 210, 210), 1, cv2.LINE_AA)
		else:
			cv2.rectangle(self.img, (0, 0), (250, 30), (160, 160, 160), -1)
			cv2.putText(self.img, fvs.f2t(frame), (5, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (210, 210, 210), 1, cv2.LINE_AA)
			cv2.putText(self.img, 'id.%03d' % id, (155, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (210, 210, 210), 1, cv2.LINE_AA)

		if bounds:
			center = int(_nest[0] *self.x2px), int(_nest[1] *self.y2px)
			hAx, vAx = int(_nestBound0 *self.x2px), int(_nestBound0 *self.x2px)
			cv2.ellipse(self.img, center, (hAx, vAx), 0, 0, 360, (255, 255, 255), 2)
			hAx, vAx = int(_nestBound1 *self.x2px), int(_nestBound1 *self.x2px)
			cv2.ellipse(self.img, center, (hAx, vAx), 0, 0, 360, (255, 255, 255), 2)
			hAx, vAx = int(_nestBound2 *self.x2px), int(_nestBound2 *self.x2px)
			cv2.ellipse(self.img, center, (hAx, vAx), 0, 0, 360, (255, 255, 255), 2)

	def init(self):

		cv2.namedWindow(self.viewer, cv2.WINDOW_NORMAL)
		cv2.resizeWindow(self.viewer, self.w, self.h)
		cv2.moveWindow(self.viewer, 1750, 100)
		self.img = np.zeros((self.h, self.w, 3), dtype = 'uint8')	# img. numpy.shape is (h,w)
		self.img[:, :, :] = 160

		self.frame += 1
		self.inited = True

		outQ = self.pool.map_async(fvs.wrkr_getFrm, range(_nCams)).get()
		for img, (a, b, c, d) in outQ:
			for q in [0, 1, 2]: self.img[c:d, a:b, q] = img

		self.strtImg = np.copy(self.img)

		self.tScore(self.frame, bounds = True)
		cv2.imshow(self.viewer, self.img)
		cv2.waitKey(1)

	def ffwd(self, t):

		if not self.started: self.start()
		if not self.inited: self.init()

		outQ = [self.pool.apply_async(fvs.wrkr_ffwd, args = (fvs.t2s(t[:8]), self.bufferSz)) for k in range(_nCams)]
		i = 0
		while not all([q.ready() for q in outQ]):
			if not i: print(' ' *20, end = '\r')
			print('   ' + ' ' *i + '>>>', end = '\r')
			i += 1
			i %= 14
			sleep(.10)

		frame = [q.get() for q in outQ]
		if len(set(frame)) != 1:
			print('+++ Cam synchro error ')

		imgQ = self.pool.map_async(fvs.wrkr_getFrm, range(_nCams)).get()
		for img, (a, b, c, d) in imgQ:
			for q in [0, 1, 2]: self.img[c:d, a:b, q] = img

		self.frame = frame[0]
		self.tScore(self.frame, bounds = True)
		cv2.imshow(self.viewer, self.img)
		cv2.waitKey(1)

	def play(self, rec = False, raw = True):

		if not self.started: self.start()
		if not self.inited: self.init()
		if not raw:
			# show tracking positions
			self.run.readTags()

		while True:

			outQ = self.pool.map(fvs.wrkr_getFrm, range(_nCams))
			# outQ = self.pool.map_async(fvs.wrkr_getFrm, range(_nCams)).get()
			for img, (a, b, c, d) in outQ:
				for q in [0, 1, 2]: self.img[c:d, a:b, q] = img
			self.frame += 1
			self.tScore(self.frame, bounds = True)

			if not raw:
				for id in [id for id in self.run.tags.values() if id.isOut(at = self.frame)]:
					l, xmm, ymm, z = id.get(at = self.frame)
					cv2.circle(self.img, (int(xmm *self.x2px), int(ymm *self.y2px)), 9, id.color, 2)

			cv2.imshow(self.viewer, self.img)
			if cv2.waitKey(1) == 32: break

			if rec: self.videoRec.write(self.img)

	def stop(self):

		if self.started:
			outQ = self.pool.map(fvs.wrkr_stop, range(_nCams))
			self.pool.terminate()

		if self.inited:
			cv2.destroyWindow(self.viewer)

		self.frame = -1
		self.started, self.inited = False, False

	def camCrop(self, cam):
		# +++ zoom cam centered image from full-size buffered image
		brdW, brdH = int(_zoomBrdr[0] *self.bffImgSz[0]), int(_zoomBrdr[1] *self.bffImgSz[1])
		row, col = np.where(_camLayout == cam)[0][0], np.where(_camLayout == cam)[1][0]
		x, y = self.bffImgSz[0] *(col +.5), self.bffImgSz[1] *(row +.5)
		a = int(x -self.bffImgSz[0] /2 -brdW)
		b = int(x +self.bffImgSz[0] /2 +brdW)
		c = int(y -self.bffImgSz[1] /2 -brdH)
		d = int(y +self.bffImgSz[1] /2 +brdH)
		if col == 0:
			a, b = 0, b +brdW
		elif col == _camLayout.shape[1] -1:
			a, b = a -brdW, self.bffImgSz[0] *_nCols
		if row == 0:
			c, d = 0, d +brdH
		elif row == _camLayout.shape[0] -1:
			c, d = c -brdH, self.bffImgSz[1] *_nRows
		return (a, b, c, d)

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

	def replay(self, last = 30, cam = -1, focus = (), waitTime = 100, rec = False):

		if not self.started or not self.inited: return

		# buffer image
		bffImg = np.zeros((self.imgSz[1], self.imgSz[0], 3), dtype = 'uint8')
		x2px, y2px = self.imgSz[0] /_tblSzmm[0], self.imgSz[1] /_tblSzmm[1]

		last = min(last *2, self.bufferSz)
		frame = (self.frame -last) -1

		for bffbck in range(last, 0, -1):
			imgQ = self.pool.map_async(fvs.wrkr_bffFrm, [bffbck] *_nCams).get()
			for (a, b, c, d), img in imgQ:
				# colour image conversion
				for q in [0, 1, 2]: bffImg[c:d, a:b, q] = img

			# +++ get current positions
			frame += 1
			idsOut = [(iid, ind.get(at = frame)) for iid, ind in self.run.tags.items() if ind.isOut(at = frame)]

			if len(self.run.tags):
				# +++ show tracking positions
				if len(focus):
					for id, pos in idsOut:
						(t, xmm, ymm), clr = pos, self.run.tags[id].color
						cv2.circle(bffImg, (int(xmm *x2px), int(ymm *y2px)), self.mrkSz, clr, -1)
					a, b, c, d = self.focusCrop(focus[0] *x2px, focus[1] *y2px)
					self.img = bffImg[c:d, a:b, :]
				elif cam != -1:
					for id, pos in idsOut:
						(t, xmm, ymm), clr = pos, self.run.tags[id].color
						cv2.circle(bffImg, (int(xmm *x2px), int(ymm *y2px)), 18, clr, 4)
					a, b, c, d = self.camCrop(cam)
					self.img = cv2.resize(bffImg[c:d, a:b, :], _vwrImgSz)
				else:
					for id, pos in idsOut:
						(t, xmm, ymm), clr = pos, self.run.tags[id].color
						cv2.circle(bffImg, (int(xmm *x2px), int(ymm *y2px)), 36, clr, 8)
					self.img = cv2.resize(bffImg, _vwrImgSz)

			self.tScore(frame, bounds = False)
			cv2.imshow(self.viewer, self.img)
			if cv2.waitKey(waitTime) == 32: break

			if rec: self.videoRec.write(self.img)

	def review(self, t = '', maxf = 1800):

		if not self.started: self.start()
		if not self.inited: self.init()

		if not len(t):
			if self.frame == -1:
				ffwd = self.bufferSz
			elif self.frame < self.bufferSz:
				ffwd = int(self.bufferSz - self.frame)
			else:
				ffwd = 0
		else:
			self.ffwd(fvs.f2t(fvs.t2s(t) *_fRate -int(self.bufferSz /2)))
			ffwd = self.bufferSz

		for f in range(ffwd):
			outQ = self.pool.map_async(fvs.wrkr_wrtBff, range(_nCams)).get()
			if sum(outQ) != sum(range(_nCams)):
				print()
				print('+++ (_wrtBff) pool mapping error !!')
				return
			self.frame += 1
			print('+++ buffering ... frame %06d t = %s' % (self.frame, fvs.f2t(self.frame)), end = '\r')
		if ffwd: print()

		self.stopRvw, count = False, 0
		while not self.stopRvw and count < maxf:

			outQ = self.pool.map_async(fvs.wrkr_wrtBff, range(_nCams)).get()
			if sum(outQ) != sum(range(_nCams)):
				print('+++ (_wrtBff) pool mapping error !!')
				return
			self.frame += 1

			rvwfrm = self.frame -int(self.bufferSz /2)
			while True:
				_rvwfrm = Rvwfrm(rvwfrm, self)
				if _rvwfrm.done:
					self.run.tags = _rvwfrm.tags
					break
			count += 1

		print()
		if input('+++ save changes ???') == 'y': self.wrtTags()


# +++ Frame Review class

class Rvwfrm():

	def __init__(self, rvwfrm, _vPlayer):

		if _vPlayer.frame - rvwfrm > _vPlayer.bufferSz:
			print('+++ Out of buffer length !!')
			return

		self.v = _vPlayer
		self.tags = _vPlayer.run.tags

		self.rvwfrm, self.frame = rvwfrm, rvwfrm

		self.mrkSz = 4
		self.done = True
		self.back = {}
		self.review()

	def review(self):

		print('+++ rvwfrm %06d t = %s' % (self.frame, fvs.f2t(self.frame)), end = '\r')

		self.idsOut = [ind for ind in self.run.tags.values() if ind.isOut(at = self.rvwfrm)]
		if len(self.idsOut) > 1:

			# save self.tags copy to undo
			for id, ind in self.tags.items(): self.back[id] = ind

			cv2.setMouseCallback(self.v.viewer, self.mouseCallBack, True)

			chkPos = [ind.get(at = self.rvwfrm)[1:] for ind in self.idsOut]
			chkDst = np.sqrt(cdist(np.array(chkPos), np.array(chkPos)))

			for i, ind in enumerate(self.idsOut):
				# if np.any(chkDst[i, i+1:] < _threshold2) or ind.toNest(at = self.rvwfrm):
				if np.any(chkDst[i, i+1:] < _threshold2):
					if ind.reviewed == self.rvwfrm -1:
						ind.reviewed = self.rvwfrm
					else:
						self.kId, self.frame = ind, self.rvwfrm
						self.show()
						if not self.done or self.v.stopRvw: break

			cv2.setMouseCallback(self.v.viewer, self.mouseCallBack, False)

	def tScore(self, frame):

		txt = fvs.f2t(self.rvwfrm)
		if self.frame >= self.rvwfrm :
			txt += ' +%02d' % (self.frame - self.rvwfrm)
		elif self.frame < self.rvwfrm:
			txt += ' -%02d' % (self.rvwfrm - self.frame)

		cv2.rectangle(self.v.img, (0, 0), (210, 30), (160, 160, 160), -1)
		cv2.putText(self.v.img, txt, (5, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (210, 210, 210), 1, cv2.LINE_AA)

	def mouseCallBack(self, event, x, y, flags, set):

		if set and event == cv2.EVENT_LBUTTONDOWN:

			self.bffImg = np.copy(self.iCopy)

			a, b, c, d = self.v.focusCrop(self.fx, self.fy)
			xEv, yEv = (x +a) *_tblSzmm[0] /self.v.imgSz[0], (y +c) *_tblSzmm[1] /self.v.imgSz[1]

			dst2Ev = []
			for ind in [ind for ind in self.tags.values() if ind.isOut(at = self.frame)]:
				t, xmm, ymm = ind.get(at = self.frame)
				dst2Ev.append((ind, sqrt((xmm -xEv)**2 + (ymm -yEv)**2)))

			dst2Ev.sort(key = operator.itemgetter(1))
			if dst2Ev[0][1] < 10:

				ind = dst2Ev[0][0]
				t, xmm, ymm = ind.get(at = self.frame)
				cv2.circle(self.bffImg, (int(xmm *self.x2px), int(ymm *self.y2px)), self.mrkSz, self.kId.color, -1)

				a, b, c, d = self.v.focusCrop(self.fx, self.fy)
				self.v.img = self.bffImg[c:d, a:b, :]

				self.tScore(self.frame)
				cv2.imshow(self.v.viewer, self.v.img)

				self.rstIds(ind)

	def show(self):

		t, self.xmm, self.ymm = self.kId.get(at = self.rvwfrm)

		while True:

			# focus viewing window (depending on current zoom)
			self.x2px, self.y2px = self.v.imgSz[0] /_tblSzmm[0], self.v.imgSz[1] /_tblSzmm[1]
			self.fx, self.fy = self.xmm *self.x2px, self.ymm *self.y2px
			# buffer image (depending on current zoom)
			self.bffImg = np.zeros((self.v.imgSz[1], self.v.imgSz[0], 3), dtype = 'uint8')

			# +++ get frame image
			bffbck = self.v.frame - self.frame
			imgQ = self.v.pool.map_async(fvs.wrkr_bffFrm, [bffbck] *_nCams).get()
			for (a, b, c, d), img in imgQ:
				# colour image conversion
				for q in [0, 1, 2]: self.bffImg[c:d, a:b, q] = img

			# +++ get copy of image without mark
			self.iCopy = np.copy(self.bffImg)

			# +++ show kId current position
			for ind in self.idsOut:
				t, xmm, ymm = ind.get(at = self.frame)
				color = self.kId.color if ind == self.kId else (220, 220, 220)
				cv2.circle(self.bffImg, (int(xmm *self.x2px), int(ymm *self.y2px)), self.mrkSz, color, -1)

			# +++ crop focus area
			a, b, c, d = self.v.focusCrop(self.fx, self.fy)
			self.v.img = self.bffImg[c:d, a:b, :]

			self.tScore(self.frame)
			cv2.imshow(self.v.viewer, self.v.img)
			wk = cv2.waitKey(0)

			if wk == 32 or wk == 110:			# next (n, spacebar)
				break
			elif wk == 114:						# reset (r)
				if len(self.back):
					for id, ind in self.back.items(): self.tags[id] = ind
				self.done = False
				break
			elif wk == 115:						# stop reviewing (s)
				self.v.stopRvw = True
				break
			elif wk == 111:						# frame backward (o)
				if (self.rvwfrm -self.frame) < self.v.bufferSz /2:
					self.frame -= 1
			elif wk == 112:						# frame forward (p)
				if (self.frame -self.rvwfrm) < self.v.bufferSz /2:
					self.frame += 1
			elif wk == 113:						# marksize smaller (q)
				self.mrkSz -= 1
			elif wk == 119:						# marksize larger (w)
				self.mrkSz += 1
			elif wk == 120:						# zoomIn (x)
				r = int(self.v.bffImgSz[0] / 800)
				if r < 4: self.v.setRes(r +1)
			elif wk == 122:						# zoomOut (z)
				r = int(self.v.bffImgSz[0] / 800)
				if r > 1: self.v.setRes(r -1)
			else:
				pass

	def rstIds(self, ind):

		if self.frame >= self.rvwfrm:

			if self.kId != ind:

				iL = [(f, x, y) for (f, x, y) in ind.track if f < self.frame]
				iR = [(f, x, y) for (f, x, y) in ind.track if f >= self.frame]

				jL = [(f, x, y) for (f, x, y) in self.kId.track if f < self.frame]
				jR = [(f, x, y) for (f, x, y) in self.kId.track if f >= self.frame]

				ind.track = iL + jR
				self.kId.track = jL + iR

			self.kId.reviewed = self.rvwfrm
			ind.reviewed = self.rvwfrm

		else:

			if self.kId != ind:

				if input('+++ rvwfrm %06d t = %s ... %3d merge to %3d ?' % (self.rvwfrm, fvs.f2t(self.rvwfrm), self.kId.id, ind.id)) == 'y':

					ind.track += self.kId.track
					self.tags.pop(self.kId.id)

					self.kId.reviewed = self.rvwfrm
					ind.reviewed = self.rvwfrm

			else:

				newkId = len(self.tags.keys())
				if input('+++ rvwfrm %06d t = %s ... %3d split to %3d (new)?' % (self.rvwfrm, fvs.f2t(self.rvwfrm), ind.id, newkId)) == 'y':

					iL = [(f, x, y) for (f, x, y) in ind.track if f < self.rvwfrm]
					jR = [(f, x, y) for (f, x, y) in self.kId.track if f >= self.rvwfrm]

					ind.track = iL
					ind.set(self.rvwfrm, _nest)

					self.tags[newkId] = Ant(newkid)
					self.tags[newkId].track = jR

					ind.reviewed = self.rvwfrm
					self.tags[newkId].reviewed = self.rvwfrm
