#!/usr/bin/env python3

import asyncio
from pathlib import Path

"""
- Fetch and analyse each FITS, get its `Position` and other useful infomation.
- Diff the `Position` between FITS, calculate calibration offset
- Send offset to control software
"""

def GetDataFITSFS(watch_dir: str):
    import logging
    from watchdog.observers import Observer
    from watchdog.events import PatternMatchingEventHandler

    class FitsFileHandler(PatternMatchingEventHandler):
        def __init__(self, *args, **kwargs):
            log_handler = logging.StreamHandler()
            log_handler.setFormatter(logging.Formatter(
                fmt='[%(name)s] %(asctime)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S',
            ))
            self.logger = logging.getLogger(name='FitsFileMonitor')
            self.logger.setLevel(logging.INFO)
            self.logger.addHandler(log_handler)
#            logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
            super().__init__(*args, **kwargs)
        
        def on_created(self, event):
            self.logger.info("created {}".format(event.src_path))

    observer = Observer()
    event_handler = FitsFileHandler(patterns=["*.fits"])
    observer.schedule(event_handler, watch_dir, recursive=True)
    observer.start()

def GetDataFITS():
    """Fetch FITS from data backend (fs,teles,epics,etc)
    """
    pass

def AnalysePosition():
    """Analyse data, get track position
    Maybe need to build catalog with astrometry.net or use image processing algorithm
    """ 
    pass

def CalcOffset():
    """Calculate offset based on series of position infomation from data
    """
    pass

def SendOffset():
    """Send offset calibration to control software
    """
    pass


def main():
    GetDataFITSFS("./tests")
    loop = asyncio.get_event_loop()
    try:
        loop.run_forever()
    except KeyboardInterrupt:
        loop.close()

if __name__ == '__main__':
    main()
