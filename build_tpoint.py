#!/usr/bin/env python3

import sys
import re
import json

# https://stackoverflow.com/questions/11109859/pipe-output-from-shell-command-to-a-python-script/11109920

HEADER = ('#FILENAME', 'DATE-OBS', 'LST', 'HA_TCS', 'DEC_TCS', 'ROT', 'TAR_RA', 'TAR_DEC', 'CENTER_RA', 'CENTER_DEC', 'REF_RA', 'REF_DEC', 'REF2_RA', 'REF2_DEC', 'REF3_RA', 'REF3_DEC', 'SHAPE0', 'SHAPE1', 'WCS_STR')

"""
{'rotate_angle': 89.544, 'rotate_angle_dir': 'E of N', 'wcsinfo': "WCSAXES =                    2 / Number of coordinate axes         
             CRPIX1  =        474.797485352 / Pixel coordinate of reference point            CRPIX2  =        347.047991435 / Pixel co
             ordinate of reference point            PC1_1   =    3.48555029108E-05 / Coordinate transformation matrix element       PC1_2   =     0
             .00436571323262 / Coordinate transformation matrix element       PC2_1   =    -0.00436777692776 / Coordinate transformation matrix ele
             ment       PC2_2   =    3.46458008958E-05 / Coordinate transformation matrix element       CDELT1  =                  1.0 / [deg] Coor
             dinate increment at reference point  CDELT2  =                  1.0 / [deg] Coordinate increment at reference point  CUNIT1  = 'deg'  
                           / Units of coordinate increment and value        CUNIT2  = 'deg'                / Units of coordinate increment and valu
                           e        CTYPE1  = 'RA---TAN'           / TAN (gnomonic) projection + SIP distortions    CTYPE2  = 'DEC--TAN'           / TAN (gnomoni
                           c) projection + SIP distortions    CRVAL1  =        266.328471632 / [deg] Coordinate value at reference point      CRVAL2  =        76
                           .3032158387 / [deg] Coordinate value at reference point      LONPOLE =                180.0 / [deg] Native longitude of celestial pole
                                  LATPOLE =        76.3032158387 / [deg] Native latitude of celestial pole        RADESYS = 'FK5'                / Equatorial coo
                                  rdinate system                   EQUINOX =               2000.0 / [yr] Equinox of equatorial coordinates         END", 'center_ra_dec'
                                  : [269.414779, 76.046389], 'wcs_img_ref': [269.6621945843195, 76.10485018979283], 'wcs_img_ref2': [269.8032582108338, 76.0834866249711
                                  9], 'output_dir': '/home/cstar/projects/AutoGuide/Cam2_20190818002820', 'filename': '/home/cstar/image/2019/08/Cam2/Cam2_2019081800282
                                  0.fits', 'date-obs': '2019-08-17T16:28:13.727000+00:00', 'LST': '22h05m07.8733s', 'exposure': 1.0, 'HA': 62.2271, 'DEC': 75.9426, 'TAR
                                  _RA': 269.1380939, 'TAR_DEC': 75.93915786, 'shape': [1033, 1060]}
"""

PATTERN = re.compile('^\[AutoGuide\].+? - ANALYSED: (?P<jsobj>.+)')
#src = '[AutoGuide][INFO] 2019-08-18 00:28:29 @main +275 - ANALYSED: {"rotate_angle": '
#p = PATTERN.match(src)
#print(PATTERN.match(src))
#print(p.groupdict())
#sys.exit()

# use stdin if it's full                                                        
if not sys.stdin.isatty():
    input_stream = sys.stdin

# otherwise, read the given filename                                            
else:
    try:
        input_filename = sys.argv[1]
    except IndexError:
        message = 'need filename as first argument if stdin is not full'
        raise IndexError(message)
    else:
        input_stream = open(input_filename, 'rU')

for line in input_stream:
#    print(line) # do something useful with each line
    p = PATTERN.match(line)
    if p is None:
        continue
    res = p.groupdict().get('jsobj', None)
    if res is None:
        continue
    info = json.loads(res)
    if len(info) == 0:
        continue
#    print(info)
    pack = [
        info['filename'],
        info['date-obs'],
        info['LST'],
        info['HA'],
        info['DEC'],
        info['rotate_angle'],
        info['TAR_RA'],
        info['TAR_DEC'],
        info['center_ra_dec'][0],
        info['center_ra_dec'][1],
        info['wcs_img_ref'][0],
        info['wcs_img_ref'][1],
        info['wcs_img_ref2'][0],
        info['wcs_img_ref2'][1],
        info['wcs_img_ref3'][0],
        info['wcs_img_ref3'][1],
        info['shape'][0],
        info['shape'][1],
        info['wcsinfo'],
    ]
    assert(len(pack) == len(HEADER))
    print(','.join(map(str, pack)))
