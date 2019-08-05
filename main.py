#!/usr/bin/env python3

"""
- Fetch and analyse each FITS, get its `Position` and other useful infomation.
- Diff the `Position` between FITS, calculate calibration offset
- Send offset to control software
"""

import asyncio
from pathlib import Path
from queue import Queue
import subprocess
import re
import logging
import argparse
from datetime import datetime
from typing import (
    Tuple,
)

import numpy as np
from numpy import linalg as LA

#import pyles

ASTROMETRY_WCS_RADEC_PATTERN = re.compile(r'Field center: \(RA,Dec\) = \((?P<RA>\S+?), (?P<DEC>\S+?)\) deg')
ASTROMETRY_WCS_ROTAT_PATTERN = re.compile(r'Field rotation angle: up is (?P<ROT>\S+?) degrees (?P<DIR>[ \w]{6})')

parser = argparse.ArgumentParser()
parser.add_argument("--data", help="fits file dir path", default="~/image")
parser.add_argument("--ra", help="RA FITS key name", default="RA")
parser.add_argument("--dec", help="DEC FITS key name", default="DEC")
parser.add_argument("--guide-threshold", 
    default=100, type=float,
    help="warning or start new guide if offset is larger than the shreshold, in arcsec",)

args = None # will be filled in the main

_logger = logging.getLogger(name='AutoGuide')
_logger.setLevel(logging.DEBUG)
_log_handler = logging.StreamHandler()
_log_handler.setFormatter(logging.Formatter(
    fmt='[%(name)s][%(levelname)s] %(asctime)s @%(funcName)s +%(lineno)d - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
))
_logger.addHandler(_log_handler)

#class AutoGuide(pyles.TelesApp):
#    def __init(self, name):
#        super().__init__(name, "AutoGuide")


def GetDataFITSFS(watch_dir: str) -> Queue:
    from watchdog.observers import Observer
    from watchdog.events import PatternMatchingEventHandler

    data_queue = Queue()
    class FitsFileHandler(PatternMatchingEventHandler):
        def __init__(self, *args, **kwargs):
#            log_handler = logging.StreamHandler()
#            log_handler.setFormatter(logging.Formatter(
#                fmt='[%(name)s] %(asctime)s - %(message)s',
#                datefmt='%Y-%m-%d %H:%M:%S',
#            ))
            self.logger = logging.getLogger(name='AutoGuide')
#            self.logger.setLevel(logging.INFO)
#            self.logger.addHandler(log_handler)
#            logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
            super().__init__(*args, **kwargs)
        
        def on_created(self, event):
            self.logger.info("file_received {}".format(event.src_path))
            data = {'filepath': event.src_path}
            data_queue.put(data)

    observer = Observer()
    event_handler = FitsFileHandler(patterns=["*.fits"])
    observer.schedule(event_handler, watch_dir, recursive=True)
    observer.start()

    return data_queue

def GetDataFITS():
    """Fetch FITS from data backend (fs,teles,epics,etc)
    """
    pass

def AnalysePosition(fpath: str, output_prefix = None, start_x=0, size_x=None, start_y=0, size_y=None):
    """Analyse data, get track position
    Maybe need to build catalog with astrometry.net or use image processing algorithm
    """ 
    # XXX what about long time exposure ? will be ellipse ?
    # Output: obs-time center-x center-y etc
    from astropy.io import fits
    from astropy import wcs
    fpath = Path(fpath)
    fitsfile = fits.open(fpath)
    fitshdu = fitsfile[0]
    fitshdr = fitshdu.header
    if len(fitsfile) > 1:
        # Compressed FITS data
        fitshdu = fitsfile[1]
    # CCDSEC, DATASEC. For CSTAR2 CCD: [8:1032,26:1050] (array access yx, keyword: xy)

    output_dir = output_prefix if output_prefix else "./"
    output_dir = Path(output_dir)
    output_dir = output_dir.joinpath(fpath.stem)

    # TODO export parameters
    astrometry_task_cmd = [
        "solve-field",
        "-p", # Do not plot
        "--downsample 2",
        f"{fpath}",
        "--use-sextractor",
        "--scale-high 16",
        "--scale-low 15",
        "--scale-units arcsecperpix",
        "--radius 3.5",
        "--overwrite",
    ]

    output_args = [
        "-D", str(output_dir),
        "-N", "none",
    ]
    astrometry_task_cmd += output_args

    guess_ra = fitshdr.get(args.ra)
    guess_dec = fitshdr.get(args.dec)
    if guess_ra and guess_dec:
        astrometry_task_cmd += ["--ra", f"{guess_ra}", "--dec", f"{guess_dec}",]
    else:
        _logger.error("No RA,DEC keywords, WCS would be very slow")

    cmd = " ".join(astrometry_task_cmd)
    task_result = subprocess.run([cmd,], capture_output=True, shell=True)
    _logger.debug(task_result.args)
    _logger.debug(task_result.returncode)
    _logger.debug(task_result.stderr.decode())
    _logger.debug(task_result.stdout.decode())

    wcs_center_radec_res = ASTROMETRY_WCS_RADEC_PATTERN.search(task_result.stdout.decode())
    wcs_center_radec = wcs_center_radec_res.groupdict()
    wcs_rotate_dir_res = ASTROMETRY_WCS_ROTAT_PATTERN.search(task_result.stdout.decode())
    wcs_rotate_dir = wcs_rotate_dir_res.groupdict()
    print(wcs_rotate_dir)

    ra = float(wcs_center_radec['RA'])
    dec = float(wcs_center_radec['DEC'])
    rot = float(wcs_rotate_dir['ROT'])
    direction = wcs_rotate_dir['DIR']
    wcs_file = str(output_dir.resolve().joinpath(fpath.stem)) + '.wcs'
    wcsinfo = wcs.WCS(fits.open(wcs_file)[0])
    date_obs = fitshdr.get('DATE-OBS')
    if date_obs is None:
        date_obs = datetime.now()
    else:
        date_obs = datetime.fromisoformat(date_obs)

    res = {
        'rotate_angle': rot,
        'rotate_angle_dir': direction,
        'wcsinfo': wcsinfo,
        'center_ra_dec': (ra, dec),
        'output_dir': output_dir.resolve(),
        'filename': fpath,
        'date-obs': date_obs,
        'exposure': fitshdr.get('EXPOTIME', 0)
    }

    return res

CalcOffsetRecorder = None
def CalcOffset(*, center_ra_dec: Tuple[float, float], **kwargs) -> Tuple[float, float]:
    """Calculate offset based on series of position infomation from data
    :param center_ra_dec: current center (ra, dec) in Degree
    Return offset in (ra, dec)
    """
    global CalcOffsetRecorder
    center_ra_dec = np.array(center_ra_dec)
    if CalcOffsetRecorder is None:
        # Just a new guide process
        CalcOffsetRecorder = np.array([center_ra_dec,])
        return None
    _logger.info(f"new center {center_ra_dec}, last center: {CalcOffsetRecorder[:4]}")

    offset = CalcOffsetRecorder[0] - center_ra_dec
    offset_distance = LA.norm(offset)
#    _logger.debug(f"last_two_offset_distance: {last_two_offset_distance}")
    if offset_distance > args.guide_threshold/3600:
        _logger.warning(f"Guide offset is too large {offset_distance}(deg2), maybe a new object")
        # We think telescope has changed the object, just reset guide process
        # TODO register a hook
        CalcOffsetRecorder = center_ra_dec
        return None
    CalcOffsetRecorder = np.vstack((CalcOffsetRecorder, center_ra_dec))
    if len(CalcOffsetRecorder) > 65535:
        # May never be used, to avoid memory overflow
        _logger.error("Two many offset records, cleanup memory")
        CalcOffsetRecorder = np.vstack((CalcOffsetRecorder[:32767], center_ra_dec))

    # XXX At present, the algorithm is very simple
    # just use the offset between current and first position
    #   does not match the star object
    #   does not use obs and expo time infomation, either
    # XXX We assume the image size is fixed
    return offset

def SendOffset(*, offset_ra_dec):
    """Send offset calibration to control software
    """
    if offset_ra_dec is None:
        return
    offra, offdec = offset_ra_dec
    # Send through teles
    # Send through epics
    import epics
    _logger.debug(f'Will SendOffset {offra}, {offdec} via EPICS')
    # TODO handle timeout
    pv_offra = epics.PV('TELCSTAR2:Mount:Guide:OFFRA')
    pv_offdec = epics.PV('TELCSTAR2:Mount:Guide:OFFDEC')
    pv_offset = epics.PV('TELCSTAR2:Mount:Guide:OFFSET')
    pv_offra.put(offra)
    pv_offdec.put(offdec)
    pv_offset.put(1)
    _logger.info(f'SendOffset via EPICS done')


def main():
    data_queue = GetDataFITSFS(args.data)
    while True:
        try:
            data = data_queue.get()
            filepath = data['filepath']
            print(filepath)
            proc_ret = AnalysePosition(filepath)
            _logger.info(proc_ret)
            offset = CalcOffset(**proc_ret)
            _logger.info(f"offset: {offset}")
            SendOffset(offset_ra_dec=offset)
        except Exception as e:
            import traceback
            _logger.error(e)
            _logger.error(traceback.format_exc())

if __name__ == '__main__':
    args = parser.parse_args()
    try:
        loop = asyncio.get_event_loop()
        main()
        loop.run_forever()
    except KeyboardInterrupt:
        loop.close()
