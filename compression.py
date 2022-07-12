import os
import numpy as np
import cv2
from vidgear.gears import WriteGear

folder = '/home/bigtracker/VidRec/'

filelist = os.listdir(folder)
videolist = list(filter(lambda x: '.avi' in x, filelist))

if len(videolist) == 36:
    
    output_params = {'-vcodec': 'libx264', '-crf': 20, '-preset': 'veryslow'}
    
    for i in range(0, 36, 3):
        vids = [cv2.VideoCapture(source = folder + n) for n in videolist[i:(i+3)]]
        # output_params['-input_framerate'] = vids[0].framerate
        
        writer = WriteGear(output_filename= 'output_%s.mp4' % str((i//3)), **output_params)
        
        while True:
            
            pieces = [vid.read()[1] for vid in vids]
            
            try:
                frame = np.concatenate(pieces, axis = 0)
                
            except:
                break
            
            writer.write(frame, rgb_mode=False)
            
        del vids
            
        writer.close()