# Earthdata example

This repository contains some basic code examples of how to download and read the HDF5 file format (`.h5` files) from NASA Earthdata

## Troubleshooting:

### How to download and install the GDAL library

**These steps are not required if you use conda as the libraries are shipped with the package**

Here is what I have done on Ubuntu:

```bash
sudo add-apt-repository ppa:ubuntugis/ppa
sudo apt-get update
sudo apt-get install gdal-bin
sudo apt-get install libgdal-dev
export CPLUS_INCLUDE_PATH=/usr/include/gdal
export C_INCLUDE_PATH=/usr/include/gdal
```

You can then install the version of the python bindings that match your native GDAL library:

```bash
pip install GDAL=="$(gdal-config --version)"
```