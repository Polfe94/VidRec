
class MultiCam:

    def __init__(self, cam_list, method = 'contiuous'):

        # cam serial numbers / indices
        self.cams = cam_list

        # camera instances filled by PySpin methods
        self.cam_list = []

        # Queues
        self.q = []
        self.vidQ = []

        self.system = PySpin.System.GetInstance()
        self.available_cams = self.system.GetCameras()
        self.nodemap = []
        self.ptrHandling = []

        '''Implementation of different recording methods'''
        if method == 'scheduled':
            self.record = self.scheduled_recording
        else:
            self.record = self.continuous_recording


    # initializes selected cameras
    def init_cameras(self):

        for i in range(len(self.cams)):
            self.cam_list.append(self.available_cams.GetBySerial(self.cams[i]))
            self.cam_list[i].Init()

            # pointers and camera configuration
            self.nodemap.append(self.cam_list[i].GetNodeMap())
            TLS_device = self.cam_list[i].GetTLStreamNodeMap()
            ptr = PySpin.CEnumerationPtr(TLS_device.GetNode("StreamBufferHandlingMode"))
            ptr_mode = ptr.GetEntryByName("NewestOnly")
            ptr.SetIntValue(ptr_mode.GetValue())
            self.cam_list[i].AcquisitionMode.SetValue(PySpin.AcquisitionMode_Continuous)


            try:
                if self.cam_list[i].PixelFormat.GetAccessMode() == PySpin.RW:
                    self.cam_list[i].PixelFormat.SetValue(PySpin.PixelColorFilter_BayerBG)
            
            except:
                print("Could not change Pixel Format mode")
                return False

            try:
                self.cam_list[i].ExposureAuto.SetValue(PySpin.ExposureAuto_Off)
            
            except:
                print("Could not disable automatic exposure")
                return False

            try:
                self.cam_list[i].GainAuto.SetValue(PySpin.GainAuto_Off)

            except:
                print("Could not disable automatic gain")
                return False

            '''
            # white balance control
            self.cam_list[i].BalanceWhiteAuto.SetValue(PySpin.BalanceWhiteAuto_Off, False)
            balanceRatio = PySpin.CFloatPtr(self.nodemap[i].GetNode("BalanceRatio"))
            self.cam_list[i].BalanceRatioSelector.SetValue(PySpin.BalanceRatioSelector_Blue)
            balanceRatio.SetValue(_balanceBlue, False)
            self.cam_list[i].BalanceRatioSelector.SetValue(PySpin.BalanceRatioSelector_Red)
            balanceRatio.SetValue(_balanceRed, False)
            '''

 
    # initializes the camera threads
    def init_threads(self):

        for i in range(len(self.cams)):
            self.q.append(Queue(1))
    

    ''' CAMERA CONTROL (EXPOSURE AND GAIN) '''
    # method for setting camera exposure time
    def setExp(self, exposure):

        try:
            exposure = min(self.cam.ExposureTime.GetMax(),(exposure *1000))
            if exposure < 20:
                exposure = 20
            self.cam.ExposureTime.SetValue(exposure)
        except PySpin.SpinnakerException as ex:
            print("Error: %s" % ex.what())

    
    # method for setting camera gain
    def setGain(self,gain):

        try:
            gain = min(self.cam.Gain.GetMax(),gain)
            self.cam.Gain.SetValue(gain)
        except PySpin.SpinnakerException as ex:
            print("Error: %s" % ex.what())

    def start(self):

        self.startTime = time.time()
        self.frame = 0

        for i in range(len(self.cam_list)):
            self.cam_list[i].BeginAcquisition()


        # ¿?¿?¿?
        # start a thread to read frames from the file video stream
        t = Thread(target = self.update, args = ())
        t.daemon = True
        t.start()

        return self

    def stop(self):

        for i in range(len(self.cam_list)):
            self.cam_list[i].EndAcquisition()

        '''
        self.cam_list.Clear()
        self.system.ReleaseInstance()
        del self.cam_list
        '''

    def getImg(self):


    def update(self):
                    
        frm = self.frmGet()
        elapseTime = time.time() -self.startTime
        

        if self.trackerQ.full(): self.trackerQ.get()
        self.trackerQ.put(blobCenter)

        if self.mainQ.full(): self.mainQ.get()
        self.mainQ.put((elapseTime, frm, blobContour, contour, centroid, self.currX, self.currY, self.currZ))
        
        if self.vWriterQ.full(): self.vWriterQ.get()
        self.vWriterQ.put((elapseTime, frm, self.frmNmb, contour, centroid, self.currX, self.currY))
        
        if self.dWriterQ.full(): self.dWriterQ.get()
        self.dWriterQ.put((elapseTime, self.frmNmb, contour, centroid, self.currX, self.currY))
        
        self.frameRate()
   
   ''' CLASS RUN '''
   def launchCapEvent(self,evt):
        self.StopCameras(evt)
        time.sleep(1)
        startCapEv = Thread ( target=self.captureEvent,args=())
        startCapEv.start()
        evt.Skip()
        return

    def captureEvent(self):
            
            for i in range(len(AcoCAMArray.cameras)):
                AcoCAMArray.cameras[i].CamPreview = False

            timeBetEvents = int(self.txtTimebetEvents.GetValue())
            secondsPerEvents = int(self.txtsecondsPerEvents.GetValue())
            
            
            self.nEvents =int(self.txtnEvents.GetValue()) 
            
            iniTime = time.time()
            MaxTime = iniTime+(self.nEvents*(timeBetEvents+secondsPerEvents))
            
            actCaptime =time.time()
            nEventsCpt = 1
            
            config= str(iniTime)+'\n'+self.txtnEvents.GetValue()+'\n'+self.txtTimebetEvents.GetValue()+'\n'+self.txtsecondsPerEvents.GetValue()                         
            with open (self.folderA+'configExp.txt','a') as file_object: #FX : EL ARXIU DE SORTIDA ES GUARDA EN LA MATEIXA CARPETA ON SON LES IMATGES A TRACTAR
                file_object.write(config)
            
            for t in range(self.nEvents):
                self.saveTh(secondsPerEvents)
                sleep(timeBetEvents)
            
            #self.saveTh(secondsPerEvents)
            '''
            while(actCaptime<MaxTime):
                if (actCaptime>=(self.nEvents*timeBetEvents+iniTime)):
                    print('inicio captura event num=',nEventsCpt)
                    self.saveTh(secondsPerEvents)
                    nEventsCpt += 1
                    if(self.EXIT):
                        break                
                actCaptime =time.time()
            '''
                
            print('FINAL captureEvent')
            self.botStartEventCapt.SetBackgroundColour((0,255,0))

    def SaveIMG(self,evt):
            
        for i in range(len(AcoCAMArray.cameras)):
            AcoCAMArray.cameras[i].CamPreview = False

        Thread(target=self.saveTh,args=(self.nSec.GetValue(),)).start()
       
        evt.Skip()
        return
    

    def saveTh(self,secondsToCapture):
        
        print('Entro saveTh')
                
        iniCaptime = time.time()
        t2Cap = int(secondsToCapture)
        actCaptime =time.time()
        
        self.CamPreview = False
        for i in range(len(AcoCAMArray.cameras)):
            AcoCAMArray.cameras[i].CamPreview = False
        
        for i in range(len(AcoCAMArray.cameras)):
            AcoCAMArray.cameras[i].folderA = self.folderA
        
        for i in range(len(AcoCAMArray.cameras)):
                AcoCAMArray.cameras[i].RECEVENT = True
        
        actT = time.time()
        while((actT-iniCaptime)<=t2Cap):
            for c in range (AcoCAMArray.nCam):
                AcoCAMArray.triggerTH[c].put(True)
            actT = time.time()
        
        for i in range(len(AcoCAMArray.cameras)):
            AcoCAMArray.cameras[i].RECEVENT = False      
        sleep(0.5)            
            
        print ('Surto saveTh')

     def StopCameras(self,evt):
            
        self.CamPreview = False 
        
        for i in range(len(AcoCAMArray.cameras)):
            AcoCAMArray.cameras[i].CamPreview = self.CamPreview
        
        evt.Skip()
        return

    ''' CLASS FLYCAPTHREAD '''

    def newIm(self):

        im = fc2.Image()
        self.c.retrieve_buffer(im)
        ar = np.array(im)
        return cv2.cvtColor(ar,cv2.COLOR_BAYER_BG2BGR)

    def update(self):

        while True:
            if self.stopped:
                return

            self.outframe = self.newIm()

            if self.CamPreview:
                im = self.outframe #REDUIR IM ABANS DE ENVIAR AL QUEUE
                pcktQ= (cv2.resize(im,(240,195)),self.nWindowPreview)
                self.qPreview.put(pcktQ)

            CAPTFLAG = self.triggerTH.empty()

            if CAPTFLAG == False:
                CAPTFLAG = self.triggerTH.get()

                if self.outVid is None and self.RECEVENT:
                    nomVideo = self.folderA+'cam'+str(self.sn)+'_EVT'+str(self.nEvent)+'.avi'
                    print('Nom Video = '+nomVideo)
                    self.outVid = cv2.VideoWriter(nomVideo,cv2.VideoWriter_fourcc('X','V','I','D'), FRMCAM, self.sizeCam)

                if self.RECEVENT is False and self.outVid is not None:

                    self.outVid.release()
                    self.outVid = None
                    self.nEvent +=1
                    print('Video '+str(self.sn)+' Parat')

                if self.outVid is not None and self.RECEVENT is True:
                    #self.outVid.write(cv2.resize(self.outframe,self.sizeCam))
                    self.outVid.write(self.outframe)
                self.ctfr +=1































































''' THREADED CLASS (vFran)'''







'''CODE'''

'''HERE IT WOULD BE GOOD TO CONTROL THE NUMBER OF CAMERAS'''
# Set camera serial numbers
SerialNums = list(_CamArray.values())
SerialNums = SerialNums[0:3]

# Get system
system = PySpin.System.GetInstance()
 
# Get camera list
cam_list = system.GetCameras()


if len(cam_list) > 1:

    cams = []
    
    # Get cameras by serial and initialize
    for i in range(len(SerialNums)):
        cams.append(cam_list.GetBySerial(SerialNums[i]))
        cams[i].Init()
        cams[0].AcquisitionMode.SetValue(PySpin.AcquisitionMode_Continuous)

    # Set primary camera
    cams[0].LineSelector.SetValue(PySpin.LineSelector_Line2)
    # cams[0].V3_3Enable.SetValue(True)

    # Set secondary cameras
    for cam in cams[1::]:
        cam.TriggerMode.SetValue(PySpin.TriggerMode_Off)
        cam.TriggerSource.SetValue(PySpin.TriggerSource_Line3)
        cam.TriggerOverlap.SetValue(PySpin.TriggerOverlap_ReadOut)
        cam.TriggerMode.SetValue(PySpin.TriggerMode_On)

elif len(cam_list) == 1:
    cams = cam_list[0]

else:
    # might as well be that no cameras are connected ??
    print('Error, no cameras were selected to record!')

'''MAIN LOOP'''


for i in range(10):
    h = 0
    for cam in cams:
        cam.BeginAcquisition()
        img = cam.GetNextImage(100)
        img.Save('~/img_cam' + str(h) + '_frame' + str(i))
        img.Release()
        h += 1

 

'''
# Start acquisition; note that secondary cameras have to be started first so acquisition of primary camera triggers secondary cameras.
cam_2.BeginAcquisition()
cam_3.BeginAcquisition()
cam_1.BeginAcquisition()
 
# Acquire images
image_1 = cam_1.GetNextImage()
image_2 = cam_2.GetNextImage()
image_3 = cam_3.GetNextImage()
 
# Save images
image_1.Save('cam_1.png')
image_2.Save('cam_2.png')
image_3.Save('cam_3.png')
 
# Release images
image_1.Release()
image_2.Release()
image_3.Release()
 
# end acquisition
cam_1.EndAcquisition()
cam_2.EndAcquisition()
cam_3.EndAcquisition()







NUM_IMAGES = 10  # number of images to grab




def acquire_images(cam, nodemap, nodemap_tldevice):

    try:
        result = True

        # In order to access the node entries, they have to be casted to a pointer type (CEnumerationPtr here)
        node_acquisition_mode = PySpin.CEnumerationPtr(nodemap.GetNode('AcquisitionMode'))
        if not PySpin.IsAvailable(node_acquisition_mode) or not PySpin.IsWritable(node_acquisition_mode):
            print('Unable to set acquisition mode to continuous (enum retrieval). Aborting...')
            return False

        # Retrieve entry node from enumeration node
        node_acquisition_mode_continuous = node_acquisition_mode.GetEntryByName('Continuous')
        if not PySpin.IsAvailable(node_acquisition_mode_continuous) or not PySpin.IsReadable(node_acquisition_mode_continuous):
            print('Unable to set acquisition mode to continuous (entry retrieval). Aborting...')
            return False

        # Retrieve integer value from entry node
        acquisition_mode_continuous = node_acquisition_mode_continuous.GetValue()

        # Set integer value from entry node as new value of enumeration node
        node_acquisition_mode.SetIntValue(acquisition_mode_continuous)

        print('Acquisition mode set to continuous...')

        #  Image acquisition must be ended when no more images are needed.
        cam.BeginAcquisition()

        print('Acquiring images...')

        #  Retrieve device serial number for filename
        #
        #  *** NOTES ***
        #  The device serial number is retrieved in order to keep cameras from
        #  overwriting one another. Grabbing image IDs could also accomplish
        #  this.
        device_serial_number = ''
        node_device_serial_number = PySpin.CStringPtr(nodemap_tldevice.GetNode('DeviceSerialNumber'))
        if PySpin.IsAvailable(node_device_serial_number) and PySpin.IsReadable(node_device_serial_number):
            device_serial_number = node_device_serial_number.GetValue()
            print('Device serial number retrieved as %s...' % device_serial_number)

        # Retrieve, convert, and save images
        for i in range(NUM_IMAGES):
            try:

                # get image with a timeout of 1000 miliseconds
                image_result = cam.GetNextImage(1000)

                ## HERE IT WOULD BE INTERESTING TO DISCARD ALL IMAGES FROM THE POOL
                if image_result.IsIncomplete():
                    print('Image incomplete with image status %d ...' % image_result.GetImageStatus())

                else:
                    
                    # convert image to color (BGR 8)
                    image_converted = image_result.Convert(PySpin.PixelFormat_BGR8, PySpin.NEAREST_NEIGHBOR)

                    # Create a unique filename
                    if device_serial_number:
                        filename = 'Acquisition-%s-%d.jpg' % (device_serial_number, i)
                    else:  # if serial number is empty
                        filename = 'Acquisition-%d.jpg' % i

                    image_converted.Save(filename)
                    print('Image saved at %s' % filename)

                    image_result.Release()
                    print('')

            except PySpin.SpinnakerException as ex:
                print('Error: %s' % ex)
                return False

        cam.EndAcquisition()
    
    except PySpin.SpinnakerException as ex:
        print('Error: %s' % ex)
        return False

    return result


def print_device_info(nodemap):
    """
    This function prints the device information of the camera from the transport
    layer; please see NodeMapInfo example for more in-depth comments on printing
    device information from the nodemap.

    :param nodemap: Transport layer device nodemap.
    :type nodemap: INodeMap
    :returns: True if successful, False otherwise.
    :rtype: bool
    """

    print('*** DEVICE INFORMATION ***\n')

    try:
        result = True
        node_device_information = PySpin.CCategoryPtr(nodemap.GetNode('DeviceInformation'))

        if PySpin.IsAvailable(node_device_information) and PySpin.IsReadable(node_device_information):
            features = node_device_information.GetFeatures()
            for feature in features:
                node_feature = PySpin.CValuePtr(feature)
                print('%s: %s' % (node_feature.GetName(),
                                  node_feature.ToString() if PySpin.IsReadable(node_feature) else 'Node not readable'))

        else:
            print('Device control information not available.')

    except PySpin.SpinnakerException as ex:
        print('Error: %s' % ex)
        return False

    return result


def run_single_camera(cam):
    """
    This function acts as the body of the example; please see NodeMapInfo example
    for more in-depth comments on setting up cameras.

    :param cam: Camera to run on.
    :type cam: CameraPtr
    :return: True if successful, False otherwise.
    :rtype: bool
    """
    try:
        result = True

        # Retrieve TL device nodemap and print device information
        nodemap_tldevice = cam.GetTLDeviceNodeMap()

        result &= print_device_info(nodemap_tldevice)

        # Initialize camera
        cam.Init()

        # Retrieve GenICam nodemap
        nodemap = cam.GetNodeMap()

        # Acquire images
        result &= acquire_images(cam, nodemap, nodemap_tldevice)

        # Deinitialize camera
        cam.DeInit()

    except PySpin.SpinnakerException as ex:
        print('Error: %s' % ex)
        result = False

    return result


def main():
    """
    Example entry point; please see Enumeration example for more in-depth
    comments on preparing and cleaning up the system.

    :return: True if successful, False otherwise.
    :rtype: bool
    """

    # Since this application saves images in the current folder
    # we must ensure that we have permission to write to this folder.
    # If we do not have permission, fail right away.
    try:
        test_file = open('test.txt', 'w+')
    except IOError:
        print('Unable to write to current directory. Please check permissions.')
        input('Press Enter to exit...')
        return False

    test_file.close()
    os.remove(test_file.name)

    result = True

    # Retrieve singleton reference to system object
    system = PySpin.System.GetInstance()

    # Retrieve list of cameras from the system
    cam_list = system.GetCameras()

    num_cameras = cam_list.GetSize()

    print('Number of cameras detected: %d' % num_cameras)

    # Run example on each camera
    for i, cam in enumerate(cam_list):

        print('Running example for camera %d...' % i)

        result &= run_single_camera(cam)
        print('Camera %d example complete... \n' % i)

    del cam

    # Clear camera list before releasing system
    cam_list.Clear()

    # Release system instance
    system.ReleaseInstance()

    input('Done! Press Enter to exit...')
    return result

if __name__ == '__main__':
    if main():
        sys.exit(0)
    else:
        sys.exit(1)

'''