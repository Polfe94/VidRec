
from math import sqrt
import numpy as np
import cv2

from Ants18S import _fRate, _threshold2
from Ants18S import f2t, t2s

class vWatcher():

	'''
	def __init__(self, exp = '20180726T', expPth = _expPth, dtaPth = _dtaPth)
	'''

	def watch(self, t = '00:00:00', showIds = True, rec = False):

		if not self.started: self.start()
		if not self.inited:	self.init()
		if not len(self.run.tags): self.run.readTags()

		frame, lastf = t2s(t) *_fRate, self.evTime(at = -1, show = False)

		mSize = [5] + [3] *5 + [2] *5
		mFill = [-1] + [1] *10

		wtime, xtime = 2, 2
		while frame < lastf:
			self.img = np.copy(self.strtImg)
			frame += 1
			self.tScore(frame, bounds = True)
			for _Ant in self.run.tags.values():
				for i, (xmm, ymm) in enumerate(_Ant.trace(at = frame)):
					cv2.circle(self.img, (int(xmm *self.x2px), int(ymm *self.y2px)), mSize[i], _Ant.color, mFill[i])
					if i == 0 and showIds:
						cv2.putText(self.img, '%04d' % _Ant.id, (int(xmm *self.x2px), int(ymm *self.y2px)), cv2.FONT_HERSHEY_SIMPLEX, 0.3, (0, 0, 0), 1, cv2.LINE_AA)
			cv2.imshow(self.viewer, self.img)
			wk = cv2.waitKey(int(wtime *xtime))
			if wk == 32:			# pause/restart (spacebar)
				if wtime == 0:
					wtime = 2
				else:
					wtime = 0
			elif wk == 111:			# decrease speed (o)
				xtime *= 2
			elif wk == 112:			# increase speed (p)
				if xtime > 4: xtime /= 2
			elif wk == 115:			# stop watching (s)
				break

			if rec: self.videoRec.write(self.img)

	def wtrack(self, startId = 0, Id = None):

		if not self.started: self.start()
		if not self.inited:	self.init()
		if not len(self.run.tags): self.run.readTags()

		# crossing dictionary
		xDict = self.run.xDict()

		mSize = [5] + [3] *5 + [2] *5
		mFill = [-1] + [1] *10

		wtime = 1
		if Id != None:
			keyLst = [Id]
		else:
			keyLst = sorted(self.run.tags.keys())

		for id in keyLst:

			if id < startId: continue
			_Ant = self.run.tags[id]
			_Ant.trckInfo()

			# show _Ant track
			frame = _Ant.track[0][0] -1
			while frame < _Ant.track[-1][0] +10:

				self.img = np.copy(self.strtImg)
				frame += 1
				self.tScore(frame, bounds = True, id = id)

				# check crossing _Ants in following -30:+30 frames
				xAntQ = []
				for xframe in range(frame-30, frame +30):
					if xframe in xDict.keys():
						x1, y1 = _Ant.lastXY(at = xframe)
						for xId, (x2, y2) in xDict[xframe]:
							if xId != id and xId not in xAntQ and sqrt((x2 -x1)**2 +(y2 -y1)**2) < _threshold2:
								xAntQ.append(xId)

				# trace crossing _Ants if any
				for xId in xAntQ:
					xAnt = self.run.tags[xId]
					for i, (xmm, ymm) in enumerate(xAnt.trace(at = frame)):
						cv2.circle(self.img, (int(xmm *self.x2px), int(ymm *self.y2px)), mSize[i], xAnt.color, mFill[i])

				# trace _Ant
				for i, (xmm, ymm) in enumerate(_Ant.trace(at = frame)):
					cv2.circle(self.img, (int(xmm *self.x2px), int(ymm *self.y2px)), mSize[i], _Ant.color, mFill[i])

				cv2.imshow(self.viewer, self.img)
				wk = cv2.waitKey(wtime)
				if wk == 32:			# pause/restart (spacebar)
					if wtime == 0:
						wtime = 1
					else:
						wtime = 0
				elif wk == 110:			# next (n)
					break
				elif wk == 115:			# stop watching (s)
					break

			if wk == 115: break
