import h5py
import os
import requests
from typing import Union
import numpy as np
import matplotlib.pyplot as plt
from netrc import netrc
from osgeo import gdal, gdal_array
import datetime as dt
import pandas as pd
from skimage import exposure
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning) # Disable annoying unverified HTTPS request

urs = 'urs.earthdata.nasa.gov' # Address to call for authentication

_PathLike = Union[str, bytes, os.PathLike]

def download_file(pool_url: str, out_file: _PathLike) -> bool:
    try:
        netrc_dir = os.path.expanduser("~/.netrc")
        netrc(netrc_dir).authenticators(urs)[0]
    except (FileNotFoundError, TypeError):
        print("Failed to authenticate. Please the earthdata_login.py script first to generate credentials")

    username, _, password = netrc(netrc_dir).authenticators(urs)

    with requests.get(pool_url, verify=False, stream=True, auth=(username, password)) as response:
        if response.status_code != 200:
            print("{} not downloaded. Verify that your username and password are correct in {}".format(pool_url.split('/')[-1].strip(), netrc_dir))
            return False
        
        response.raw.decode_content = True
        content = response.raw
        with open(out_file, "wb") as f:
            while chunk := content.read(16 * 1024):
                f.write(chunk)
        print(f"Downloaded file: {str(out_file)}")

# Example
# download_file("https://e4ftl01.cr.usgs.gov/VIIRS/VNP09GA.001/2018.07.02/VNP09GA.A2018183.h18v03.001.2018184074906.h5", "data/example.h5")

file = h5py.File("data/example.h5", "r")
print(list(file.keys()))