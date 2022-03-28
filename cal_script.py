import sys
import json
from copy import deepcopy
sys.path.append('/home/bigtracker/VidRec')

import calibration

# '20220321Tt'
# cal_obj = open('/home/bigtracker/tracking/calibration/2022/20220324M.json')
cal_obj = open('/home/bigtracker/tracking/cals/patates_braves.json')
cal = json.load(cal_obj)

obj = calibration.vTuner('20220321T', expPth = '/home/bigtracker/tracking/calibration/2022/')
obj.mm2px = 5.35

obj.info = deepcopy(cal)
obj.info[99] = obj.mm2px

# replace string keys with integer keys
for i in list(obj.info.keys()):
    obj.info[int(i)] = obj.info.pop(i)

obj.newInfo = obj.info

obj.tune(0)