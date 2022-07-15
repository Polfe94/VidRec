import PySpin
import cv2
import numpy as np
from time import sleep
from threading import Thread
import time
from queue import Queue

DEBUG = False

imsY,imsX = 1080,1920

FRMCAM =15
actExp =30
genGain =0

TRIGGER = False
RGB = True

dimX = 2000
dimY = 1500

maxX = 5472
maxY = 3078

currX = 1776
currY = 1284

class SpinThreaded:
    
    maxExp = 60
    minExp = 1
    maxGain = 24
    maxA = 1024
    maxB = 1024
    vA = 512
    vB = 512
    BACKSETTED = False
    
    REALCAM = True
    COLOR = False
    nmock=1
    Tini = time.time()
    font = cv2.FONT_HERSHEY_SIMPLEX
    
    ACTRES = 0
    
    def __init__(self,nCam,RGBCAM,QspinCam):
        
        self.stopped = False
        self.CamPreview = True
        self.nWindowPreview = 0
        self.recordVideo = False
        self.Q = QspinCam
        
        self.outframe = np.zeros((100,100,3),dtype=np.uint8)
        
        if(self.REALCAM):
            self.n = nCam
            self.stopped = False
            self.ctfr = 0
            self.nWindowPreview = 0
            self.CAPTVIDEO = False
            #self.qIm= qIm
            
            self.RGB = True
            
            self.nom = ''
            self.recordVideo = False
            self.BINNING = False
            
            self.camsize = (1920,1200)
            
            try:
                self.system = PySpin.System.GetInstance()
            except:
                print('error getInstance')
                
            self.cam_list = self.system.GetCameras()
            self.num_cameras = self.cam_list.GetSize()
            
            if self.num_cameras ==0:
                print('No cameras detected. Please connect Camera')
                return
            
            self.cam = self.cam_list.GetByIndex(nCam)
            
            self.outVid = None
            
            self.frmcpt = 0
            self.mvcpt = 0
            
            self.nodemap_tldevice = self.cam.GetTLDeviceNodeMap()
            
            self.cam.Init()
            self.cam.BeginAcquisition()
            
            sleep(1)
            
            try:
                if self.cam.IsStreaming():
                    self.cam.EndAcquisition()
                    print('EndAcquisition OK')
            except:
                print('No es pot EndAcquisition()')
                
           
            self.nodemap = self.cam.GetNodeMap()
            
            #Binning Selector
            binSel = self.nodemap.GetNode("BinningSelector")
            node_bin_selector = PySpin.CEnumerationPtr(binSel)
            node_bin_selector_sensor = node_bin_selector.GetEntryByName("All")
            bin_selector_value = node_bin_selector_sensor.GetValue()
            node_bin_selector.SetIntValue(bin_selector_value)
            
            #BinningHorizontal
            node_BH = PySpin.CIntegerPtr(self.nodemap.GetNode("BinningHorizontal"))
            
            if node_BH.GetAccessMode()==4:
                node_BH.SetValue(2)
            else:
                print('+++ Error 117 set BinningSelector')
            
            #Binning Horizontal Mode
            binHoz = self.nodemap.GetNode("BinningHorizontalMode")
            node_bin_horiz = PySpin.CEnumerationPtr(binHoz)
            node_bin_horiz_add = node_bin_horiz.GetEntryByName("Sum")
            bin_horiz_value = node_bin_horiz_add.GetValue()
            
            if node_bin_horiz.GetAccessMode()==4:
                node_bin_horiz.SetIntValue(bin_horiz_value)
            else:
                print('+++ Error 127 set BinningHorizontalMode')
            
            
            #BinningVertical
            node_BH = PySpin.CIntegerPtr(self.nodemap.GetNode("BinningVertical"))
                        
            if node_BH.GetAccessMode()==4:
                node_BH.SetValue(2)
            else:
                print('+++ Error 129 set BinningVertical')
            
            
            #Binning Vertical Mode
            binVer = self.nodemap.GetNode("BinningVerticalMode")
            node_bin_ver = PySpin.CEnumerationPtr(binVer)
            node_bin_ver_add = node_bin_ver.GetEntryByName("Sum")
            bin_ver_value = node_bin_ver_add.GetValue()
            
            if binVer.GetAccessMode()==4:
                node_bin_ver.SetIntValue(bin_ver_value)
            else:
                print('+++ Error 129 set BinningVerticalMode')
            
            
            #Device Thr Limit
            self.cam.DeviceLinkThroughputLimit.SetValue(60000000)
            
            #Pixel Format
            pix = self.nodemap.GetNode("PixelFormat")
            node_pixel_format = PySpin.CEnumerationPtr(pix)
            node_pixel_format_mono16 = node_pixel_format.GetEntryByName("Mono16")
            acquisition_mode_pixel = node_pixel_format_mono16.GetValue()
            
            if pix.GetAccessMode()==4:
                node_pixel_format.SetIntValue(acquisition_mode_pixel)
            else:
                print('+++ Error 164 PixelFormat')
            
            #ADC
            adc = self.nodemap.GetNode("AdcBitDepth")
            node_adc = PySpin.CEnumerationPtr(adc)
            node_adc_12 = node_adc.GetEntry(2)
            adc_mode_12 = node_adc_12.GetValue()
            if adc.GetAccessMode()==4:
                node_adc.SetIntValue(adc_mode_12)
            else:
                print('+++ Error 174 AdcBitDepth')
            
            
            self.node_acquisition_mode = PySpin.CEnumerationPtr(self.nodemap.GetNode("AcquisitionMode"))
            self.node_acquisition_mode_continuous = self.node_acquisition_mode.GetEntryByName("Continuous")
            self.acquisition_mode_continuous = self.node_acquisition_mode_continuous.GetValue()
            self.node_acquisition_mode.SetIntValue(self.acquisition_mode_continuous)
            

            """
            MODE COLOR
            """
            '''
            try:
                if self.cam.PixelFormat.GetAccessMode() == PySpin.RW:
                    self.cam.PixelFormat.SetValue(PySpin.PixelColorFilter_BayerBG)#COLOR RGB
                    print("Pixel format set to %s..." % self.cam.PixelFormat.GetCurrentEntry().GetSymbolic())
            except PySpin.SpinnakerException as ex:
                print("Error: %s" % ex)
            '''
                
            '''SET BUFFERHANDLING'''
            self.nodemap_TLSdevice = self.cam.GetTLStreamNodeMap()
            
            self.ptrHandlingMode = PySpin.CEnumerationPtr(self.nodemap_TLSdevice.GetNode("StreamBufferHandlingMode"))
            self.ptrHandlingModeEntry = self.ptrHandlingMode.GetEntryByName("NewestOnly")
            self.ptrHandlingMode.SetIntValue(self.ptrHandlingModeEntry.GetValue())     
                
            """Configuracio QuickSpin"""
            
            """Exposure Time"""
            if self.cam.ExposureAuto is None or self.cam.ExposureAuto.GetAccessMode() != PySpin.RW:
                print("Unable to disable automatic exposure. Aborting...")
                return False
            
            self.cam.ExposureAuto.SetValue(PySpin.ExposureAuto_Off)

            """
            Activar el Balanc de Blanc! (cal per les cameres en color)
            """
            
            if(False):
                self.cam.BalanceWhiteAuto.SetValue(PySpin.BalanceWhiteAuto_Off,False)#,False)
                self.cam.BalanceRatioSelector.SetValue(PySpin.BalanceRatioSelector_Blue)
                node_BR = PySpin.CFloatPtr(self.nodemap.GetNode("BalanceRatio"))
                node_BR.SetValue(2.0)
                
                self.cam.BalanceRatioSelector.SetValue(PySpin.BalanceRatioSelector_Red)
                node_BR.SetValue(3.0)
            
            """Gain"""
            self.cam.GainAuto.SetValue(PySpin.GainAuto_Off)
            
            if self.cam.OffsetX.GetAccessMode() == PySpin.RW:
                self.cam.OffsetX.SetValue(self.cam.OffsetX.GetMin())
                print ("Offset X set to %d..." % self.cam.OffsetX.GetValue())

            else:
                print ("Offset X not available...")

            if self.cam.OffsetY.GetAccessMode() == PySpin.RW:
                self.cam.OffsetY.SetValue(self.cam.OffsetY.GetMin())
                print ("Offset Y set to %d..." % self.cam.OffsetY.GetValue())
            else:
                print ("Offset Y not available...")
            
            """
            AJUSTO MIDA CAPUTURA PIXELS camera
            """
            if self.cam.Width.GetAccessMode() == PySpin.RW and self.cam.Width.GetInc() != 0 and self.cam.Width.GetMax != 0:
                self.cam.Width.SetValue(self.cam.WidthMax())
                print ("Width set to %i..." % self.cam.Width.GetValue())

            else:
                print ("Width not available...")
            
            if self.cam.Height.GetAccessMode() == PySpin.RW and self.cam.Height.GetInc() != 0 and self.cam.Height.GetMax != 0:
                self.cam.Height.SetValue(self.cam.HeightMax())
                print ("Height set to %i..." % self.cam.Height.GetValue())
            else:
                print ("Height not available...")
            
            
            
            self.cam.BeginAcquisition()
            
            self.sn = self.getSerial()
            self.BCK = False
            #self.setExp(100)
            print("Serial Number = ",self.sn)
            
            self.setGain(30)
            self.setGamma(0.8)
            
        else:
        
            self.mockim = []
            self.sn = 8888
            print("Serial Number = ",self.sn)
        
    def setParam(self,strparam):
        self.param  = strparam
        return
    
    def setWB (self,vA,vB):
        if (self.REALCAM and self.COLOR):
        
            self.cam.BalanceRatioSelector.SetValue(PySpin.BalanceRatioSelector_Blue)
            node_BR = PySpin.CFloatPtr(self.nodemap.GetNode("BalanceRatio"))
            node_BR.SetValue(vB)
            
            self.cam.BalanceRatioSelector.SetValue(PySpin.BalanceRatioSelector_Red)
            node_BR.SetValue(vA)   

        return
    
    def getWB(self):
        if self.REALCAM and self.COLOR:
            self.cam.BalanceRatioSelector.SetValue(PySpin.BalanceRatioSelector_Blue)
            node_AR = PySpin.CFloatPtr(self.nodemap.GetNode("BalanceRatio"))
            self.vA = node_AR.GetValue()
        
            self.cam.BalanceRatioSelector.SetValue(PySpin.BalanceRatioSelector_Red)
            node_BR = PySpin.CFloatPtr(self.nodemap.GetNode("BalanceRatio"))
            self.vB = node_BR.GetValue()
        else:
            self.vA = 1
            self.vB = 1
        
        return ((int)(self.vA*1000),(int)(self.vB*1000))
        
    def setExp(self,exposure):
        if self.REALCAM:
            try:
                exposure = min(self.cam.ExposureTime.GetMax(),(exposure*1000))
                if exposure <20:
                    exposure = 20
                self.cam.ExposureTime.SetValue(exposure)
                print("Exposure set = ",exposure)
            except PySpin.SpinnakerException as ex:
                print("Error: %s" % ex.what())
        else:
            return
    def getMaxExp(self):
        return (self.cam.ExposureTime.GetMax()/1000)
              
    def getExp(self):
        
        if self.REALCAM:
            exp = 0
            try:
                exp = self.cam.ExposureTime.GetValue()
                print("Exposure setted = ",exp)
            except PySpin.SpinnakerException as ex:
                print("Error: %s" % ex.what())
        else:
            exp = 40
            
        return exp
       
    def setLive(self,live):
        self.CamPreview = live
        
    def getLive(self):
        return self.CamPreview
    
    def setGain(self,gain):
        
        if self.REALCAM:
            try:
                gain = min(self.cam.Gain.GetMax(),gain)
                self.cam.Gain.SetValue(gain)
        
            except PySpin.SpinnakerException as ex:
                print("Error: %s" % ex.what())
        else:
            return
    
    def setGamma(self,g):
        if(self.REALCAM):
            try:
                self.cam.Gamma.SetValue(g)
            except PySpin.SpinnakerException as ex:
                print("Error: %s" % ex.what())    
            return
        return
        
    def getGain(self):
        
        gain = 0.0
        
        if self.REALCAM:
        
            try:
                return self.cam.Gain.GetValue()
        
            except PySpin.SpinnakerException as ex:
                print("Error: %s" % ex.what())
        else:
            return gain
            
    def getSerial(self):
        
        if self.REALCAM:
            return self.cam.DeviceSerialNumber.GetValue()
        else:
            return 88888
        
    def activaBinning(self):
        
        try:
            self.cam.EndAcquisition()
        except:
            print('camera not initated')
        
        #Binning Selector
        binSel = self.nodemap.GetNode("BinningSelector")
        node_bin_selector = PySpin.CEnumerationPtr(binSel)
        node_bin_selector_sensor = node_bin_selector.GetEntryByName("All")
        bin_selector_value = node_bin_selector_sensor.GetValue()
        node_bin_selector.SetIntValue(bin_selector_value)
        #BinningHorizontal
        node_BH = PySpin.CIntegerPtr(self.nodemap.GetNode("BinningHorizontal"))
        node_BH.SetValue(2)
        #Binning Horizontal Mode
        binHoz = self.nodemap.GetNode("BinningHorizontalMode")
        node_bin_horiz = PySpin.CEnumerationPtr(binHoz)
        node_bin_horiz_add = node_bin_horiz.GetEntryByName("Sum")
        bin_horiz_value = node_bin_horiz_add.GetValue()
        node_bin_horiz.SetIntValue(bin_horiz_value)
        #BinningVertical
        node_BH = PySpin.CIntegerPtr(self.nodemap.GetNode("BinningVertical"))
        node_BH.SetValue(2)
        #Binning Vertical Mode
        binVer = self.nodemap.GetNode("BinningVerticalMode")
        node_bin_ver = PySpin.CEnumerationPtr(binVer)
        node_bin_ver_add = node_bin_ver.GetEntryByName("Sum")
        bin_ver_value = node_bin_ver_add.GetValue()
        node_bin_ver.SetIntValue(bin_ver_value)
        #Device Thr Limit
        self.cam.DeviceLinkThroughputLimit.SetValue(500000000)
        #Pixel Format
        pix = self.nodemap.GetNode("PixelFormat")
        node_pixel_format = PySpin.CEnumerationPtr(pix)
        node_pixel_format_mono16 = node_pixel_format.GetEntryByName("Mono16")
        acquisition_mode_pixel = node_pixel_format_mono16.GetValue()
        node_pixel_format.SetIntValue(acquisition_mode_pixel)
        #ADC
        adc = self.nodemap.GetNode("AdcBitDepth")
        node_adc = PySpin.CEnumerationPtr(adc)
        node_adc_12 = node_adc.GetEntry(2)
        adc_mode_12 = node_adc_12.GetValue()
        node_adc.SetIntValue(adc_mode_12)
        
        
        if self.cam.OffsetX.GetAccessMode() == PySpin.RW:
            self.cam.OffsetX.SetValue(self.cam.OffsetX.GetMin())
            print ("Offset X set to %d..." % self.cam.OffsetX.GetValue())

        else:
            print ("Offset X not available...")

        if self.cam.OffsetY.GetAccessMode() == PySpin.RW:
            self.cam.OffsetY.SetValue(self.cam.OffsetY.GetMin())
            print ("Offset Y set to %d..." % self.cam.OffsetY.GetValue())
        else:
            print ("Offset Y not available...")
        
        """
        AJUSTO MIDA camera
        """
        if self.cam.Width.GetAccessMode() == PySpin.RW and self.cam.Width.GetInc() != 0 and self.cam.Width.GetMax != 0:
            self.cam.Width.SetValue(self.cam.WidthMax())
            print ("Width set to %i..." % self.cam.Width.GetValue())

        else:
            print ("Width not available...")
        
        if self.cam.Height.GetAccessMode() == PySpin.RW and self.cam.Height.GetInc() != 0 and self.cam.Height.GetMax != 0:
            self.cam.Height.SetValue(self.cam.HeightMax())
            print ("Height set to %i..." % self.cam.Height.GetValue())
        else:
            print ("Height not available...")

        
        self.cam.BeginAcquisition()
        sleep(0.1)
                    
    def desactivaBinning(self):
        
        try:
            self.cam.EndAcquisition()
        except:
            print('camera not initated')
    
        #BinningHorizontal
        node_BH = PySpin.CIntegerPtr(self.nodemap.GetNode("BinningHorizontal"))
        node_BH.SetValue(1)
        #BinningVertical
        node_BH = PySpin.CIntegerPtr(self.nodemap.GetNode("BinningVertical"))
        node_BH.SetValue(1)
        #Device Thr Limit
        self.cam.DeviceLinkThroughputLimit.SetValue(60000000)
        #Pixel Format
        pix = self.nodemap.GetNode("PixelFormat")
        node_pixel_format = PySpin.CEnumerationPtr(pix)
        node_pixel_format_mono16 = node_pixel_format.GetEntryByName("Mono8")
        acquisition_mode_pixel = node_pixel_format_mono16.GetValue()
        node_pixel_format.SetIntValue(acquisition_mode_pixel)
        #ADC
        adc = self.nodemap.GetNode("AdcBitDepth")
        node_adc = PySpin.CEnumerationPtr(adc)
        node_adc_12 = node_adc.GetEntry(1)
        adc_mode_12 = node_adc_12.GetValue()
        node_adc.SetIntValue(adc_mode_12)
        
        self.cam.OffsetX.SetValue(self.cam.OffsetX.GetMin())
        self.cam.OffsetY.SetValue(self.cam.OffsetY.GetMin())
        
        self.cam.Width.SetValue(self.cam.WidthMax())
        self.cam.Height.SetValue(self.cam.HeightMax())
        
        if self.cam.OffsetX.GetAccessMode() == PySpin.RW:
            self.cam.OffsetX.SetValue(self.cam.OffsetX.GetMin())
            print ("Offset X set to %d..." % self.cam.OffsetX.GetValue())

        else:
            print ("Offset X not available...")

        if self.cam.OffsetY.GetAccessMode() == PySpin.RW:
            self.cam.OffsetY.SetValue(self.cam.OffsetY.GetMin())
            print ("Offset Y set to %d..." % self.cam.OffsetY.GetValue())
        else:
            print ("Offset Y not available...")
        
        """
        AJUSTO MIDA camera
        """
        if self.cam.Width.GetAccessMode() == PySpin.RW and self.cam.Width.GetInc() != 0 and self.cam.Width.GetMax != 0:
            self.cam.Width.SetValue(self.cam.WidthMax())
            print ("Width set to %i..." % self.cam.Width.GetValue())

        else:
            print ("Width not available...")
        
        if self.cam.Height.GetAccessMode() == PySpin.RW and self.cam.Height.GetInc() != 0 and self.cam.Height.GetMax != 0:
            self.cam.Height.SetValue(self.cam.HeightMax())
            print ("Height set to %i..." % self.cam.Height.GetValue())
        else:
            print ("Height not available...")
        
        self.cam.BeginAcquisition()
        sleep(0.1)
        

    def read(self):
        if self.REALCAM:
            return self.outframe
        else:
            return self.mockIM()
        
    def newIm(self,hq=False):
        
        if(DEBUG):
            print('entro newIm SpinThreaded')
        
        if self.REALCAM:
            try:
                iniTime = time.time()
                image_result = self.cam.GetNextImage()
                
                '''
                actTime = time.time()
                temps = actTime - iniTime
                print("GetNextImage:" + str(temps))
                '''
                if image_result.IsIncomplete():
                    print("Image incomplete with image status %d ..." % image_result.GetImageStatus())
               
            
                #imout = (image_result.Convert(PySpin.PixelFormat_BGR8, PySpin.HQ_LINEAR)).GetNDArray()
                '''
                iniTime = time.time()
                imout = image_result.GetNDArray()
                actTime = time.time()
                temps = actTime - iniTime
                print("GetNDArray:" + str(temps))
                '''
                #imout = cv2.cvtColor(image_result.GetNDArray(),cv2.COLOR_BAYER_BG2BGR)
                return image_result.GetNDArray()
    
            except PySpin.SpinnakerException as ex:
                print("Error:newIm")
        else:
            if(DEBUG):
                print('surto newIm MOCK')
            
            return self.mockIM()

    def updateApp(self):

        while True:
            
            if DEBUG: print('entro updateApp SpinThreaded')
            if self.stopped:
                return
            
            self.Q.put(self.newIm())
         
            if DEBUG: print('surto updateApp SpinThreaded')
            
        return True
    
    def rmvBCKAlter(self,inputImage):
        

        kernelBlur =(257,257)
        
        try:
            BCK = (cv2.GaussianBlur(inputImage,kernelBlur,0))+64
            imOut = inputImage.astype(dtype='float64')/BCK.astype(dtype='float64')
        except:
            print('Out divArray')
            imOut = inputImage.astype(dtype='float64')/BCK.astype(dtype='float64')
            
        imOut = np.where(imOut>1.0,1,imOut)
        imx = (np.multiply(imOut,255)).astype(dtype=np.uint8)
        
        return imx

    def rmvBCK(self,inputImage):
        
        inputImage = inputImage
        
        imgN = np.divide(inputImage.astype(dtype=np.float64),256)#np.asarray(inputImage, dtype=np.float32)
        mskN = np.divide(self.bck.astype(dtype=np.float64),256)
        imOut = imgN/mskN
            
        imOut = np.where(imOut>1.0,1,imOut)
        imx = (np.multiply(imOut,255)).astype(dtype=np.uint8)
        
        return imx

    def setBCK(self,im):
        
        self.bck = im
        self.BCK = True
        return 

    def start(self):
        print ('Start images pSpinThread')
        
        Pr = Thread(target=self.updateApp,args=())
        Pr.daemon = True
        Pr.start()
        return self
    
    def stop(self):
        
        self.stopped = True
        return
   
    def autoWB (self):
        
        if self.REALCAM:
            self.cam.BalanceWhiteAuto.SetValue(PySpin.BalanceWhiteAuto_Continuous,True)

        return #(vA,vB)
    
    def mockIM(self):
        
        font = cv2.FONT_HERSHEY_SIMPLEX
        w,h = dimX,dimY
        im = np.random.randint(96, size=(h,w,3),dtype=np.uint8)#np.ones((h,w,3),dtype=np.uint8)
        #im = im*200
        cv2.putText(im,str(self.nmock),(int(w//2),int(h//2)), font,4,(128,0,255),5,cv2.LINE_AA)
        self.nmock +=1
        if self.nmock>99999:self.nmock=0
        #sleep(0.05)

        return im
    