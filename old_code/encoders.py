#!/usr/bin/env python
# coding: utf-8
"""
Codi per Llegir els Encoders XY
author: fxgomezco@winkoms.eu
"""

import serial
from time import sleep
import sys

ENDCAR = '\r'
GETPOS = 'Q'
DEBUG = False


class Encoder:

    def __init__(self, port, baud):
        
        print('Inicio Port Arduino')
        
        self.ardu = serial.Serial()
        self.ardu.port = port
        self.ardu.baudrate = baud
        
        self.iniSerial()
        sleep(2)
        self.checkSerial()

    def iniSerial(self):

        if self.ardu.is_open:
            return
        else:
            try:
                self.ardu.open()
            except:
                print('Error obrint el port. Per favor conecteu el ARDUINO')
                #sys.exit(0)
        return

    def checkSerial(self):
        
        try:
            if not self.ardu.is_open:
                miss = 'Conecta el Controlador'
                return False
            else:
                return True
        except:
            miss = 'COMPROVA EL CONTROLADOR ARDUINO'
            return False

    def sendCommand(self,ordre):
        
        comand = ordre+ENDCAR
        self.ardu.write(comand.encode())

    def read(self):
        
        self.sendCommand(GETPOS)
        retStr = self.ardu.readline().decode()
        while not retStr:
            self.sendCommand(GETPOS)
            sleep(0.1)
            retStr = self.ardu.readline().decode()

        x = float(retStr[(retStr.index('X') +1) :retStr.index('Y')])
        y = float(retStr[(retStr.index('Y') +1) :retStr.index('F')])#fx_no hi ha Z

        return (x, y)
