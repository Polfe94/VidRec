import os
import json

# +++ Experiment class:

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
