import h5py
import os
import numpy as np
import matplotlib.pyplot as plt

from pathlib import Path
from typing import Union
from skimage import exposure

_PathLike = Union[str, bytes, os.PathLike]

def generate_rgb_image(file: h5py.File, file_path: _PathLike) -> None:
    """
    Generate an RGB image from an H5 file using the 
    SurfReflect_M3-M5 Bands
    """
    data_fields = file['HDFEOS']['GRIDS']['VNP_Grid_1km_2D']['Data Fields']
    r = data_fields['SurfReflect_M5_1'] # M5 = Red
    g = data_fields['SurfReflect_M4_1'] # M4 = Green
    b = data_fields['SurfReflect_M3_1'] # M3 = Blue
    n = data_fields['SurfReflect_M7_1'] # M7  = NIR (Near Infra Red)

    # These are common to r, g, b and n
    scale_factor = r.attrs['Scale'][0]
    fill_value = r.attrs['_FillValue'][0]

    red = r[()] * scale_factor
    green = g[()] * scale_factor
    blue = b[()] * scale_factor
    nir = n[()] * scale_factor

    rgb = np.dstack((red, green, blue)) # Create rgb array
    rgb[rgb == fill_value * scale_factor] = 0 # Set fill value as 0 instead of random value

    # This section is only done to create the image, we should not do this
    # except for just visualizing the photo
    p2, p98 = np.percentile(rgb, (2, 98)) # 2nd and 98th percentile for updating min/max vals
    rgb_stretched = exposure.rescale_intensity(rgb, in_range=(p2, p98)) # Contrast stretch
    rgb_stretched = exposure.adjust_gamma(rgb_stretched, 0.5) # Gamma correction

    # Draw the image
    fig = plt.figure(figsize =(10,10)) # Set the figure size
    ax = plt.Axes(fig,[0,0,1,1]) 
    ax.set_axis_off() # Turn off axes
    fig.add_axes(ax)
    ax.imshow(rgb_stretched, interpolation='bilinear', alpha=0.9) # Plot a natural color RGB
    fig.savefig(Path(file_path) / "image.jpeg") # Export natural color RGB as jpeg


def quality_filtering(file: h5py.File, file_path: _PathLike):
    """
    This function aims to show how to decode bit values from the QF flags
    determine which values to mask and how to apply the masks to the data arrays
    """
    # Same thing as generating the images
    data_fields = file['HDFEOS']['GRIDS']['VNP_Grid_1km_2D']['Data Fields']
    r = data_fields['SurfReflect_M5_1'] # M5 = Red
    g = data_fields['SurfReflect_M4_1'] # M4 = Green
    b = data_fields['SurfReflect_M3_1'] # M3 = Blue
    n = data_fields['SurfReflect_M7_1'] # M7  = NIR (Near Infra Red)

    # These are common to r, g, b and n
    scale_factor = r.attrs['Scale'][0]
    fill_value = r.attrs['_FillValue'][0]

    red = r[()] * scale_factor
    green = g[()] * scale_factor
    blue = b[()] * scale_factor
    nir = n[()] * scale_factor

    # Here we use the QF5 since it contains data about M1-7
    # See all bit values: https://landweb.modaps.eosdis.nasa.gov/NPP/forPage/NPPguide/VIIRS_Surf_Refl_UserGuide_v1.7.pdf
    qf5 = data_fields['SurfReflect_QF5_1'][()] # Import QF5 SDS

    bits = 8 # Number of bits
    vals = list(range(0, 2 ** bits)) # Generate list of all possible bit values
    
    good_qf = [] # All flags which represent good quality of surface reflectance data

    for v in vals:
        bitVal = format(vals[v], 'b').zfill(bits)
        if bitVal[0:4] == '0000': # Keep good data for M7, M5, M4, M3 (bits 4-7)
            good_qf.append(vals[v])

    # Apply mask to each SR SDS based on the qf layer and the list of good quality values generated above
    red = np.ma.MaskedArray(red, np.in1d(qf5, good_qf, invert = True))    
    green = np.ma.MaskedArray(green, np.in1d(qf5, good_qf, invert = True))    
    blue = np.ma.MaskedArray(blue, np.in1d(qf5, good_qf, invert = True))    
    nir = np.ma.MaskedArray(nir, np.in1d(qf5, good_qf, invert = True))

    # Use QF2 to apply quality and land/water masks
    # See spec in pdf above for other possible flags
    qf2 = data_fields['SurfReflect_QF2_1'][()] # Import QF2 SDS
    land = [] # Store bit values classified as land

    for v in vals:
        bitVal = format(vals[v],'b').zfill(bits) # Convert to binary based on values and # of bits defined above:
        if bitVal[-3:] != '010' and bitVal[-3:] != '011' : # Keep all values NOT equal to inland or sea water
            land.append(vals[v]) # Append to list
    
    # Apply mask to each SR SDS based on the qf2 layer and the list of land values generated above
    red = np.ma.MaskedArray(red, np.in1d(qf2, land, invert = True))    
    green = np.ma.MaskedArray(green, np.in1d(qf2, land, invert = True))    
    blue = np.ma.MaskedArray(blue, np.in1d(qf2, land, invert = True))    
    nir = np.ma.MaskedArray(nir, np.in1d(qf2, land, invert = True))

    # Tutorial specific functions
    # Define a function to calculate NDVI (Normalized Difference Vegetation Index)
    def ndviCalc(red, nir):
        return ((nir - red)/(nir + red))

    # Define a function to calculate EVI (Enhanced Vegetation Index)
    def eviCalc(red, nir, blue):
        return (2.5 * (nir - red)/(nir + 6 * red - 7.5 * blue + 1))

    ndvi = ndviCalc(red, nir)                                   # Calculate NDVI from red/NIR bands
    evi = eviCalc(red, nir, blue)                               # Calculate EVI from red, NIR, and blue bands
    ndvi[np.where(np.logical_or(ndvi < 0, ndvi > 1)) ] = np.nan # Exclude VIs outside of range
    evi[np.where(np.logical_or(evi < 0, evi > 1)) ] = np.nan    # Exclude VIs outside of range

    fig = plt.figure(figsize=(10,10)) # Set the figure size (x,y)
    fig.set_facecolor("black")        # Set the background color to black
    plt.axis('off')                   # Remove axes from plot
    plt.imshow(ndvi, cmap = 'YlGn')   # Plot the array using a color map

    fig = plt.figure(figsize=(10,10)) # Set the figure size (x,y)
    fig.set_facecolor("black")        # Set the background color to black
    plt.axis('off')                   # Remove axes from plot
    plt.imshow(evi, cmap = 'YlGn');   # Plot the array using a color map

    # Combine both plots into a single figure
    t = 'VIIRS Vegetation Indices'                                                           # Set title to a variable
    figure, axes = plt.subplots(nrows=1, ncols=2, figsize=(20, 8), sharey=True, sharex=True) # Set subplots with 1 row & 2 columns
    axes[0].axis('off'), axes[1].axis('off')                                                 # Turn off axes' values
    figure.set_facecolor("black")                                                            # Set the background color to black
    figure.suptitle('{}'.format(t), fontsize=24, fontweight='bold', color="white") # Add a title for the plots
    axes[0].set_title('NDVI', fontsize=18, fontweight='bold', color="white")                 # Set the first subplot title
    axes[1].set_title('EVI', fontsize=18, fontweight='bold', color="white")                  # Set the second subplot title
    axes[0].imshow(ndvi, vmin=0.1, vmax=0.9, cmap='YlGn');                                   # Plot original data
    axes[1].imshow(evi, vmin=0.1, vmax=0.9, cmap='YlGn');                                    # Plot Quality-filtered data
    figure.savefig(Path(file_path) / "image_VIIRS_VIs.jpeg", facecolor = "black")            # Set up filename, export to png 


def calculate_surface_reflection(file: h5py.File) -> None:
    """
    Calculate the surface reflection using the I3 Band
    Similar to how we want to do it to get the albedo
    """
    data_fields = file['HDFEOS']['GRIDS']['VNP_Grid_500m_2D']['Data Fields']

    i3 = data_fields['SurfReflect_I3_1']

    # These are common to r, g, b and n
    scale_factor = i3.attrs['Scale'][0]
    fill_value = i3.attrs['_FillValue'][0]
    
    # Apply scale factor
    reflec = i3[()] * scale_factor

    # Set fill values to zero since we don't want random garbage in the data
    reflec[reflec == fill_value * scale_factor] = 0

    print("Without any masks: \n")
    print(reflec)

    """
    Authors note: 
    
    We could probably filter for clouds and things using the 1km QF.
    As it turns out, using the 1km data we get a (1200, 1200) numpy array for QF and all the bands
    Where as using the 500m one we get (2400, 2400) numpy array, which means the filter could
    be used by interpolating values between...

    I personnally couldn't get this to work, my code is below:
    """

    qf6 = file['HDFEOS']['GRIDS']['VNP_Grid_1km_2D']['Data Fields']['SurfReflect_QF6_1'][()]
    qf6 = np.kron(qf6, np.ones((2,2), dtype=qf6.dtype))

    bits = 8 # Number of bits
    vals = list(range(0, 2 ** bits)) # Generate list of all possible bit values
    
    good_qf = [] # All flags which represent good quality of surface reflectance data

    for v in vals:
        bitVal = format(vals[v], 'b').zfill(bits)
        if bitVal[2] == '0': # Keep good data for I3 band
            good_qf.append(vals[v])

    # TODO: Becomes garbage data?
    reflec = np.ma.MaskedArray(reflec, np.in1d(qf6, good_qf, invert = True))

if __name__ == "__main__":
    file = h5py.File("data/VNP09GA.A2022229.h06v11.001.2022243174836.h5", "r")

    # generate_rgb_image(file, "data/")
    # quality_filtering(file, "data/")  
    calculate_surface_reflection(file)


"""
Example keys present in a h5 file:

 'HDFEOS',
 'HDFEOS/ADDITIONAL',
 'HDFEOS/ADDITIONAL/FILE_ATTRIBUTES',
 'HDFEOS/GRIDS',
 'HDFEOS/GRIDS/VNP_Grid_1km_2D',
 'HDFEOS/GRIDS/VNP_Grid_1km_2D/Data Fields',
 'HDFEOS/GRIDS/VNP_Grid_1km_2D/Data Fields/SensorAzimuth_1',
 'HDFEOS/GRIDS/VNP_Grid_1km_2D/Data Fields/SensorZenith_1',
 'HDFEOS/GRIDS/VNP_Grid_1km_2D/Data Fields/SolarAzimuth_1',
 'HDFEOS/GRIDS/VNP_Grid_1km_2D/Data Fields/SolarZenith_1',
 'HDFEOS/GRIDS/VNP_Grid_1km_2D/Data Fields/SurfReflect_M10_1',
 'HDFEOS/GRIDS/VNP_Grid_1km_2D/Data Fields/SurfReflect_M11_1',
 'HDFEOS/GRIDS/VNP_Grid_1km_2D/Data Fields/SurfReflect_M1_1',
 'HDFEOS/GRIDS/VNP_Grid_1km_2D/Data Fields/SurfReflect_M2_1',
 'HDFEOS/GRIDS/VNP_Grid_1km_2D/Data Fields/SurfReflect_M3_1',
 'HDFEOS/GRIDS/VNP_Grid_1km_2D/Data Fields/SurfReflect_M4_1',
 'HDFEOS/GRIDS/VNP_Grid_1km_2D/Data Fields/SurfReflect_M5_1',
 'HDFEOS/GRIDS/VNP_Grid_1km_2D/Data Fields/SurfReflect_M7_1',
 'HDFEOS/GRIDS/VNP_Grid_1km_2D/Data Fields/SurfReflect_M8_1',
 'HDFEOS/GRIDS/VNP_Grid_1km_2D/Data Fields/SurfReflect_QF1_1',
 'HDFEOS/GRIDS/VNP_Grid_1km_2D/Data Fields/SurfReflect_QF2_1',
 'HDFEOS/GRIDS/VNP_Grid_1km_2D/Data Fields/SurfReflect_QF3_1',
 'HDFEOS/GRIDS/VNP_Grid_1km_2D/Data Fields/SurfReflect_QF4_1',
 'HDFEOS/GRIDS/VNP_Grid_1km_2D/Data Fields/SurfReflect_QF5_1',
 'HDFEOS/GRIDS/VNP_Grid_1km_2D/Data Fields/SurfReflect_QF6_1',
 'HDFEOS/GRIDS/VNP_Grid_1km_2D/Data Fields/SurfReflect_QF7_1',
 'HDFEOS/GRIDS/VNP_Grid_1km_2D/Data Fields/num_observations_1km',
 'HDFEOS/GRIDS/VNP_Grid_1km_2D/Data Fields/obscov_1km_1',
 'HDFEOS/GRIDS/VNP_Grid_1km_2D/Data Fields/orbit_pnt_1',
 'HDFEOS/GRIDS/VNP_Grid_500m_2D',
 'HDFEOS/GRIDS/VNP_Grid_500m_2D/Data Fields',
 'HDFEOS/GRIDS/VNP_Grid_500m_2D/Data Fields/SurfReflect_I1_1',
 'HDFEOS/GRIDS/VNP_Grid_500m_2D/Data Fields/SurfReflect_I2_1',
 'HDFEOS/GRIDS/VNP_Grid_500m_2D/Data Fields/SurfReflect_I3_1',
 'HDFEOS/GRIDS/VNP_Grid_500m_2D/Data Fields/iobs_res_1',
 'HDFEOS/GRIDS/VNP_Grid_500m_2D/Data Fields/num_observations_500m',
 'HDFEOS/GRIDS/VNP_Grid_500m_2D/Data Fields/obscov_500m_1',
 'HDFEOS INFORMATION',
 'HDFEOS INFORMATION/StructMetadata.0',
 'SensorAzimuth_c',
 'SensorZenith_c',
 'SolarAzimuth_c',
 'SolarZenith_c',
 'SurfReflect_I1_c',
 'SurfReflect_I2_c',
 'SurfReflect_I3_c',
 'SurfReflect_M10_c',
 'SurfReflect_M11_c',
 'SurfReflect_M1_c',
 'SurfReflect_M2_c',
 'SurfReflect_M3_c',
 'SurfReflect_M4_c',
 'SurfReflect_M5_c',
 'SurfReflect_M7_c',
 'SurfReflect_M8_c',
 'SurfReflect_QF1_c',
 'SurfReflect_QF2_c',
 'SurfReflect_QF3_c',
 'SurfReflect_QF4_c',
 'SurfReflect_QF5_c',
 'SurfReflect_QF6_c',
 'SurfReflect_QF7_c',
 'iobs_res_c',
 'nadd_obs_row_1km',
 'nadd_obs_row_500m',
 'obscov_1km_c',
 'obscov_500m_c',
 'orbit_pnt_c'
"""