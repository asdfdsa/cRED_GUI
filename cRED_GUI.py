#! python2

from Tkinter import *
import ImgConversion
import logging
import os
from instamatic import TEMController
import datetime
import threading
import time

class DCGui(threading.Thread):
    
    ctrl=TEMController.initialize(camera="timepix")
    
    def __init__(self,master):
        threading.Thread.__init__(self)
        self.master = master
        frame=Frame(master)
        frame.pack()
        self.label_dir=Label(master,text="Please enter saving directory")
        self.label_dir.pack()
        
        v1=StringVar()
        self.ent1=Entry(master,textvar=v1)
        self.ent1.pack()
        v1.set("C:/")
        
        self.label_exp=Label(master,text="Please indicate exposure time")
        self.label_exp.pack()
        
        v2=StringVar()
        self.ent2=Entry(master,textvar=v2)
        self.ent2.pack()
        v2.set("0.5")
        
        self.b1=Button(master,text="Confirm",command=self.Name_dataset)
        self.b1.pack()
        
    def Name_dataset(self):
        self.label_dsn=Label(root,text="Please give name of your dataset")
        self.label_dsn.pack()
        
        self.ent3=Entry(root)
        self.ent3.pack()
        self.b2=Button(root,text="Confirm",command=self.mkdirs)
        self.b2.pack()
        
    def mkdirs(self):
        path1=os.path.join(self.ent1.get(),self.ent3.get())
        if not os.path.exists(path1):
            os.makedirs(path1)
        
        cl=self.ctrl.magnification.get()
        self.label_cl=Label(root,text="Camera length is now {} cm, please ensure you are in DIFFRACTION mode and change the camera length if you want NOW!".format(int(cl/10)))
        self.label_cl.pack()
        
        self.b3=Button(root,text="Confirm",command=self.CreateLog)
        self.b3.pack()
        
    def CreateLog(self):
        self.logger=logging.getLogger('DCGUI')
        hdlr=logging.FileHandler(os.path.join(self.ent1.get(),self.ent3.get(),'DCLog.log'))
        self.logger.addHandler(hdlr)
        self.logger.setLevel(logging.INFO)
        self.logger.info("Data collection started at: {}".format(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        if not os.path.exists(os.path.join(self.ent1.get(),self.ent3.get(),"tiff")):
            os.makedirs(os.path.join(self.ent1.get(),self.ent3.get(),"tiff"))
        self.pathtiff=os.path.join(self.ent1.get(),self.ent3.get(),"tiff")
        
        if not os.path.exists(os.path.join(self.ent1.get(),self.ent3.get(),"SMV")):
            os.makedirs(os.path.join(self.ent1.get(),self.ent3.get(),"SMV"))
        self.pathsmv=os.path.join(self.ent1.get(),self.ent3.get(),"SMV")
        
        if not os.path.exists(os.path.join(self.ent1.get(),self.ent3.get(),"RED")):
            os.makedirs(os.path.join(self.ent1.get(),self.ent3.get(),"RED"))
        self.pathred=os.path.join(self.ent1.get(),self.ent3.get(),"RED")
        
        self.logger.info("log file and folders created")
        
        self.b4=Button(root,text="Start Collection",command=self.startcollection)
        self.b4.pack()
        
    def startcollection(self):
        self.t=threading.Event()
        a0=self.ctrl.stageposition.a
        a=a0
        ind_set=[]
        ind=10001
        ind_set.append(ind)
        self.label_start=Label(root,text="Please start to rotate the goniometer.")
        self.label_start.pack()
        
        """while abs(a0-a)<0.5:
            a=self.ctrl.stageposition.a
            if abs(a-a0)>0.5:
                break"""
            
        self.logger.info("Data recording started at: {}".format(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        
        self.label_remind_stop=Label(root,text="Remove your foot from the pedal BEFORE HITTING STOP BUTTON")
        self.label_remind_stop.pack()
        self.b5=Button(root,text="Stop Collection",command=self.stopcollection)
        self.b5.pack()
        
        self.stop=0
        expt=self.ent2.get()
        expt=float(expt)
        
        startangle=a
        #self.ctrl.cam.block()
        while not self.t.is_set():
            print ("collecting...")
            time.sleep(0.1)
            self.master.update_idletasks()
            #self.ctrl.getImage(expt,1,out=os.path.join(self.pathtiff,"{}.tiff".format(ind)),header_keys=None)
            ind=ind+1
        
        #self.ctrl.cam.unblock()
        ind_set.append(ind)
    
    def stopcollection(self):
        self.t.set()
        
root=Tk()
GUI=DCGui(root)
root.mainloop()