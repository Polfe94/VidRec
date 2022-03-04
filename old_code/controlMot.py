"""
Clase contructora dels missatges per enviar a diversos motors
@author: F Xavier Gomez 17-2-2019
"""

import serial
from time import sleep

import sys


'''
VAR GLOBALS
'''

SPACE = " "
ENDCAR = "\r"
ENCZ ="ABSZ"
getZEnc ="1"

DEBUG = False

TOL = 25

# default project values for serial port
# _port = /dev/ttyUSB0
# _baud = 115200


class ArduMot:

    ARDUINO = "ACOLOMA"
    getPosArdu = "Q"
    resetArdu = "R"
    comSetZArdu ="S"
    comMovUp = "-"
    comMovDw = "+"
    comMovUpFast = "U"
    comMovDwFast = "D"
    comMissCapOn = "F"
    comMissCapOFF = "P"
    comEncoderZ = "E"
    getEncPos = "EQ"
    checkReady = "K"

    def __init__(self, port, baud, spinCamQ):

        self.spinCamQ = spinCamQ

        self.ardu = serial.Serial()
        self.ardu.port = port
        self.ardu.baudrate = baud

        self.start()        
        sleep(0.001)
        self.check()

        self.ready = True
        
    def start(self):
        if not self.ardu.is_open:
            try:
                self.ardu.open()
                self.ardu.reset_output_buffer()
            except:
                print('+++ controlMot.start(): Error')
                sys.exit(0)

    def stop(self):
        if self.ardu.is_open:
            self.ardu.close()
            sleep(0.1)

    def check(self):
        if(self.ardu.is_open == False):
            print('++ Serial port NOT open')
            return False
        else:
            print('+++ Serial port open')
            return True

    def write(self, command):
        self.ardu.reset_input_buffer()
        self.ardu.write(str.encode(command +ENDCAR))

    def reset(self):
        self.write(ArduMot.resetArdu)
        #self.chkReady()

    def chkReady(self):
        try:
            self.ardu.reset_input_buffer()
            retStr = self.ardu.readline().decode()
            self.ready = (retStr[:3] == 'YES') 
            while not self.ready:
                self.updXYZ(retStr)
                retStr = self.ardu.readline().decode()
                self.ready = (retStr[:3] == 'YES') 
        except Exception as e:
            print('+++ controlMot.chkReady(): Error')
            print(e)
            self.start()

    def updXYZ(self, retStr):
        # get instant cam position            
        if (retStr[-4:-2] == 'eF'):
            try:
                x = float(retStr[retStr.find('X') +1: retStr.find('Y')])
                y = float(retStr[retStr.find('Y') +1: retStr.find('Z')])
                z = float(retStr[retStr.find('Z') +1: retStr.find('eF')])
            except:
                pass
            # update instant cam position in spinCam.positionQ            
            try:
                if self.spinCamQ.full(): self.spinCamQ.get()
                self.spinCamQ.put((x, y, z))
            except:
                print('+++ controlMot.updXYZ(): Error in self.spinCamQ.put()')
            
    def moveZ(self, Z):
        # manual focus on stop (tracking off)
        # Att!!! don't change numeric format
        self.write('Z%5.4f' % (Z))
        self.chkReady()        

    def move2(self, X, Y, Z = 0):
        # Att!!! don't change numeric format
        self.write('X%5.4fY%5.4fZ%5.4f' % (X, Y, Z))          
        self.chkReady()

    def position(self):
        try:
            self.write(ArduMot.getPosArdu)
            retStr = self.ardu.readline().decode()
            if (retStr[-4:-2] == 'eF'):
                x = float(retStr[retStr.find('X') +1: retStr.find('Y')])
                y = float(retStr[retStr.find('Y') +1: retStr.find('Z')])
                z = float(retStr[retStr.find('Z') +1: retStr.find('eF')])
                return (x, y, z)
            else:
                print('+++ controlMot.position(): moving')
                return ()
        except:
            print('+++ controlMot.position(): Error')
            return ()
    
    