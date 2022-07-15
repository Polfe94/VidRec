'''CONFIG'''
vidPath = '/home/bigtracker/'
vidRes = (4000, 3000) # output video resolution 
vidName = 'test'

''' DEFAULT CAMERA PARAMETERS '''

# Note: this parameters were set with minimal camera aperture
exposure = 15.0 # 40
gain = 2.0 # 10.0 # 5.0
mode = 'BW' # black and white recording
resize = 1 # factor (0 to 1) to resize output image (i.e. 0.5 * (4000, 3000) = (2000, 1500))

# white balance values // ignored
# _balanceRed = 2.2799999713897705 # celegans
# _balanceBlue = 1.1799999475479126 # celegans


''' CAMERA ARRAY SERIAL NUMBERS '''
# Note: top left is the nearest cam to the lab door

# keys = cam order (top-left to bottom-right)
# values = serial numbers
CamArray = {
    0: '17215390',
    1: '17215425',
    2: '17179428',
    3: '17215392',
    4: '17179427',
    5: '17215383',# 5: '17215395',
    6: '17215394',
    7: '17215423',
    8: '17215421',
    9: '17215382',
    10: '17215420',
    11: '17215424'
}
