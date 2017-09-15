from Tkinter import *
from PIL import Image, ImageEnhance
from PIL import ImageTk
import threading
import numpy as np
import time
import datetime
from instamatic.formats import write_tiff
from instamatic.camera import Camera
import os
import fabio
import glob
import ImgConversion

class ImageGrabber(object):
    """docstring for ImageGrabber"""
    def __init__(self, cam, callback, frametime=0.05):
        super(ImageGrabber, self).__init__()
        
        self.callback = callback
        self.cam = cam

        self.default_exposure = self.cam.default_exposure
        self.default_binsize = self.cam.default_binsize
        self.dimensions = self.cam.dimensions
        self.defaults = self.cam.defaults
        self.name = self.cam.name

        self.frame = None
        self.thread = None
        self.stopEvent = None

        self.stash = None

        self.frametime = frametime
        self.exposure = self.frametime
        self.binsize = self.cam.default_binsize

        self.lock = threading.Lock()

        self.stopEvent = threading.Event()
        self.acquireInitiateEvent = threading.Event()
        self.acquireCompleteEvent = threading.Event()
        self.continuousCollectionEvent = threading.Event()

    def run(self):
        while not self.stopEvent.is_set():

            if self.acquireInitiateEvent.is_set():
                self.acquireInitiateEvent.clear()
                
                frame = self.cam.getImage(t=self.exposure, fastmode=True)
                self.callback(frame, acquire=True)

            elif not self.continuousCollectionEvent.is_set():
                frame = self.cam.getImage(t=self.frametime, fastmode=True)
                self.callback(frame)

    def start_loop(self):
        self.thread = threading.Thread(target=self.run, args=())
        self.thread.start()

    def end_loop(self):
        self.thread.stop()


class VideoStream(threading.Thread):
    """docstring for VideoStream"""
    def __init__(self, cam="timepix"):
        threading.Thread.__init__(self)
        try:
            self.cam = Camera(kind=cam)
            self.camtyp=1
        except RuntimeError:
            self.cam = Camera(kind="simulate")
            self.camtyp=0

        self.panel = None

        self.default_exposure = self.cam.default_exposure
        self.default_binsize = self.cam.default_binsize
        self.dimensions = self.cam.dimensions
        self.defaults = self.cam.defaults
        self.name = self.cam.name

        self.frame_delay = 50

        self.frametime = 0.05
        self.brightness = 11800

        self.last = time.time()
        self.nframes = 1
        self.update_frequency = 0.25
        self.last_interval = self.frametime

        self.stream = self.setup_stream()
        self.start()

    def run(self):
        self.root = Tk()

        self.init_vars()
        self.buttonbox(self.root)
        self.header(self.root)
        self.makepanel(self.root)

        # self.stopEvent = threading.Event()
 
        self.root.wm_title("Instamatic stream")
        self.root.wm_protocol("WM_DELETE_WINDOW", self.close)

        self.root.bind('<Escape>', self.close)

        self.root.bind('<<StreamAcquire>>', self.on_frame)
        self.root.bind('<<StreamEnd>>', self.close)
        self.root.bind('<<StreamFrame>>', self.on_frame)

        self.start_stream()
        self.root.mainloop()

    def header(self, master):
        ewidth = 10
        lwidth = 12

        frame = Frame(master)
        self.e_fps         = Entry(frame, bd=0, width=ewidth, textvariable=self.var_fps, state=DISABLED)
        self.e_interval = Entry(frame, bd=0, width=ewidth, textvariable=self.var_interval, state=DISABLED)
        
        self.saving_path = Entry(frame, width = 50, textvariable=self.var_saving_path)
        self.name_data=Entry(frame, width = 50, textvariable=self.var_name_dataset)
        self.Expt=Entry(frame,width=50,textvariable=self.var_dataRecordExpt)
        
        self.ConfirmButton1= Button(frame,text="Confirm",command=self.mkdirs)
        self.ConfirmButton1.grid(row=3,column=3)
        
        #var=cRED_Collection()
        self.CollectionButton=Button(frame,text="Start Collection",command=self.collection)
        self.CollectionButton.grid(row=3,column=4)
        self.CollectionStopButton=Button(frame,text="Stop Collection",command=self.collectionstop)
        self.CollectionStopButton.grid(row=3,column=5)
        self.CollectionContButton=Button(frame,text="Continue Collection",command=self.continuecollection)
        self.CollectionContButton.grid(row=3,column=6)
        self.exitButton=Button(frame,text="EXIT",command=self.close_window)
        self.exitButton.grid(row=3,column=7)
        # self.e_overhead    = Entry(frame, bd=0, width=ewidth, textvariable=self.var_overhead, state=DISABLED)
        
        Label(frame, anchor=E, width=lwidth, text="fps:").grid(row=1, column=0)
        self.e_fps.grid(row=1, column=1)
        Label(frame, anchor=E, width=lwidth, text="interval (ms):").grid(row=1, column=2)
        self.e_interval.grid(row=1, column=3)
        Label(frame, anchor=E, width=30, text="Saving path:").grid(row=2, column=0)
        self.saving_path.grid(row=2,column=2)
        Label(frame, anchor=E, width=30, text="Name of current dataset:").grid(row=3,column=0)
        self.name_data.grid(row=3,column=2)
        Label(frame, anchor=E, width=30,text="Exposure time for data collection").grid(row=4,column=0)
        self.Expt.grid(row=4,column=2)
        # Label(frame, anchor=E, width=lwidth, text="overhead (ms):").grid(row=1, column=4)
        # self.e_overhead.grid(row=1, column=5)
        
        """        self.progress=ttk.Progressbar(frame,orient=HORIZONTAL,length=100,mode='determinate')
        self.progress.pack(expand=True,fill=BOTH,side=TOP)
        self.progress.start(50)"""
        
        frame.pack()

        frame = Frame(master)
        
        self.e_frametime = Spinbox(frame, width=ewidth, textvariable=self.var_frametime, from_=0.0, to=1.0, increment=0.01)
        
        Label(frame, anchor=E, width=lwidth, text="exposure (s)").grid(row=1, column=0)
        self.e_frametime.grid(row=1, column=1)

        self.e_brightness = Spinbox(frame, width=ewidth, textvariable=self.var_brightness, from_=0.0, to=11800, increment=10)
        
        Label(frame, anchor=E, width=lwidth, text="Max Intensity").grid(row=1, column=2)
        self.e_brightness.grid(row=1, column=3)
        
        frame.pack()

    def makepanel(self, master, resolution=(512,512)):
        if self.panel is None:
            image = Image.fromarray(np.zeros(resolution))
            image = ImageTk.PhotoImage(image)

            self.panel = Label(image=image)
            self.panel.image = image
            self.panel.pack(side="left", padx=10, pady=10)

    def buttonbox(self, master):
        btn = Button(master, text="Save image",
            command=self.saveImage)
        btn.pack(side="bottom", fill="both", expand="yes", padx=10, pady=10)

    def init_vars(self):
        self.var_fps = DoubleVar()
        self.var_interval = DoubleVar()
        self.var_saving_path = StringVar(value="C:/")
        self.var_name_dataset=StringVar(value="Co-CAU-30_1")
        self.var_dataRecordExpt=StringVar(value="0.5")
        # self.var_overhead = DoubleVar()

        self.var_frametime = DoubleVar()
        self.var_frametime.set(self.frametime)
        self.var_frametime.trace("w", self.update_frametime)

        self.var_brightness = DoubleVar(value=11800)
        self.var_brightness.set(self.brightness)
        self.var_brightness.trace("w", self.update_brightness)

    def update_frametime(self, name, index, mode):
        # print name, index, mode
        try:
            self.frametime = self.var_frametime.get()
        except:
            pass
        else:
            self.stream.frametime = self.frametime

    def update_brightness(self, name, index, mode):
        # print name, index, mode
        try:
            self.brightness = self.var_brightness.get()
        except:
            pass

    def saveImage(self):
        outfile = datetime.datetime.now().strftime("%Y%m%d-%H%M%S.%f") + ".tiff"
        write_tiff(outfile, self.frame)
        print (" >> Wrote file:", outfile)

    def close(self):
        self.stream.stopEvent.set()
        self.root.quit()

    def send_frame(self, frame, acquire=False):
        if acquire:
            self.stream.lock.acquire(True)
            self.acquired_frame = self.frame = frame
            self.stream.lock.release()
            self.stream.acquireCompleteEvent.set()
        else:
            self.stream.lock.acquire(True)
            self.frame = frame
            self.stream.lock.release()

        # these events feel fragile if fired in rapid succession
        # self.root.event_generate('<<StreamFrame>>', when='tail')

    def setup_stream(self):
        return ImageGrabber(self.cam, callback=self.send_frame, frametime=self.frametime)
    
    def start_stream(self):
        self.stream.start_loop()
        self.root.after(500, self.on_frame)

    def on_frame(self, event=None):
        self.stream.lock.acquire(True)
        frame = self.frame
        self.stream.lock.release()

        frame = np.rot90(frame, k=3)

        if self.brightness != 11800:
            #image = Image.fromarray(frame).convert("L")
            #image = ImageEnhance.Brightness(image).enhance(self.brightness)
            # Can also use ImageEnhance.Sharpness or ImageEnhance.Contrast if needed
            image=np.clip(frame,0,self.brightness)
            image=image/self.brightness*11800
            image=Image.fromarray(image)

        else:
            image = Image.fromarray(frame)

        image = ImageTk.PhotoImage(image=image)

        self.panel.configure(image=image)
        # keep a reference to avoid premature garbage collection
        self.panel.image = image

        self.update_frametimes()
        # self.root.update_idletasks()

        self.root.after(self.frame_delay, self.on_frame)

    def update_frametimes(self):
        self.current = time.time()
        delta = self.current - self.last

        if delta > self.update_frequency:
            interval = delta/self.nframes

            interval = (interval * 0.5) + (self.last_interval * 0.5)

            fps = 1.0/interval
            # overhead = interval - self.stream.frametime

            self.var_fps.set(round(fps, 2))
            self.var_interval.set(round(interval*1000, 2))
            # self.var_overhead.set(round(overhead*1000, 2))
            self.last = self.current
            self.nframes = 1

            self.last_interval = interval
        else:
            self.nframes += 1

    def getImage(self, t=None, binsize=1):
        current_frametime = self.stream.frametime

        # set to 0 to prevent it lagging data acquisition
        self.stream.frametime = 0
        if t:
            self.stream.exposure = t
        if binsize:
            self.stream.binsize = binsize

        self.stream.acquireInitiateEvent.set()

        self.stream.acquireCompleteEvent.wait()

        self.stream.lock.acquire(True)
        frame = self.acquired_frame
        self.stream.lock.release()
        
        self.stream.acquireCompleteEvent.clear()
        self.stream.frametime = current_frametime
        return frame

    def block(self):
        self.stream.continuousCollectionEvent.set()

    def unblock(self):
        self.stream.continuousCollectionEvent.clear()

    def continuous_collection(self, exposure=0.1, n=100, callback=None):
        """
        Function to continuously collect data
        Blocks the videostream while collecting data, and only shows collected images
        exposure: float
            exposure time
        n: int
            number of frames to collect
            if defined, returns a list of collected frames
        callback: function
            This function is called on every iteration with the image as first argument
            Should return True or False if data collection is to continue
        """
        buffer = []

        go_on = True
        i = 0

        self.block()
        while go_on:
            i += 1

            img = self.getImage(t=exposure)

            if callback:
                go_on = callback(img)
            else:
                buffer.append(img)
                go_on = i < n

        self.unblock()

        if not callback:
            return buffer

    def mkdirs(self):
        
        mother_path=self.var_saving_path.get()
        dataset_name=self.var_name_dataset.get()
        
        self.saving=os.path.join(mother_path,dataset_name)
        
        if not os.path.exists(os.path.join(mother_path,dataset_name)):
            os.mkdir(os.path.join(mother_path,dataset_name))
            
        if not os.path.exists(os.path.join(mother_path,dataset_name,"tiff")):
            os.mkdir(os.path.join(mother_path,dataset_name,"tiff"))
            
        if not os.path.exists(os.path.join(mother_path,dataset_name,"SMV")):
            os.mkdir(os.path.join(mother_path,dataset_name,"SMV"))
            
        if not os.path.exists(os.path.join(mother_path,dataset_name,"RED")):
            os.mkdir(os.path.join(mother_path,dataset_name,"RED"))
        
        import logging
        self.logger=logging.getLogger('DCGUI')
        hdlr=logging.FileHandler(os.path.join(self.saving,'DataCollectionLog.log'))
        formatter=logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        hdlr.setFormatter(formatter)
        self.logger.addHandler(hdlr)
        self.logger.setLevel(logging.INFO)
        self.logger.info("log file and folders created")
        self.logger.info("Data collection started at: {}".format(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        
    
    def collection(self):
        self.t=threading.Event()
        
        #cwd=os.getcwd()
        flatfield=fabio.open(os.path.join(r'C:\Users\bwang\workspace\cRED_Collection_Structured','flatfield_tpx_2017-06-21.tiff'))
        data=flatfield.data
        newdata=np.zeros([512,512],dtype=np.ushort)
        newdata[0:256,0:256]=data[0:256,0:256]
        newdata[256:,0:256]=data[260:,0:256]
        newdata[0:256,256:]=data[0:256,260:]
        newdata[256:,256:]=data[260:,260:]
        flatfield=newdata
        
        pxd={'15': 0.00838, '20': 0.00623, '25': 0.00499, '30': 0.00412, '40': 0.00296, '50': 0.00238, '60': 0.00198, '80': 0.00148}
        
        a0=ctrl.stageposition.a
        a=a0
        ind_set=[]
        ind=10001
        ind_set.append(ind)
        expt=float(self.Expt.get())
        
        self.pathtiff=os.path.join(self.saving,"tiff")
        self.pathsmv=os.path.join(self.saving,"SMV")
        self.pathred=os.path.join(self.saving,"RED")

        self.logger.info("Data recording started at: {}".format(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        self.logger.info("Data saving path: {}".format(self.saving))
        self.logger.info("Data collection exposure time: {} s".format(self.Expt.get()))
        self.cl=int(ctrl.magnification.get())/10
        self.logger.info("Data collection camera length: {} cm".format(self.cl))
        self.logger.info("Data collection spot size: {}".format(ctrl.spotsize))
        
        w=Tk()
        w.after(5000,lambda:w.destroy())
        Label(w,text="Now you can start to rotate the goniometer at any time.").pack()
        Label(w,text="Remove your foot from the pedal BEFORE click STOP COLLECTION!").pack()
        Label(w,text="Window autocloses in 3 sec.").pack()
        
        if self.camtyp == 1:
            while abs(a-a0)<0.5:
                a=ctrl.stageposition.a
                if abs(a-a0)>0.5:
                    break
            
            self.startangle=a
            
            ctrl.cam.block()
            
            while not self.t.is_set():
                ctrl.getimage(expt,1,out=os.path.join(self.pathtiff,"{}.tiff".format(ind)),header_keys=None)
                ind=ind+1
                self.root.update()
                
            ctrl.cam.unblock()
            self.endangle=ctrl.stageposition.a
            ind_set.append(ind)
            
        else:
            self.startangle=a
            self.cl=30
            flatfield=np.random.rand(1024,1024)
            while not self.t.is_set():
                write_tiff(os.path.join(self.pathtiff,"{}.tiff".format(ind)), np.random.rand(1024,1024))
                print ("Simulated image saved...")
                time.sleep(expt)
                ind=ind+1
                self.root.update()
            self.endangle=self.startangle+10
            ind_set.append(ind)
        
        self.ind=ind
        
        self.logger.info("Data collected from {} degree to {} degree.".format(self.startangle,self.endangle))
        
        listing=glob.glob(self.pathtiff)
        numfr=len(listing)
        osangle=(self.endangle-self.startangle)/numfr
        if osangle>0:
            self.logger.info("Oscillation angle: {}".format(osangle))
        else:
            self.logger.info("Oscillation angle: {}".format(-osangle))
        
        self.logger.info("Pixel size and actual camera length updated in SMV file headers for DIALS processing.")
        self.logger.info("XDS INP file created as usual.")
        buf=ImgConversion.ImgConversion(flatfield,pxd)
        pb=buf.TiffToIMG(self.pathtiff,self.pathsmv,str(self.cl),self.startangle,osangle,self.logger)
        pxs=pxd[str(self.cl)]
        buf.ED3DCreator(self.pathtiff,self.pathred,pxs,self.startangle,self.endangle,self.logger)
        buf.MRCCreator(self.pathtiff,self.pathred,header=ImgConversion.ImgConversion.mrc_header,pb=pb,logger=self.logger)
        
        RA=-38.5
        buf.XDSINPCreator(self.pathsmv,self.ind,self.startangle,20,0.8,pb,str(self.cl),osangle,RA,self.logger)
        
        w=Tk()
        Label(w,text="Data conversion done.").pack()
        Label(w,text="Click Continue Collection to continue data collection. Otherwise click EXIT.").pack()
        
    def collectionstop(self):
        self.t.set()
        print ('Collection stopped.')
        
    def continuecollection(self):
        self.t.clear()
        
    def close_window(self):
        import sys
        sys.exit()
        

if __name__ == '__main__':
    from instamatic import TEMController
    ctrl=TEMController.initialize(camera="timepix")
    stream = VideoStream()
    from IPython import embed
    embed()
    stream.close()