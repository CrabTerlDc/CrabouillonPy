#!/usr/bin/env python
# coding: utf-8

# biblio
#
#

# preferred python3
# login pi/raspberry
# killall -9 python
# odrivetool shell
#
# edit from another linux:
#   sudo apt install sshfs
#   mkdir mntpi
#   sshfs pi@192.168.2.5:. mntpi
#
# debug
#  from from CrabouillonCnc import *
#
# dev 
#   https://www.eclipse.org/downloads/
#   help/marketplace/pydev ... confirm, accept
#   https://www.jetbrains.com/pycharm/  - more for PC dev
#   mu ?

GlobalParams={}
DRV_GRBL=1
DRV_ODRIVE=2
DRV_ESPUSB=3

GlobalParams['AutoInstall']=True

GlobalParams['rev'] = "CrabouillonCnc_20230519" # revision identification (Name_Date)

GlobalParams['Drive']=DRV_ESPUSB
GlobalParams['Simul'] = False # True : simulator instead for devs, +False+ for real life
GlobalParams['AutoRecover'] = True # +True+ : real life recover from whatever, False throw exceptions
GlobalParams['NextFileOnTrig']=False # True - change file if Alarm occurs(max switch trigged)

GlobalParams['DoOdriveCalib'] = True # True to do motors calibration on each startup

GlobalParams['WithSocket']=False
GlobalParams['LogFileName']=False # +False+ for real life, true for devs (at systemd startup) will produce a logfile with Traces

# https://deusyss.developpez.com/tutoriels/RaspberryPi/PythonEtLeGpio/
GpioMinX = 29
GpioMaxX = 31
GpioMinY = 33
GpioMaxY = 35
#GpioPhoto = 18
#GpioPhoto2 = 16
GpioToolUp = 8
GpioTool1 = 10
GpioTool2 = 12
GpioExtTrig1 = 37


if (GlobalParams['AutoRecover']):
  print( "AutoRecover On")
else:
  print( "AutoRecover Off: fail on error or will never find bugs")

# https://openclassrooms.com/forum/sujet/tkinter-comment-marche-mainloop
# https://pythonfaqfr.readthedocs.io/en/latest/prog_even_tkinter.html

# init libs
LibFailureCatastrophic = False
import os
if (GlobalParams['WithSocket']):
    import socket
import time
import sys

# some python flavors want that
try:
    if (True):
      nop=1
except:
    #from builtins import False, True
    nop=1

#try:
#    from notebook.nbconvert.handlers import respond_zip
#except:
#    nop=1

import select
import glob
import subprocess
import copy

GlobalParams['MeRaspi']= True # at first suppose we are in a raspberry pi
from datetime import datetime

try:
  import RPi.GPIO as GPIO
  GlobalParams['MeRaspi']= True
except:
  print( "ERR- No RPi.GPIO (raspberry gpio for python)")
  print( "     try 'pip install RPi.GPIO'")
  print( "     maybe U'r not a raspberry...")
  print( "     see https://deusyss.developpez.com/tutoriels/RaspberryPi/PythonEtLeGpio/")
  #quit()
  GlobalParams['MeRaspi']= False

import time
import math
import atexit
try:
  import termios, tty, fcntl
except:
  print( "ERR- no termios or no tty or no fcntl, is there linux here?")
  import msvcrt

GlobalParams['WithSerial']=False
if (DRV_GRBL == GlobalParams['Drive'] or DRV_ESPUSB == GlobalParams['Drive']):
  try:
    import serial
    from serial.tools import list_ports as serial_tools_list_ports
    GlobalParams['WithSerial']=True
  except:
    print( "try on command line")
    print( "pip install pyserial")
    print( "win: python -m pip install pyserial")
    print( "if not try to get pip for python, maybe 'sudo apt install python-pip'")
    print( "https://pip.pypa.io/en/stable/installing/")
    LibFailureCatastrophic = True
    raise
    
GlobalParams['GrblSerial']=False
GlobalParams['GrblErr']=False # False or the error number in last responses if any, prio wit the one requesting reboot, homing (9), etc
GlobalParams['TempSerial']=False
GlobalParams['EspUsbSerial'] = []
GlobalParams['EspUsbSerialNb'] = 0
GlobalParams['TermalOk']=True

if GlobalParams['WithSerial']:
    print( "Got Serial")

# triggers for whatever
GlobalParams['ExtTrig']={}
GlobalParams['ExtTrig'][GpioExtTrig1]=0
GlobalParams['ExtTrig'][GpioMinX]=0
GlobalParams['ExtTrig'][GpioMaxX]=0
GlobalParams['ExtTrig'][GpioMinY]=0
GlobalParams['ExtTrig'][GpioMaxY]=0

# do not overflow with error messages
GlobalParams['ErrNoFileCnt'] = 0

# TODO_LATER: external triggers from OSC (above 100)
try:
    import OSC
    import types
    GlobalParams['OscServer'] = OSCServer( ( ip, 7120) )
    GlobalParams['OscServer'].timeout = 0
except:
    #os.system("pip3 install python-osc")
    GlobalParams['OscServer']=False

if (GlobalParams['OscServer']):
    GlobalParams['ExtTrig'][100]=0
    def handle_timeout(self):
        self.timed_out = True
    def user_callback(path, tags, args, source):
        global GlobalParams
        Val = str (args[0])
        if ("" == Val):
            GlobalParams['ExtTrig'][100]=1
        else:
            try:
                GlobalParams['ExtTrig'][100]=int(Val)
            except:
                foo=1

    GlobalParams['OscServer'].handle_timeout = types.MethodType(handle_timeout, GlobalParams['OscServer'])
    GlobalParams['OscServer'].addMsgHandler( "/note/1", user_callback )    
    

GlobalParams['Simul'] = not(GlobalParams['MeRaspi'])
GlobalParams['Gui'] = not(GlobalParams['MeRaspi']) # True : draw, +False+ for real life
GlobalParams['GuiList'] = []

if (GlobalParams['Gui']):
  try:
    try:
      import Tkinter
    except:
      import tkinter
      Tkinter=tkinter
    GlobalParams['Gui'] = Tkinter.Tk()
    GlobalParams['Gui'].myLabel = Tkinter.Label( GlobalParams['Gui'], text="Courbet, le geste du peintre")
    GlobalParams['Gui'].myLabel.pack()
    GlobalParams['Gui'].MyMx=520
    GlobalParams['Gui'].MyMy=520
    GlobalParams['Gui'].myDraw = Tkinter.Canvas( GlobalParams['Gui'], width=GlobalParams['Gui'].MyMx, height=GlobalParams['Gui'].MyMy)
    GlobalParams['Gui'].myDraw.pack()
    time.sleep(0.01)
    print("GUI- setup gui ok")
  except:
    print("GUI- ERR- failed to setup gui")
    GlobalParams['Gui']=False
else:
  print("GUI- no gui by config")
  GlobalParams['Gui'] =False

if (LibFailureCatastrophic):
    print( "try on command line")
    print( "pip install asyncio")
    print( "if not try to get pip for python, maybe 'sudo apt install python-pip'")
    print( "if not try to get pip3 for python, maybe 'sudo apt install python3-pip' and call 'pip3 install blabla'")


# TODO_HERE
# grbl - detecter la fin d'execution de tt ce qui est envoye a grbl avant photo 
# homing at boot and on command
# overtemp thru gpio (2nd arduino specialise temp)
# test pause osc

# TODO_LATER
#  dns-sd as a printer
#  params set and get from a file
#  hot restart on script update
#  bettter precision on small segments

# what's in
#   get gcode from files in /home/pi/spool_todo/*.ngc"
#   tool up down see Act_MoveTool(...)
#   photo        see Act_TakePhoto(...)
#   surveillance script

#   run at startup, https://raspberrypi.stackexchange.com/questions/8734/execute-script-on-start-up
# -- initd
# $ sudo chmod 755 /etc/init.d/courbetcnc
# $ sudo update-rc.d courbetcnc defaults
# $ sudo ln -s /etc/rc6.d/S45courbetcnc ../init.d/courbetcnc
#  lrwxrwxrwx 1 root root ...  /etc/rc6.d/S45courbetcnc -> ../init.d/courbetcnc
# ls -l /etc/rc*.d/*cou*
# --systemd
# $ cat /etc/systemd/system/courbetcnc.service
#[Unit]
#Description=cnc courbet le geste du peintre
#
#[Service]
#Type=simple
#ExecStart=/bin/bash /etc/init.d/courbetcnc.sh start
#ExecStop=/bin/bash /etc/init.d/courbetcnc.sh stop
#
#[Install]
#WantedBy=default.target
#
# sudo systemctl enable courbetcnc
#  sudo journalctl -u courbetcnc

# Wifi
#   sudo nano /etc/wpa_supplicant/wpa_supplicant.conf
#   wpa_cli -i wlan0 reconfigure
#   see https://www.raspberrypi.org/documentation/configuration/wireless/wireless-cli.md
#   sudo ifconfig eth0 down
#   sudo ifconfig eth0 hw aa:bb:cc:dd:ee:ff # set new MAC address
#   sudo ifconfig eth0 up

# TODO_LATER
# PVT Position Velocity ... newport ... https://www.newport.com/p/XPS-GCODE

# params init
OdriveErrCount = 0

GlobalParams['AlimVolts']=24
GlobalParams['AlimAmps']=25
# motor specs
#                               rpm/v     A     V    USD      g                                                                Nm
# ODrive Robotics D5065 - 270kv    270      70    32     69    420    https://odriverobotics.com/shop/odrive-custom-motor-d5065    2.14
GlobalParams['MotorMaxAmps'] = 65.0
GlobalParams['MotorMaxVolts'] = 33.6 # 8S
GlobalParams['MotorMaxRpm'] = 8000
GlobalParams['MotorMagNb'] = 18
GlobalParams['MotorTorq'] = 2.3
GlobalParams['MotorPoles'] = 14/2 # 7 by default, counted 14 'stops'

#encoder AMT102-V https://www.cui.com/product/resource/amt10.pdf
GlobalParams['EncoderMaxRpm'] = 7500
GlobalParams['EncoderCpr'] = 8192

GlobalParams['BrakeResistance'] = 1.95
GlobalParams['AxisDiamM'] = 20.0/1000 # 20 mm
GlobalParams['CprToMeters'] = (math.pi*GlobalParams['AxisDiamM'])/GlobalParams['EncoderCpr']
GlobalParams['GcodeToMeters'] = 1.20/348.0 # 1m40 (cnc size)  is 348 units in GCode (see spirals), theory: mm to m is 1.0/1000
GlobalParams['GcodeToCpr'] = GlobalParams['GcodeToMeters']/GlobalParams['CprToMeters']

GlobalParams['TypicalBF'] = 20000
# TODO_LATER : speed test and decide 'vel_limit_Max'
GlobalParams['vel_limit_Max'] = 120000 # absolute speed not to go more than that (3/4 of tha speed that is dangerous)
# 40000 OK

#133185 at max X 1m30
MaxCpr = 115000.0 # availlable CPR on an axis
# 125000.0 tac maxY
# 120000.0 misss room for an encoder calibration
GlobalParams['SizeM'] = 1.0 # size of the bed in meters
GlobalParams['CprToMeters'] = GlobalParams['SizeM']/MaxCpr # in m/cpr
GlobalParams['GcodeToCpr'] = MaxCpr/400.0 # in Cpr/G 
GlobalParams['GcodeToMeters'] = GlobalParams['GcodeToCpr']*GlobalParams['CprToMeters'] 

GlobalParams['CprMax'] = GlobalParams['SizeM']/GlobalParams['CprToMeters']

GlobalParams['CurrentPosX'] = 0
GlobalParams['CurrentPosY'] = 0
GlobalParams['CurrentSpeedX'] = 0.0
GlobalParams['CurrentSpeedY'] = 0.0
CurrentZ = 0
(CorrX, CorrY) = (0,0)
odrv0 = None
(StopXMin, StopXMax) = (0,0)
(StopYMin, StopYMax) = (0,0)

DummyVal = -1.234567389 # a value that won't naturally be found by reading counters (or not often)
GlobalParams['CurrentTool'] = 1  # supposed to start with tool 1 activated
GlobalParams['CurrentZ']    = -1 # supposed to start with tool deployed
GlobalParams['TimeToolMvS'] = 17 # time for up down tools

GlobalParams['pos_setpoint_last'] = DummyVal+0.0 # cache memory to spare 3.5ms in loop if already set

if (DRV_GRBL == GlobalParams['Drive'] or DRV_ESPUSB == GlobalParams['Drive']):
    GlobalParams['CprMax'] = 1000.0
    GlobalParams['GcodeToCpr']= GlobalParams['CprMax']/1000.0 # gcode units to machine units, gcode max is 400(inches), machine mac is 1200mm

GlobalParams['TsunamiLines']=[ 15, 13, 11, 7]

# "RUN" "HOMING" "TUNE"
GlobalParams['State']="RUN"

if (GlobalParams['WithSocket']):
    #GlobalParams['TraceSocket'] = ("localhost", 8787)
    GlobalParams['TraceSocket'] = (socket.gethostname(), 8787)
GlobalParams['TraceTTy'] = None # None: will open ty1 asap

GlobalParams['ParamList'] =( "BF",)
if (GlobalParams['MeRaspi']):
  GlobalParams['BasePath']="/home/crabouillon/"
else:
  GlobalParams['BasePath']="./"

TraceNoAccept = False
TraceChar = False
Epsilon = 0.001

def SocketExchange():
    """ read and write to the 'run'ner """
    global GlobalParams
    (TraceLastUs, TraceLastMs) = (0,0)
    ClientSocket = None
    EndLoop=False
    Count=0
    print("attempt connection to %s" % str(GlobalParams['TraceSocket']))
    
    if (GlobalParams['WithSocket']):
        while(not EndLoop):
            if (ClientSocket is None):
                try:
                    ClientSocket = socket.socket( socket.AF_INET, socket.SOCK_STREAM)
                    #now connect to the web server on port 80
                    # - the normal http port
                    # ClientSocket.setblocking(0) # Hummm no connect with nonblocking
                    ClientSocket.connect(GlobalParams['TraceSocket']) # 1 sec in blocking mode
                    ClientSocket.setblocking(0)
                    print("trace- connected")
                except:
                    if (not (ClientSocket is None)):
                      ClientSocket.close()
                    ClientSocket = None
                    #print("no connection availlable for %s %i" % (str(GlobalParams['TraceSocket']), Count))
                    Count = Count+1
                    #time.sleep(0.2);
            
            if (not (ClientSocket is None)):
                try:
                  readable, writable, exceptional = select.select( [ClientSocket], [], [ClientSocket],0)
                  for s in readable:
                    chunk = s.recv( 2048)
                    Str=chunk.decode()
                    if (len(Str) >=2):
                      Str = Str[:-2]
                    if (len(Str) > 0):
                      #print( "+%s-" % Str)
                      print( Str)
                  for s in exceptional:
                    print ("exceptionnal")
                    foo = 1
                except:
                  print("trace- disconnected")
                  if (not (ClientSocket is None)):
                    ClientSocket.close()
                  ClientSocket = None
            ReadedChar = getch()
            if (None == ReadedChar):
              if (not (ClientSocket is None)):
                (TraceNowUs, TraceNowMs) = GetTimings()
                if (diff( TraceNowMs, TraceLastMs) > 2000):
                  (TraceLastUs, TraceLastMs) = (TraceNowUs, TraceNowMs)
                  try:
                    ClientSocket.send('L'.encode('utf-8'))
                  except:
                    print( "Failed to send alive check")
                    if (not (ClientSocket is None)):
                      ClientSocket.close()
                    ClientSocket = None
            elif ('q' == ReadedChar):
              # 'q' to quit this
              EndLoop = True
            else:
              if (not (ClientSocket is None)):
                try:
                  ReadedChar = ReadedChar.encode('utf-8')
                except:
                  foo=1
                try:
                  ClientSocket.send(ReadedChar)
                except:
                  print( "Failed to send char %s" % ReadedChar)
                  if (not (ClientSocket is None)):
                    ClientSocket.close()
                  ClientSocket = None
    


# https://steelkiwi.com/blog/working-tcp-sockets/
serversocket = None
clientsocket = None
GlobalParams['LogFileHandle']=False

def Trace( Msg):
  global serversocket
  global clientsocket
  global GlobalParams
  global TraceNoAccept
  global TraceChar
  totalsent = 0

  print(Msg)

  if (None == GlobalParams['TraceTTy']):
    try:
      GlobalParams['TraceTTy'] = open( "/dev/tty1",'w')
    except:
      print( "fail trace tty1 open")
      GlobalParams['TraceTTy'] = False
  if (GlobalParams['TraceTTy']):
    try:
      GlobalParams['TraceTTy'].write( "%s\n" % Msg)
    except:
      foo = 1
      print( "fail trace tty1 send")
      GlobalParams['TraceTTy'].close()
      GlobalParams['TraceTTy'] = None

  if(True==GlobalParams['LogFileName']):
      GlobalParams['LogFileName']=GlobalParams['BasePath']+"default.txt"
  if(not GlobalParams['LogFileHandle'] and GlobalParams['LogFileName']):
      try:
          # https://docs.python.org/3/library/functions.html#open
          GlobalParams['LogFileHandle'] = open( GlobalParams['LogFileName'],'a')
      except:
          print( "fail trace open %s" % str(GlobalParams['LogFileName']))
  if(GlobalParams['LogFileHandle']):
      try:
          Res=GlobalParams['LogFileHandle'].write( "%s\n" % Msg)
          GlobalParams['LogFileHandle'].flush()
          #TODO_LATER : size manage
      except:
          foo=1
          print( "fail trace file send")
          GlobalParams['LogFileHandle'].close()
          GlobalParams['LogFileHandle']=False

  if (GlobalParams['WithSocket']):
        # Send to a friend if any, do not block
        if (serversocket is None):
            serversocket = socket.socket( socket.AF_INET, socket.SOCK_STREAM)
            #bind the socket to a public host,
            # and a well-known port
            serversocket.bind( GlobalParams['TraceSocket'])
            print("trace- binded")
        if (not(serversocket is None) and (clientsocket is None)):
            #become a server socket
            serversocket.setblocking(0)
            serversocket.listen(5)
        if (not(serversocket is None) and (clientsocket is None)):
         # accept connections from outside
         # do not block
         try:
           (clientsocket, address) = serversocket.accept()
           clientsocket.setblocking(0)
           TraceNoAccept = False
         except:
           clientsocket = None
           if (not TraceNoAccept):
             print( "trace- no accept %s" % str(GlobalParams['TraceSocket']))
             TraceNoAccept = True
        
        if (not (clientsocket is None)):
            try:
              clientsocket.send( ( "%s\r\n" % Msg).encode('utf-8'))
            except:
              clientsocket.close()
              clientsocket = None
              print( "trace sock send fail")
            try:
                  readable, writable, exceptional = select.select( [clientsocket], [], [clientsocket],0.0001)
                  for s in readable:
                    chunk = s.recv( 2048)
                    Str=chunk.decode()
                    #if (len(Str) > 0 and '\n' == Str[len(Str)]):
                    #  Str = Str[:-1]
                    #if (len(Str) > 0 and '\n' == Str[len(Str)]):
                    #  Str = Str[:-1]
                    if (len(Str) > 0):
                      TraceChar = Str # TODO_LATER : char by char
                      #print( "+%s-" % Str)
                      #print( Str)
            except:
               #print("ERR- sock recv ko")
               print("trace- disconnected")
               if (not (clientsocket is None)):
                 clientsocket.close()
               clientsocket = None

def GuiCprPoint( CprX, CprY, Color="blue"):
  global GlobalParams

  if (GlobalParams['Gui']):
    Tx = CprX*(GlobalParams['Gui'].MyMx-20)/GlobalParams['CprMax']+10
    if (Tx < 0):
      Tx = 0
    if (Tx > GlobalParams['Gui'].MyMx):
      Tx = GlobalParams['Gui'].MyMx
    Ty = CprY*(GlobalParams['Gui'].MyMy-20)/GlobalParams['CprMax']+10
    if (Ty < 0):
      Ty = 0
    if (Ty > GlobalParams['Gui'].MyMx):
      Ty = GlobalParams['Gui'].MyMx
    GlobalParams['GuiList'].append(GlobalParams['Gui'].myDraw.create_line( Tx, Ty, Tx+1, Ty+1, fill=Color))
    GlobalParams['GuiList'].append(GlobalParams['Gui'].myDraw.create_line( Tx+1, Ty, Tx, Ty+1, fill=Color))
    while( len(GlobalParams['GuiList']) > 3000):
        GlobalParams['Gui'].myDraw.delete( GlobalParams['GuiList'].pop(0))
    GlobalParams['Gui'].update()

def GuiCprLine( CprX, CprY, DprX, DprY, Color="blue"):
  global GlobalParams

  if (GlobalParams['Gui']):
    Tx = CprX*(GlobalParams['Gui'].MyMx-20)/GlobalParams['CprMax']+10
    if (Tx < 0):
      Tx = 0
    if (Tx > GlobalParams['Gui'].MyMx):
      Tx = GlobalParams['Gui'].MyMx
    Ty = CprY*(GlobalParams['Gui'].MyMy-20)/GlobalParams['CprMax']+10
    if (Ty < 0):
      Ty = 0
    if (Ty > GlobalParams['Gui'].MyMx):
      Ty = GlobalParams['Gui'].MyMx
    TDx = DprX*(GlobalParams['Gui'].MyMx-20)/GlobalParams['CprMax']+10
    if (TDx < 0):
      TDx = 0
    if (TDx > GlobalParams['Gui'].MyMx):
      TDx = GlobalParams['Gui'].MyMx
    TDy = DprY*(GlobalParams['Gui'].MyMy-20)/GlobalParams['CprMax']+10
    if (TDy < 0):
      TDy = 0
    if (TDy > GlobalParams['Gui'].MyMx):
      TDy = GlobalParams['Gui'].MyMx
    GlobalParams['GuiList'].append(GlobalParams['Gui'].myDraw.create_line( Tx, Ty, TDx, TDy, fill=Color))
    GlobalParams['Gui'].update()

def GuiCprText( CprX, CprY, Txt, Color="blue"):
  global GlobalParams

  if (GlobalParams['Gui']):
    Tx = CprX*(GlobalParams['Gui'].MyMx-20)/GlobalParams['CprMax']+10
    if (Tx < 0):
      Tx = 0
    if (Tx > GlobalParams['Gui'].MyMx):
      Tx = GlobalParams['Gui'].MyMx
    Ty = CprY*(GlobalParams['Gui'].MyMy-20)/GlobalParams['CprMax']+10
    if (Ty < 0):
      Ty = 0
    if (Ty > GlobalParams['Gui'].MyMx):
      Ty = GlobalParams['Gui'].MyMx
    GlobalParams['GuiList'].append(GlobalParams['Gui'].myDraw.create_text(Tx,Ty,fill=Color,font="Times 7 italic bold",
                        text=Txt))
    GlobalParams['Gui'].update()

#difftime https://docs.python.org/3/library/datetime.html
def difftimeUs( t1, t2):
  if t2 > t1 :
    Res = t2-t1
  else :
    Res = t1-t2
  if (Res > 1000000/2):
    Res = 1000000-Res
  return( Res)

def diff( t1, t2):
   if t2 > t1 :
    return( t2-t1)
   else :
    return( t1-t2)
    
def sign(x):
  if (x>=0):
    return(1.0)
  return -1.0

def Vector( Pt1, Pt2):
   """ Construit un vecteur par deux points """
   #try:
   #   (Px1, Py1, Pz1) = Pt1
   #except :
   #   print "Debug"
   #   print "Pt1"
   #   print Pt1
   (Px1, Py1, Pz1) = Pt1
   (Px2, Py2, Pz2) = Pt2
   return( Px2-Px1, Py2-Py1, Pz2-Pz1)

def PerpendiculairePointDroite( Pt1, Droite):
   """ Resutltat H, projection perpendiculaire de Pt1 sur la droite """
   (Px1, Py1, Pz1) = Pt1
   (D1, D2) = Droite
   (Dx1, Dy1, Dz1) = D1   
   (Dx2, Dy2, Dz2) = D2
   X1 = Dx2 - Dx1
   Y1 = Dy2 - Dy1
   Z1 = Dz2 - Dz1
   XP1 = Px1 - Dx1
   YP1 = Py1 - Dy1
   ZP1 = Pz1 - Dz1
   k=(XP1*X1+YP1*Y1+ZP1*Z1)/(X1*X1+Y1*Y1+Z1*Z1)
   return( Dx1+k*X1, Dy1+k*Y1, Dz1+k*Z1)

def KPerpendiculairePointDroite( Pt1, Droite):
   """ K position de la projection, 0 en A, 1 en B """
   (Px1, Py1, Pz1) = Pt1
   (D1, D2) = Droite
   (Dx1, Dy1, Dz1) = D1   
   (Dx2, Dy2, Dz2) = D2
   X1 = Dx2 - Dx1
   Y1 = Dy2 - Dy1
   Z1 = Dz2 - Dz1
   XP1 = Px1 - Dx1
   YP1 = Py1 - Dy1
   ZP1 = Pz1 - Dz1
   try:
     k=(XP1*X1+YP1*Y1+ZP1*Z1)/(X1*X1+Y1*Y1+Z1*Z1)
   except:
     k=0.5 # possiblement c'est a la fois 0 et 1 en A et B et rien ailleurs
   return( k)

if (not(GlobalParams['MeRaspi'])):
    print( "WARN- gpio simulator engaged")
    class GPIOClass:
        def output(self, pin, val):
            self.GpioList[pin]=val
        HIGH=1
        LOW=0
        GpioList={}
    GPIO=GPIOClass()

# tools debug

# tools

def bChoose( TF, A, B):
  if (TF):
    return(A)
  return(B)

 # no blocking keyboard by default
def getch_isData():
  return False
getch_avail = False
def getch():
  return( None)
def getch_restore():
  return( True)

try: # try to define non blocking keyboard for linux
  old_settings = termios.tcgetattr(sys.stdin)
  # print (old_settings)

  def getch_restore():
    try:
      termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
    except:
      dummy=3

  if __name__ == "__main__":
    tty.setcbreak(sys.stdin.fileno())

  def getch_isData():
    return select.select([sys.stdin], [], [], 0.0001) == ([sys.stdin], [], [])

  def getch():
    if getch_isData():
      c = sys.stdin.read(1)
    else:
      c = None
    return( c)

  print( "with keyboard line entry linux style")
  getch_avail = True
except:
  print( "WARN: no keyboard line entry linux style")
  try:
    termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
  except:
    dummy=3
try: 
  if old_settings[6][5] == 0:
    print( "try patch AAA")
    old_settings[6][5] = '\x00'
  if old_settings[6][6] == 1:
    print( "try patch BBB")
    old_settings[6][6] = '\x01'
except:
  dummy=1

if not getch_avail:
  try:
    msvcrt.kbhit()
    def getch():
      if (msvcrt.kbhit()):
        Str = msvcrt.getch()
        try:
          Str = Str.decode()
        except:
          foo=1
        return(Str)
      return( None)
    getch_avail = True
    print( "with keyboard line entry window style")
  except:
    print("WARN: no getch win style")

def GetTimings():
  dt = datetime.now()
  LastUs = dt.second*1000000+dt.microsecond
  LastMs = (dt.minute*60+dt.second)*1000+LastUs/1000.0
  return( LastUs, LastMs)

def Smooth ( N, LastSmooth, New):
  """ Smoothing value, if N is 0 means direct value """
  return( (LastSmooth * N*1.0 + New)/(N+1)) 

def KeepMinMax ( N, VMinMax, NewValue):
  (ValueMin, ValueMax)= VMinMax
  """ recomend N of 5 """
  if( NewValue > ValueMax):
    ValueMax = Smooth ( N, NewValue, ValueMax)
  else :
    ValueMax = Smooth ( N, ValueMax, NewValue)

  if( NewValue < ValueMin):
    ValueMin = Smooth ( N, NewValue, ValueMin)
  else :
    ValueMin = Smooth ( N, ValueMin, NewValue)
  return(ValueMin, ValueMax)

#-------------- Serial
def SerialInitRound():
  """ discover serial devices """
  global GlobalParams

  SerialPorts=serial_tools_list_ports.comports()
  for SerialPort in SerialPorts:
        Found=False
        PortName= SerialPort[0]
        try:
            print( "try: %s"% PortName)
            myserial=serial.Serial(
                port=PortName,
                baudrate=115200,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                bytesize=serial.EIGHTBITS,
                timeout=0.1
                )
            if (DRV_ESPUSB == GlobalParams['Drive']):
              print( "wait: %s for DRV_ESPUSB"% PortName)
              #time.sleep(5)
              Resp=SerialReadAll( myserial, "Serial", 5000)
              Found = EspUsbAffect( Resp, PortName, myserial);
            else :
              print( "wait: %s for GrblSerial"% PortName)
              #time.sleep(5)
              Resp=SerialReadAll( myserial, "Serial", 5000)
              if ((not Found) and (not GlobalParams['GrblSerial']) and isinstance( Resp, str) and 'Grbl' in Resp):
                  Found=True
                  print("  Welcome grbl in '%s'" %(PortName))
                  GlobalParams['GrblSerial']=myserial
              if ((not Found) and (not GlobalParams['GrblSerial']) and isinstance( Resp, str) and '[VER' in Resp):
                  Found=True
                  print("  Welcome grbl in '%s'" %(PortName))
                  GlobalParams['GrblSerial']=myserial
              if ((not Found) and (not GlobalParams['TempSerial']) and isinstance( Resp, str) and 'Temp=' in Resp):
                  GlobalParams['TempSerial'] = myserial
                  print("  Welcome Temp in '%s'" %(PortName))
                  Found=True
              if ((not Found) and (not myserial in GlobalParams['EspUsbSerial']) and isinstance( Resp, str) and '#EspUsb' in Resp):
                  GlobalParams['EspUsbSerial'] = GlobalParams['EspUsbSerial'] + [myserial]
                  GlobalParams['EspUsbSerialNb'] = GlobalParams['EspUsbSerialNb']+1
                  print("  Welcome EspUsbSerial in '%s'" %(PortName))
                  Found=True
            if (not Found):
                print("  Not mine '%s'" %(PortName))
                myserial.close()
        except Exception as e:
            print( "not the expected candidate %s" % PortName)
            template = "An exception of type {0} occured. Arguments:\n{1!r}"
            message = template.format(type(e).__name__, e.args)
            print( message)
            foo=1
            #raise
  if (DRV_ESPUSB == GlobalParams['Drive']):
    return(('CRBL_AXEX1' in GlobalParams) and ('CRBL_AXEX2' in GlobalParams) and ('CRBL_AXEY' in GlobalParams) and ('CRBL_AXEZ' in GlobalParams))
  else :
    return(GlobalParams['GrblSerial'] and GlobalParams['TempSerial'])

def SerialInit():
  "try to get enough subparts to have a working crabouillon"
  Found = SerialInitRound();

  if (DRV_ESPUSB == GlobalParams['Drive'] and not(Found)):
    Found = SerialInitRound();
    
  if (Found):
    print( "All my friends are linked")
  
  return(Found)

def SerialPeek( MySerial, Cmt, TimeMaxMs=0):
    """ get from serial, time constraint, max TimeMaxMs allowed, bufferize and return the string upon cr|lf"""
    ResStr=""
    (LastUs, LastMs) = GetTimings()
    if (MySerial):
        MyEnd=False
        while(not MyEnd):
            Ch=MySerial.read() # supposed to have inter-char timeout
            if (not Ch):
                #MyEnd = True
                foo=1
            elif ('\n' == Ch):
                ResStr= ResStr+"\n"
            else:
                try:
                    ResStr= ResStr+Ch.decode()
                except:
                    foo=1 # why must we care with decode... the hell to those beardeds
            (NowUs, NowMs) = GetTimings()
            difft=diff(NowMs, LastMs)
            if ( difft >= TimeMaxMs):
                MyEnd = True
            #print( "%s-SerialPeek %i %fms %fms" %( Cmt, MyEnd, TimeMaxMs, difft))
    return( ResStr)

def SerialRecv( MySerial, Cmt, TimeoutSec=0.01):
    if (MySerial):
        (LastUs, LastMs) = GetTimings()
        MyEnd=False
        ResStr=""
        while (not MyEnd):
            (NowUs, NowMs) = GetTimings()
            Ch=MySerial.read() # supposed to have inter-char timeout
            if (not Ch):
                if (len(ResStr)):
                    MyEnd=True # receiced something and inter-char timeout
                if(diff(LastMs, NowMs)> TimeoutSec*1000):
                    MyEnd = True
            elif ('' == Ch):
                MyEnd = True
            elif ('\n' == Ch):
                MyEnd = True
            else:
                try:
                    ResStr= ResStr+Ch.decode()
                except:
                    foo=1 # why must we care with decode... the hell to those beardeds
        if(len(ResStr)):
            ResStr=ResStr.strip()
            Trace( '%s-SerialRecv<--\"%s\"' % (Cmt, ResStr))
        return (ResStr)
    else:
        return( '')

def SerialReadAll( MySerial, Cmt, DurationMs=100):
    """ read during DurationS seconds"""
    FullResp = ""
    MyEnd = False
    (FirstUs, FirstMs) = GetTimings()
    while(not MyEnd):
        (NowUs, NowMs) = GetTimings()
        RemainMS= NowMs- FirstMs
        if (RemainMS <0.0):
            RemainMS = 0.01
            MyEnd=True
        if (RemainMS > DurationMs):
            RemainMS = 0.01
            MyEnd=True
        Resp = SerialRecv( MySerial, Cmt, RemainMS/1000.0)
        if(len(Resp)):
            FullResp=FullResp+Resp
    return(FullResp)

def SerialSend( MySerial, Cmt, CommandStr, AutoEol=True):
    global GlobalParams
    if ( MySerial):
        if (AutoEol):
            StrSend=CommandStr + "\r\n"
        else:
            StrSend=CommandStr + ""
        MySerial.write( StrSend.encode('utf-8'))
        #Trace('%sSend-->\"%s\"' % (Cmt, CommandStr))
    
def SerialSendWait( MySerial, Cmt, Cmd, TimeoutSec=60):
    """ send a command and wait for ok """
    # TODO_HERE : end on error too
    Trace("%sSendWait for %f sec" % (Cmt, TimeoutSec*1.0))
    Found = False
    FullResp=SerialReadAll( MySerial, Cmt, 200) # empty the queue
    SerialSend( MySerial, Cmt, Cmd)
    # TimeoutSec
    (LastUs, LastMs) = GetTimings()
    MidMs = LastMs
    while(not Found):
        (NowUs, NowMs) = GetTimings()
        Resp=SerialRecv( MySerial, Cmt)
        if (isinstance( Resp, str)):
            if ( 'ok' in Resp):
                Found = True
                Trace("%sSendWait Ok After %f sec" % ( Cmt, diff(NowMs, LastMs)/1000.0))
                return(FullResp+Resp)
            if ( 'error' in Resp):
                Found = True
                return(Resp)
        if(diff(NowMs, LastMs) > TimeoutSec*1000):
            Trace( "%sSendWait timeout... %f sec" %( Cmt, diff(NowMs, LastMs)/1000.0))
            return("timeout")
        if (diff(NowMs, MidMs)> 30*1000):
            Trace( "%sSendWait retry... %f sec" %( Cmt, diff(NowMs, LastMs)/1000.0))
            SerialSend( MySerial, Cmt, Cmd)
            MidMs = NowMs
    return( "nop")
    
#-------------- grbl

def GrblInit():
    """ Find an arduino with grbl (cn gcode driver) inside if not already got one """
    global GlobalParams
    
    if (GlobalParams['GrblSerial']):
        Trace("already got grbl")
        return(GlobalParams['GrblSerial'])

    SerialInit()
    if (GlobalParams['GrblSerial']):
        GrblSend("$X")
    return(GlobalParams['GrblSerial'])

def GrblProcess( GrblStr):
    if (GlobalParams['GrblSerial']):
        """ pick up what is of some interrest in a grbl result (alarm) """
        if (isinstance( GrblStr, str)):
            #Trace("Received str %s-" % GrblStr)
            if (GrblStr.find("ALARM:") >= 0):
                GlobalParams['GrblErr']=9
            if (GrblStr.find("<Alarm|") >= 0):
                GlobalParams['GrblErr']=9
            if (GrblStr.find("error") >= 0):
                Trace("-- Err received")
                RespList=GrblStr.replace(':',' ').replace('\r',' ').split(' ')
                RespNums=[int(s) for s in RespList if s.isdigit()]
                for error in RespNums:
                   if (GlobalParams['GrblErr']==9):
                      #GlobalParams['GrblErr']=9
                      foo = 1
                   else:
                      if error in [1,9]:
                          GlobalParams['GrblErr']=9
                      elif error in [35]:
                          foo=1
                      else:
                          GlobalParams['GrblErr']=error
    # TODO_LATER              GlobalParams['CurrentPosX']
    # TODO_LATER              GlobalParams['CurrentPosY']

def GrblRecv( TimeoutSec=0.01):
    """ receive from grbl and catch errors """
    if (GlobalParams['GrblSerial']):
        ResStr=SerialRecv( GlobalParams['GrblSerial'], 'Grbl', TimeoutSec)
        GrblProcess( ResStr)
        return( ResStr)

def GrblReadAll( DurationMs=100):
    if (GlobalParams['GrblSerial']):
        ResStr = SerialReadAll( GlobalParams['GrblSerial'], 'Grbl', DurationMs)
        GrblProcess( ResStr)
        return( ResStr)

def GrblSend( CommandStr):
    if (GlobalParams['GrblSerial']):
        SerialSend( GlobalParams['GrblSerial'], 'Grbl', CommandStr)
        
def GrblSendWait( Cmd, TimeoutSec=60):
    if (GlobalParams['GrblSerial']):
        ResStr=SerialSendWait( GlobalParams['GrblSerial'], 'Grbl', Cmd, TimeoutSec)
        GrblProcess( ResStr)
        return( ResStr)

def GrblClose():
    if (GlobalParams['GrblSerial']):
        GlobalParams['GrblSerial'].close()
        GlobalParams['GrblSerial']=False

def GrblIsIdle( WaitMs=0, Strict=0):
    if (GlobalParams['GrblSerial']):
        """ return true if grbl is idle (no more instruction to process and awaiting, 
            if gentle asked wait some milliseconds for grbl to be idle"""
        Continue=True
        while(Continue):
            SerialSend( GlobalParams['GrblSerial'], 'Grbl', "?", AutoEol=False)
            ResStr=GrblRecv( TimeoutSec=0.001);
            if (ResStr.find("<Idle|") >= 0):
                return( True)
            if (not Strict):
                if (ResStr.find("<Alarm|") >= 0):
                    return( True) # dilemna ... somehow it's not moving like Idle... 
            if(WaitMs <= 0):
                return( False)
            if(WaitMs > 0):
                time.sleep(1)
                WaitMs = WaitMs -1000
                Trace("GrblIsIdle sill %i to wait" % WaitMs)
            else:
                time.sleep(WaitMs/1000.0)

def GrblExist():
    if (GlobalParams['GrblSerial']):
        return( True)
    return( False)
  
  
#---------------------- Temp

def TempProcess( ResStr):
    IdxSt=ResStr.find("Temp=[")
    IdxNd=-1
    if (IdxSt>=0):
        IdxNd=ResStr[IdxSt:].find("]")
    if (IdxNd>=0):
        try:
            ResStr = ResStr[IdxSt+5:IdxSt+IdxNd+1]
            Temps=eval(ResStr)
            Trace("Temp:%s"% str(Temps))
            Trace("Temp:%s"% str(Temps))
            GlobalParams['TermalOk']=True
            for temp in Temps:
                if (temp < -100):
                    Trace("Temp probe disconnected - must reconnect")
                    GlobalParams['TermalOk']=False
                if (temp > 70):
                    Trace("time to cooldown")
                    GlobalParams['TermalOk']=False
                # over 80 another external device is supposed to cut off power
        except:
            # seen : raspi failed to sent a ',' in the string...
            GlobalParams['TermalOk']=False
            #if (not GlobalParams['AutoRecover']):
            #    raise

TempRecvLastMs=0
TempRecvBuff=""
def TempRecv( TimeoutSec=0.001):
    global TempRecvLastMs
    global TempRecvBuff
    
    ResStr=""
    (LastUs, LastMs) = GetTimings()
    Res = SerialPeek( GlobalParams['TempSerial'], 'Temp', 5)# 5ms
    TempRecvBuff = TempRecvBuff+Res
    Idx = TempRecvBuff.rfind("\n") # search from the end
    if( Idx < 0):
        Idx = TempRecvBuff.rfind("\r")
    if (Idx >= 0):
        ResStr=TempRecvBuff[:Idx+1]
        TempRecvBuff=TempRecvBuff[Idx+1:]

    (NowUs, NowMs) = GetTimings()
    # Trace("TempRecv After %fs each %fs - %s - %s" % ( diff(NowMs, LastMs)/1000.0, diff(NowMs, TempRecvLastMs)/1000.0,  TempRecvBuff, ResStr))
    TempRecvLastMs = NowMs
    return( ResStr)

def TempClose():
    global GlobalParams

    if (GlobalParams['TempSerial']):
        GlobalParams['TempSerial'].close()
        GlobalParams['TempSerial']=False

#-------------- EspUsb

def EspUsbInit():
    """ Find an Esp with some motor - sensor capabilities """
    global GlobalParams
    
    SerialInit()

    if ([] == GlobalParams['EspUsbSerial'] ):
        Trace("no ESP effecter found")
    else :
        Trace("found %i ESP effecter.e.s" % GlobalParams['EspUsbSerialNb'])

def EspUsbExist():
    global GlobalParams

    if (0 == GlobalParams['EspUsbSerialNb']):
        return( False)
    return( True)

def EspUsbAffect( Resp, PortName, myserial):
    """ discover serial devices """
    global GlobalParams
    Found=False
    
    if(isinstance( Resp, str) and 'CRBL_AXEX' in Resp):
      if (not('CRBL_AXEX1' in GlobalParams)):
        print("  Welcome AXEX1 in '%s'" %(PortName))
        GlobalParams['CRBL_AXEX1'] = myserial
        Found=True
      elif (not( 'CRBL_AXEX2' in GlobalParams)):
        print("  Welcome AXEX2 in '%s'" %(PortName))
        GlobalParams['CRBL_AXEX2'] = myserial
        Found=True
      else :
        print("  too many AXEX ... TODO_LATER : update code to support" %(PortName))
    if(isinstance( Resp, str) and 'CRBL_AXEY' in Resp):
      if (not( 'CRBL_AXEY' in GlobalParams)):
        print("  Welcome AXEY in '%s'" %(PortName))
        GlobalParams['CRBL_AXEY'] = myserial
        Found=True
      else :
        print("  too many AXEY ... TODO_LATER : update code to support" %(PortName))
    if(isinstance( Resp, str) and 'CRBL_AXEZ' in Resp):
      if (not( 'CRBL_AXEZ' in GlobalParams)):
        print("  Welcome AXEZ in '%s'" %(PortName))
        GlobalParams['CRBL_AXEZ'] = myserial
        Found=True
      else :
        print("  too many AXEZ ... TODO_LATER : update code to support" %(PortName))

    return( Found)

def EspUsbSend( GNum, BX, BY, BZ, BF):
  "Send to our USB effectors - GNum type of move TODO_LATER - BF Speed TODO_LATER"
  global GlobalParams
  global GoNext

  print( "EspUsbSend( GNum:%i, BX:%i, BY:%i, BZ:%i, BF:%i)\n" %( GNum, BX, BY, BZ, BF));
  if ('CRBL_AXEX1' in GlobalParams):
      SerialSend( GlobalParams['CRBL_AXEX1'], 'CRBL_AXEX1', "G0 X %i" % BX)
  if ('CRBL_AXEX2' in GlobalParams):
      SerialSend( GlobalParams['CRBL_AXEX2'], 'CRBL_AXEX2', "G0 X %i" % BX)
  if ('CRBL_AXEY' in GlobalParams):
      SerialSend( GlobalParams['CRBL_AXEY'], 'CRBL_AXEY', "G0 X %i" % BY)
  if ('CRBL_AXEZ' in GlobalParams):
      SerialSend( GlobalParams['CRBL_AXEZ'], 'CRBL_AXEZ', "G0 X %i" % BZ)
  GlobalParams['GoNext'] = False
  
def EspUsbRecv():
  global GlobalParams
  global GoNext
  
  time.sleep( 4.5) # TODO_LATER ASP should send 'go' and etc ... now the do the move in 5 seconds - see GcodeG ... WishDTms , 5000
  GlobalParams['GoNext']=True
  TimeoutSec = 0.02
  if ('CRBL_AXEX1' in GlobalParams):
    ResStr=SerialRecv( GlobalParams['CRBL_AXEX1'], 'CRBL_AXEX1', TimeoutSec)
  if ('CRBL_AXEX2' in GlobalParams):
    ResStr=SerialRecv( GlobalParams['CRBL_AXEX2'], 'CRBL_AXEX2', TimeoutSec)
  if ('CRBL_AXEY' in GlobalParams):
    ResStr=SerialRecv( GlobalParams['CRBL_AXEY'], 'CRBL_AXEY', TimeoutSec)
  if ('CRBL_AXEZ' in GlobalParams):
    try:
        ResStr=SerialRecv( GlobalParams['CRBL_AXEZ'], 'CRBL_AXEZ', TimeoutSec)
    except serial.SerialException:
        ResStr='AXEZ Disconnection or other communication line error'

#---------------------- ACT_

def Act_TakePhoto( FileName, WorkDurationSec):
  """ try to take photo """
  Trace("gpio in script take photo")
  os.system( GlobalParams['BasePath']+"TakePhoto.sh %s %i" % (FileName, WorkDurationSec))

def Act_PlaySound( Snd):
  """ square a gpio to trigger a sound """
  global GlobalParams

  Trace( "  PlaySound( %i)" % Snd)
  if (Snd < 1):
    Snd = 1
  if (Snd > len(GlobalParams['TsunamiLines'])):
    Snd = len(GlobalParams['TsunamiLines'])
  GpioLine = GlobalParams['TsunamiLines'][ Snd-1]
  try:
    GPIO.output( GpioLine, GPIO.HIGH)
    time.sleep(0.5)
    GPIO.output( GpioLine, GPIO.LOW)
  except :
    if (GlobalParams['MeRaspi']):
      Trace("  ERR- Act_Playsound (%i)- failed" % Snd)
      if (not GlobalParams['AutoRecover']):
        raise

def Act_MoveTool( BZ, ToolNum = 1, TimeMoveS="default"):
  """ BZ>0 Up, <0 down   https://deusyss.developpez.com/tutoriels/RaspberryPi/PythonEtLeGpio/"""
  global GlobalParams
  global odrv0
  Run = False

  #Trace( "Act_MoveTool( BZ=%i, ToolNum=%i) CurrentZ:%i CurrentTool:%i" %( BZ, ToolNum, GlobalParams['CurrentZ'], GlobalParams['CurrentTool']))
  if (DRV_ESPUSB == GlobalParams['Drive']):
      return

  ToolNum = int(ToolNum)
  if (BZ < 0 and ToolNum == 0):
    ToolNum = 1

  if ("default"==TimeMoveS):
      TimeMoveS = GlobalParams['TimeToolMvS']
      # by default move only if not already done
  else:
      Run = True # want to spend a specific amount of time on this... 
      Trace("  Tool %i small time! (z:%f, %i s)" % (ToolNum, BZ, TimeMoveS))

  try:
    if ((0 ==GlobalParams['CurrentTool'] and 0!=ToolNum and GlobalParams['CurrentZ']<0) or (BZ > 0 and GlobalParams['CurrentZ'] < 0)):
      Trace("  Tools up! (%i s)" % TimeMoveS)
      Run = True
    elif (BZ < 0 \
          and (GlobalParams['CurrentZ'] > 0 or ToolNum != GlobalParams['CurrentTool'])):
      Trace("  Tool %i move down! (%i s)" % (ToolNum, TimeMoveS))
      Run = True
    else:
      foo = 1
      #Trace( "  Tools Already moved")

    if (Run):
      if (GrblExist()):
          GrblReadAll()
          if(9 != GlobalParams['GrblErr']):
              GrblIsIdle( 30000) # time for last moves to perform
              GrblIsIdle( 30000)
              GrblIsIdle( 30000)
              #GrblSendWait("G04 P0", 2.0)
      if (DRV_ESPUSB == GlobalParams['Drive']):
          GrblReadAll()
          if(9 != GlobalParams['GrblErr']):
              GrblIsIdle( 30000) # time for last moves to perform
              GrblIsIdle( 30000)
              GrblIsIdle( 30000)
              #GrblSendWait("G04 P0", 2.0)
      GPIO.output( GpioTool1, GPIO.LOW) # Defines tool direction by default ... up
      GPIO.output( GpioTool2, GPIO.LOW)
      if (BZ < 0):
        if (1 == ToolNum):
          GPIO.output( GpioTool1, GPIO.HIGH)
        if (2 == ToolNum):
          GPIO.output( GpioTool2, GPIO.HIGH)
      GPIO.output( GpioToolUp, GPIO.HIGH) # start move
      if (not GlobalParams['Simul']):
          time.sleep( TimeMoveS)
      GPIO.output( GpioToolUp, GPIO.LOW)
      GPIO.output( GpioTool1, GPIO.LOW)
      GPIO.output( GpioTool2, GPIO.LOW)
      Trace("Tools move supposed done")
      GlobalParams['CurrentTool'] = ToolNum+0
      GlobalParams['CurrentZ'] = BZ+0.0
      if (GrblExist() or DRV_ESPUSB == GlobalParams['Drive']):
          GrblIsIdle( 1000)
          if(9 == GlobalParams['GrblErr']):
              Trace("Tools move trigg correction")
              GlobalParams['GrblErr']=False
              if ("timeout" == GrblSendWait("$X")):
                  Trace("timeout on grbl trigg correction")
                  GrblClose()
                  GrblInit()
  except :
    if (GlobalParams['MeRaspi']):
      Trace("ERR- Act_MoveTool- Tool Move failed")
      if (not GlobalParams['AutoRecover']):
        raise
    else:
      GlobalParams['CurrentTool'] = ToolNum+0
      GlobalParams['CurrentZ'] = BZ+0.0

def Vect2D( A, B):
  (AX, AY) = A
  (BX, BY) = B
  return( BX-AX, BY-AY )

def Vect2DNorm( V):
  (VX,VY) = V
  return( math.sqrt(VX*VX+VY*VY))
  
def Vect2DRenorm( V, L):
  (VX,VY) = V
  N =  Vect2DNorm( V)
  if (N < 0.0001):
    N = 0.0001 # this is the real world U Know, divide by too small and essentially get errors
  return( VX*L/N, VY*L/N )
  
def Vect2DMult( V, L):
  (VX,VY) = V
  return( VX*L, VY*L )
  
def  Vect2DAdd( P, V):
  (PX, PY) = P
  (VX, VY) = V
  return( VX+PX, VY+PY) 

def GcVal( GcodeStr):
    """ Gcode like G01 of X123.456 """
    try:
      Res= float(GcodeStr[1:])
    except:
        if (not GlobalParams['AutoRecover']):
            print( "No val in \"%s\"" % GcodeStr);
        Res = False
    return Res

def NiceQuit():
    #Trace( "TODO_LATER kill properly")

    GrblClose()
    TempClose()

    try:
        getch_restore() # or face messy command line after crash
    except:
        foo=1


def GpioSetup():
  """ configure gpio in out """
  global GlobalParams
  try:
    defaultStop=GPIO.PUD_UP
    GPIO.setmode(GPIO.BOARD)
    # for dev
    GPIO.setup( GpioToolUp, GPIO.OUT, initial=GPIO.LOW)# Tool
    GPIO.setup( GpioTool1, GPIO.OUT, initial=GPIO.LOW)# Tool
    GPIO.setup( GpioTool2, GPIO.OUT, initial=GPIO.LOW)# Tool

    for GpioLine in GlobalParams['TsunamiLines'] :
        GPIO.setup( GpioLine, GPIO.OUT, initial=GPIO.LOW)
    for IoNum in GlobalParams['ExtTrig']:
        if (IoNum < 100):
            GPIO.setup( IoNum, GPIO.IN, pull_up_down=defaultStop)
            GlobalParams['ExtTrig'][IoNum]=GPIO.input( IoNum)
            
  except:
    if (GlobalParams['MeRaspi']):
      Trace( "ERR- failed to setup Gpio, maybe stoppers Ko (min, max), homing compromised")
      if (not GlobalParams['AutoRecover']):
        raise

def PoolingLoop():
    """ acctions to try each loop (no act, just watch) """
    if (GlobalParams['OscServer']):
        GlobalParams['OscServer'].handle_request()

    ResStr=TempRecv()
    TempProcess( ResStr)

    if (GrblExist() or DRV_ESPUSB == GlobalParams['Drive']):
        foo=1 # TODO_LATER

atexit.register( NiceQuit) # stop and restore keyboard on crash

def MachineRun():
  """ main loop, drive the motors and try to draw as expected """ 
  global GlobalParams
  global TimeSliceS
  global old_settings
  global CorrX
  global CorrY
  global TraceChar
  global odrv0
  global StopXMin
  global StopXMax
  global StopYMin
  global StopYMax


  # setup
  
  DriveMethod = 1
  GcodeFileHdl = False;
  IdxParamList = 0
  Comment=""

  LastShowMs = 0
  TimeSliceUs = 0
  (TimeSliceSMin, TimeSliceS, TimeSliceSMax)= (0, 0, 0) #   TimeSliceUs = 0 but unit is in Seconds
  LastTimeSliceMs = 0
  ( VRMin, VR, VRMax) = (0,0,0)
  CurrentAccelX = 0
  CurrentAccelY = 0
  ( kX, kY) = ( 0, 0)
  ( CSX, CSY) = ( 0,0)

  ( CurrentSpeedXMin, CurrentSpeedXMax) = ( 0.0, 0.0)
  ( CurrentSpeedYMin, CurrentSpeedYMax) = ( 0.0, 0.0)

  WishedSpeedX = 1000
  WishedSpeedY = 1000
 
  AliveX = 1000
  AliveY = 1000
  FileName = ""
  FileLineCount = 0

  WishedMaxSpeedX = 1000
  WishedMaxSpeedY = 1000
  #Delta = 170 # precision : the dist that is difficult to go below... probab the dist between 2 coils
  Delta = 250
  GoNext = True # take a first instruction
  AtEnd = True
  FileList = []
  FilePath=GlobalParams['BasePath']+"spool_todo/*.ngc"
  FileCount = 0
  FileEnded = False # not even started, will trigger photo
  
  Trace( "1.0 Gcode is %f Cpr, is %f meters(%f mm)" % (GlobalParams['GcodeToCpr'], GlobalParams['GcodeToMeters'], GlobalParams['GcodeToMeters']*1000))
  Trace( "    CprMax %f, size %fm, %f m/Cpr" % (GlobalParams['CprMax'], GlobalParams['SizeM'], GlobalParams['CprToMeters']))

  (LastUs, LastMs) = GetTimings()

  GpioSetup()
  
  # warning : volts
  # raspi config pour ssid-password
  
  AZ = 5
  BZ = 5 # tool heigh, 0 is touch, -1 in in the dust

  if (DRV_GRBL == GlobalParams['Drive'] or DRV_ESPUSB == GlobalParams['Drive']):
      GrblInit()
      AX=0.0
      BX=0.0
      AY=0.0
      BY=0.0
      Dx=0.0
      Dy=0.0

  Act_MoveTool( 5, 0) # hands up

  (NowUs, NowMs) = GetTimings()
  (LastUs, LastMs) = (NowUs, NowMs)

  AX=0.0
  BX=0.0
  AY=0.0
  BY=0.0
  AF=0.0
  BF=GlobalParams['TypicalBF']
  AT = 1
  BT = 1 

  # A first file to test machine
  if 1:
    FileName = GlobalParams['BasePath']+"setup.ngc"
    try:
        GcodeFileHdl = open( FileName, "r")
        Trace( 'SETUP Got file "%s"' % (FileName))
        FileCount = FileCount + 1
        FileLineCount = 0
    except:
        Trace( 'SETUP failed to open file "%s"' % FileName)
        GcodeFileHdl = False
        FileName = ''
    EndOfFile = False
    LineCnt = 0; # local line count

  # loop
  while (True) :
  
    #print("----- cycle start ----")
   
    #state

    #  autotuning
    #  running
    #  toconnect -> un petit temps

    if (GoNext and FileEnded):
      # whatever to do when file is done (maybe on a stuff in GCode or will take at end of clear ...)
      Act_TakePhoto( FileName, 0)
      FileEnded = False;

    # get inputs
    #  as printer
    #  a file
    if (GoNext and "RUN" == GlobalParams['State']):
      if (len(FileList)<=0):
         try:
           FileList = glob.glob(FilePath)
           FileList.sort()
           if (len(FileList)<=0 and GlobalParams['ErrNoFileCnt'] < 3):
               Trace( 'no file in "%s"' % FilePath)
               GlobalParams['ErrNoFileCnt'] = GlobalParams['ErrNoFileCnt'] + 1
         except:
           FileList = []
           if ( GlobalParams['ErrNoFileCnt'] < 3):
               Trace( 'failed to list files in "%s""'% FilePath)
               GlobalParams['ErrNoFileCnt'] = GlobalParams['ErrNoFileCnt'] + 1
      while (len(FileList)>0 and not GcodeFileHdl):
         FileName = FileList[0]
         FileList = FileList[1:]
         GlobalParams['ErrNoFileCnt'] = 0
         try:
           GcodeFileHdl = open( FileName, "r")
           Trace( 'Got file "%s"' % (FileName))
           FileCount = FileCount + 1
           FileLineCount = 0
         except:
           Trace( 'failed to open file "%s"' % FileName)
           GcodeFileHdl = False
           FileName = ''
      EndOfFile = False
      LineCnt = 0; # local line count
      while(GcodeFileHdl and GoNext ): # TODO_LATER: and LineCnt < 10
        LineStr = GcodeFileHdl.readline();
        FileLineCount = FileLineCount+1
        LineCnt = LineCnt+1
        if('' == LineStr):
          GcodeFileHdl.close()
          GcodeFileHdl = False
          # TODO_LATER if required os.system( 'mv "%s" "spool_done/%s"' % (FileName, GlobalParams['BasePath'], FileName.split('/')[-1]))
          AtEnd = True
          FileEnded = True
        else:
          while( len(LineStr) > 0 and( LineStr[-1:] == '\r' or LineStr[-1:] == '\n' or LineStr[-1:] == ' ')):
            LineStr = LineStr[:-1]
          LineSplit=LineStr.split(" ")

        Comment = "file %i l:%i " % (FileCount, FileLineCount)
        if (not len(LineSplit[0])):
          Dummy = 0 # don't care empty lines
          Comment = ""
        elif( LineSplit[0][0]=="("):
          Comment += " " + LineStr
        elif( LineSplit[0][0]=="W"): # W for the sound
            try:
              Val = GcVal( LineSplit[0])
              Act_PlaySound(int(Val))
              GoNext = True
              Trace("Gcode sound cmd Val%i" % Val)
            except:
              Trace("Gcode sound cmd failed")
              if (GlobalParams['MeRaspi']):
                if (not GlobalParams['AutoRecover']):
                  raise
        elif( LineSplit[0][0]=="T"):
            GT = GcVal( LineSplit[0])
            #GT = "none"
            #for Cmd in LineSplit:
            #  if(Cmd[0] == 'T'):
            #    GT = GcVal( Cmd)
            if ("none" != GT):
              BT = copy.copy(GT)
            Trace("Gcode Tool cmd detected, GT:%i, BT:%i"%(BT,GT))
            GoNext = True
        elif( LineSplit[0][0]=="M"):
            GNum = "none"
            PNum = "none"
            SNum = "none"
            ENum = "none"
            for Cmd in LineSplit:
                if (len(Cmd)):
                    if(Cmd[0] == 'M'):
                        GNum = GcVal( Cmd)
                    if(Cmd[0] == 'P'):
                        PNum = GcVal( Cmd)
                    if(Cmd[0] == 'S'):
                        SNum = GcVal( Cmd)
                    if(Cmd[0] == 'E'):
                        ENum = GcVal( Cmd)
            if ("none" == GNum): # bad format gor GCode, expect "Gxx"
              foo = 1
            elif (226 == GNum): # http://marlinfw.org/docs/gcode/M226.html
                if ("none"==PNum):
                    PNum=GpioExtTrig1
                if ("none"==SNum):
                    SNum=1
                # TODO_LATER : S<..., 2(trig)...>
                Comment = Comment+"M226 - Wait for Pin State P<pin num:%i> S<State 0(low),1(up):%i>" % (int(PNum), int(SNum))
                if PNum in GlobalParams['ExtTrig']:
                    if (PNum >=100):
                        Trigg = False
                        Trace( "Wait ExtTrig %i" % PNum)
                        while (not Trigg):
                            Trig = GlobalParams['ExtTrig'][PNum]
                            PoolingLoop()
                            time.sleep(1)
                    else:
                        Trace(Comment)
                        Trace("Pause: en attente du déclenchement par le spectateur")
                        Comment=""
                        IoVal=int(GPIO.input( int(PNum)))
                        Trace( "got %i expect %i" %(IoVal, SNum));
                        while( IoVal != int(SNum)):
                            Trace( "PNum%i is %i, not the %i expected" %(PNum, IoVal, SNum));
                            PoolingLoop()
                            Trace("Pause: en attente du déclenchement par le spectateur")
                            time.sleep(0.5)
                            IoVal=int(GPIO.input( int(PNum)))
                else:
                     Trace( "ExtTrig %i not availlable" % PNum)
        elif( LineSplit[0][0]=="G"):
            Comment += "GCODE "
            # https://all3dp.com/g-code-tutorial-3d-printer-gcode-commands/
            # https://www.simplify3d.com/support/articles/3d-printing-gcode-tutorial/
            # G00 rapid motion
            # G01 controlled motion
            # G02 ??
            # G03 set plane
            # wtf, move if X and Y inside
            GNum = "none"
            GX = "none"
            GY = "none"
            GZ = "none"
            GF = "none"
            GT = "none"
            GP = "none"
            for Cmd in LineSplit:
                if (1 == len(Cmd)): # TODO_LATER support weird Gcode
                    Trace("Warn - input file should have no space between coordinate '%s' and value for l.%i '%s'" % (Cmd, FileLineCount, LineStr))
                if (len(Cmd)):
                    if(Cmd[0] == 'G'):
                        GNum = GcVal( Cmd)
                    if(Cmd[0] == 'X'): # in mm maybe
                        GX = GcVal( Cmd)*GlobalParams['GcodeToCpr']
                        if (GX > GlobalParams['CprMax']):
                            GX=GlobalParams['CprMax']
                    if(Cmd[0] == 'Y'):
                        GY = GcVal( Cmd)*GlobalParams['GcodeToCpr']
                        if (GY > GlobalParams['CprMax']):
                            GY=GlobalParams['CprMax']
                    if(Cmd[0] == 'Z'):
                        GZ = GcVal( Cmd) # Z is not counted in cpr, somehow only the sign matters
                    if(Cmd[0] == 'F'): #TODO_LATER This speed must always specified in units of mm/min -> Cpr.s-1
                        GF = GcVal( Cmd) # raw from file so it's easier to tune for the one who wrote the file
                    if(Cmd[0] == 'T'): # T1:tool 1, T2:tool 2
                        GT = GcVal( Cmd)
                    if(Cmd[0] == 'P'): # time to wait in ms
                        GP = GcVal( Cmd)
            # TODO_LATER G90 absolute, G91 relatives
            if ("none" == GNum): # bad format gor GCode, expect "Gxx"
              foo = 1
            elif (4 == GNum): # G04 pause
                Comment = "Pausing in %s " % LineStr
                if ("none"!=GP and "none" != GT and "none" != GZ):
                    BZ = copy.copy(GZ)
                    BT = copy.copy(GT)
                    Act_MoveTool( BZ, BT, GP/1000.0)
                elif("none"!=GP):  
                    time.sleep(GP/1000.0)
            elif( 28 == GNum):
                # G28 X Y ; home X and Y axes
                Comment += ("Homing")
                BF = GlobalParams['TypicalBF']
                GlobalParams['CurrentPosX'] = 0
                GlobalParams['CurrentPosY'] = 0
                if (GrblExist() or DRV_ESPUSB == GlobalParams['Drive']):
                    GrblReadAll()
                    GrblIsIdle( 30000) # time for last moves to perform
                    GrblIsIdle( 30000)
                GlobalParams['State']="HOMING"
            elif (GX!="none" or GY!="none" or GZ!="none" or GF!="none"):
              if ("none"==GX):
                GX = BX+0.0 
              if ("none"==GY):
                GY = BY+0.0 
              if ("none"==GZ):
                GZ = BZ+0.0
              if ("none"==GF):
                GF = BF+0.0 
              ( AX, AY, AZ, AF)= ( BX + 0.0, BY + 0.0, BZ + 0.0, BF + 0.0)
              ( BX, BY, BZ, BF) = (GX + 0.0, GY + 0.0, GZ + 0.0, GF + 0.0)
              GuiCprPoint( BX, BY, "Yellow")
              GoNext = False;
              AtEnd = False; # will keep last pos
              GuiCprText( BX, BY, "l.%i" % FileLineCount, Color="blue")
              Mod = False
              if (Mod):
                  if (3 == GNum): # TODO_LATER : just replace instead of rewrite
                      GNum= 1
                  CommandStr="G%2.2i X%4.3f Y%4.3f F%4.3f" %( GNum, BX, BY, BF)
              else:
                  CommandStr = LineStr
              Comment = Comment + "OK: go '%s' in '%s'" % ( CommandStr, LineStr)
              if (DRV_ESPUSB == GlobalParams['Drive']):
                  EspUsbSend( GNum, GX, GY, GZ, BF)
              elif (GrblExist()):
                  GrblSend( CommandStr)# TODO_HERE
              #Comment = ""
            else:
              Comment = Comment + "no X Y Z F in '%s'" % ( LineStr)
            if ("none" != GT):
              BT = copy.copy(GT)
        else:
          Comment = Comment + ( "GCODE full ignored-'%s'" % ( LineStr))
        if (Comment and len(Comment)):
          Trace(Comment)
          Comment=""
        if (LineCnt > 10):
          LineCnt = 0
          time.sleep(0.001) # give time for other threads like the print one to not saturate
    #  a socket
    # INPUT keyboard
    ReadedChar = getch()
    if (None == ReadedChar):
      ReadedChar = TraceChar
      TraceChar = False
    if (False == ReadedChar):
      #Trace("No char")
      nop = 3
    elif ("Q" == ReadedChar or "q" == ReadedChar):
      Trace("char %s" % ReadedChar)
      NiceQuit() # called by quit but sadly
      quit();
    elif ("D" == ReadedChar or "d" == ReadedChar):
      Trace( crash_to_test)
    elif ("H" == ReadedChar or "h" == ReadedChar):
      GlobalParams['State']="HOMING"
      GoNext=True
    elif ("T" == ReadedChar or "t" == ReadedChar):
      if( GlobalParams['State']=="TUNE"):
        GlobalParams['State']="RUN"
      else:      
        GlobalParams['State']="TUNE"
    elif ("V" == ReadedChar):
      if(IdxParamList < len(GlobalParams['ParamList'])):
        Val = BF+0.1 # TODO_LATER : remove once checked
        ValStr = GlobalParams['ParamList'][IdxParamList]
        Str = "Val = %s" % ValStr
        myCode = compile( Str, '<string>', 'exec')
        eval(myCode)
        Val = Val*1.2+100
        BF = BF*1.2+100
        #http://www.python-simple.com/python-langage/evaluation.php
        Str = "%s = %.40f" % ( ValStr,  Val)
        myCode = compile( Str, '<string>', 'exec')
        eval(myCode)
        Trace("EXEC- %s" % Str)
      else:
        Trace("ERR- Bad Idx")
    elif ("v" == ReadedChar):
      if(IdxParamList < len(GlobalParams['ParamList'])):
        ValStr= GlobalParams['ParamList'][IdxParamList]
        Val = eval(ValStr)
        Val = Val*0.7
        BF = BF*0.7
        Str = "%s = %.40f" % (ValStr,  Val)
        myCode = compile( Str, '<string>', 'exec')
        eval(myCode)
        Trace("EXEC- %s" % Str)
      else:
        Trace("ERR- Bad Idx")
    elif ("k" == ReadedChar):
      if (IdxParamList+1 >= len(GlobalParams['ParamList'])):
        IdxParamList = 0
      else:
        IdxParamList = IdxParamList +1
    else:
      Trace("ignored char %s" % ReadedChar)
      nop = 3
    
    # TUNE move a little to test system
    if (GoNext and "TUNE" == GlobalParams['State']):
      Trace( "Next")
      ( AX, AY)= ( BX + 0.0, BY + 0.0)
      if (BX > 500):
         BX = 0
         BY = 0
      else :
        BX = GlobalParams['SizeM']/GlobalParams['CprToMeters']
        BY = GlobalParams['SizeM']/GlobalParams['CprToMeters']/3
        #BY = 0.0
      if ( BF < Epsilon):
        BF = GlobalParams['TypicalBF']
      Trace( "%s to X:%i Y:%i"% ( GlobalParams['State'], BX, BY))
      GoNext = False;
      AtEnd = False; # will keep last pos

    # "HOMING" find min by itself (TODO_LATER: max later on)
    if (GlobalParams['State']=="HOMING"): # entry of homing sequense, set vals
        Trace("HOMING")
        Act_MoveTool( 5, BT) # hands up everyone
        if (GrblExist() or DRV_ESPUSB == GlobalParams['Drive']):
            GlobalParams['GrblErr']=False
            if ("timeout" == GrblSendWait("$X")):
                Trace("timeout on grbl homing")
                GrblClose()
                GrblInit()
            GrblSendWait("$H", 90) # full homing
            if ( GlobalParams['GrblErr']): # TODO_LATER: optim
                GlobalParams['GrblErr']=False
                GrblSendWait("$H")
            #go to last known pos
            if (BF < GlobalParams['TypicalBF']):
                BF = GlobalParams['TypicalBF']
            if (BF > 50000.0):
                BF = 50000.0
            if (GlobalParams['CurrentPosX'] > 1000.0):
                GlobalParams['CurrentPosX'] = 1000.0
            if (GlobalParams['CurrentPosX'] < 0.0):
                GlobalParams['CurrentPosX'] = 0.0
            if (GlobalParams['CurrentPosY'] > 1000.0):
                GlobalParams['CurrentPosY'] = 1000.0
            if (GlobalParams['CurrentPosY'] < 0.0):
                GlobalParams['CurrentPosY'] = 0.0
            # BF = GlobalParams['TypicalBF']
            CmdStr= "G01 X%f Y%f F%f"%(GlobalParams['CurrentPosX'], GlobalParams['CurrentPosY'], BF)
            Trace( "Homing - Go last known pos -%s-" % CmdStr)
            GrblSend(CmdStr) 
            Trace("HOMING attempted")
        GlobalParams['State']="HOMING_1"
    if (GlobalParams['State']=="HOMING_1"): # homing active
        if (GrblExist() or DRV_ESPUSB == GlobalParams['Drive']):
            GlobalParams['GrblErr']=False # TODO_HERE : go out of the pit
            GrblSend("G01 X0 Y0 F5000")
            GlobalParams['State']="RUN" # grbl home acknowledge is done by a 'ok'

    # timeslice
    dt = datetime.now()
    (NowUs, NowMs) = GetTimings()
    TimeSliceUs = Smooth ( 2.0, TimeSliceUs, difftimeUs( NowUs, LastUs))
    TimeSliceS = TimeSliceUs *1.0/ 1000000.0 
    LastTimeSliceMs = Smooth ( 2.0, LastTimeSliceMs, diff( NowMs, LastMs))
    (LastUs, LastMs) = (NowUs, NowMs)

    IsHoming = GlobalParams['State']=="HOMING" or GlobalParams['State']=="HOMING_1"
    # print( "State %s (IsHoming %i)" % ( GlobalParams['State'], IsHoming)) 

    ResStr=TempRecv()
    TempProcess( ResStr)

    if (DRV_ESPUSB == GlobalParams['Drive']):
        EspUsbRecv()
        GoNext = GlobalParams['GoNext']
    elif (GrblExist()):
        # no next if motor are hot, count on $25 idle delay to cooldown the stuff
        if (GlobalParams['TermalOk']):
            Resp=GrblRecv()
            if(9 == GlobalParams['GrblErr']): # locked - touched limits
                Trace("limit touched, homing required file:%s l:%i" %(FileName, FileLineCount))
                time.sleep(1); # arduino secu shut off max after 2 sec to allow homing from max
                GlobalParams['State']="HOMING"
                # next file
                if (GlobalParams['NextFileOnTrig']):
                    GcodeFileHdl.close()
                    GcodeFileHdl = False
            if (isinstance( Resp, str)):
               if ( 'ok' in Resp):
                  GlobalParams['CurrentPosX'] = AX+0.0 # TODO_LATER : this does not really represent the device position
                  GlobalParams['CurrentPosY'] = AY+0.0
                  GoNext=True
                  Trace("Go next on grbl ok")
               elif (GrblIsIdle( WaitMs=0, Strict=1)):
                  GoNext=True
        
    Act_MoveTool( BZ, BT)

    PoolingLoop()

    if ( GlobalParams['Simul']):
        GuiCprPoint( Dx, Dy, "blue")
        if (BZ < 0):
            GuiCprLine( GlobalParams['CurrentPosX'], GlobalParams['CurrentPosY'], BX, BY, "green")
        else:
            GuiCprLine( GlobalParams['CurrentPosX'], GlobalParams['CurrentPosY'], BX, BY, "purple")
        GuiCprPoint( BX, BY, "yellow")
        GuiCprPoint( GlobalParams['CurrentPosX'], GlobalParams['CurrentPosY'], "red")
    

    if (diff(NowMs, LastShowMs) > 2000):
    #if (1): # to uncomment at dev time
        Trace( "  X:%7.3f  Y:%7.3f ms:%i s:%f" % ( GlobalParams['CurrentPosX'], GlobalParams['CurrentPosY'],LastTimeSliceMs, TimeSliceS))
        LastShowMs = NowMs
    #time.sleep(0)
    if (len(Comment)):
      Trace( Comment)

  # end of the big loop
    # end of the show

    # on end send a command to trigger picture
    
    #time.sleep(0.01)

# rien a voir
# id : enora casque squids... 800


def main( ArgList) :
  if( len(ArgList) and "start" == ArgList[0]):
    print( "  TODO_HERE launch with start")
  elif( len(ArgList) and "talk" == ArgList[0]):
    SocketExchange()
  elif( len(ArgList) and "run" == ArgList[0]):
    if (GlobalParams['LogFileName']):
        GlobalParams['LogFileName']=GlobalParams['BasePath']+"Courbetlog_%s.txt" % ArgList[0]
    GlobalParams['State']="RUN"
    #Trace( "Connect to talker if availlable")
    time.sleep(1);
    MachineRun()
  elif( len(ArgList) and "tune" == ArgList[0]):
    GlobalParams['State']="TUNE"
    MachineRun()
  elif( len(ArgList) and "dev" == ArgList[0]):
    #GlobalParams['Gui'] = True
    if (GlobalParams['LogFileName']):
        GlobalParams['LogFileName']=GlobalParams['BasePath']+"Courbetlog_%s.txt" % ArgList[0]
    GlobalParams['State']="RUN" # for dev - no stoppers, no homing
    time.sleep(1);
    MachineRun()
  elif( len(ArgList) and "parts" == ArgList[0]):
    GlobalParams['State']="SEARCH"
    # MachineRun()
    SerialInit()
  else:
    print( "  launch with argument")
    print( "    'run' to have it standalone")
    print( "    'start' to have it monitored and automatically restarted on (of course never happening) crash")
    print( "    'talk' try to connect to a 'run' to show traces")
    print( "    'tune' standalone move axes to check everything rocks and rolls")
    print( "    'parts' search for connected axes")
    time.sleep(1);
    NiceQuit()

if __name__ == "__main__":
  main(sys.argv[1:])
