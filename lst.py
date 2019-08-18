import os
#import glob2
import ephem
#import subprocess
import numpy as np
import astropy.units as u
from astropy.io import fits
from astropy.time import Time
from astropy.wcs import WCS
#from PythonPhot import mmm
from astropy.coordinates import Angle
from astropy.coordinates import SkyCoord

# For XuYi
class GetLST:
    @staticmethod
    def GL(date: str, lon='118.465', lat='32.736', elev=200):
        
        Osservatorio = ephem.Observer()
        Osservatorio.lon,Osservatorio.lat = lon, lat  
        Osservatorio.elevation = elev
        
#        # Assume date has format='isot'
#        Osservatorio.date = Time(date, format='iso').iso  
        Osservatorio.date = date
        sid = Osservatorio.sidereal_time()
        a = Angle(sid, u.radian)
        sid_str = a.to_string(unit=u.hour)   
        
        return sid_str

