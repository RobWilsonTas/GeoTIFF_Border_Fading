import time
from pathlib import Path
from datetime import datetime
startTime = time.time()


"""
##########################################################
User options
"""

#Initial variable assignment
inImage                 = 'C:/Temp/YourImage.tif' #E.g 'C:/Temp/BigImage.tif'
fadeDistance            = 200 #Number of pixels to fade the border by. Ensure this is an int greater than 0
editFadeBoundary        = True #Whether you want the process to stop to allow you to edit which sides of the raster you want to fade


#Options for compressing the images, ZSTD gives the best speed but LZW allows you to view the thumbnail in windows explorer
compressOptions =       'COMPRESS=ZSTD|NUM_THREADS=ALL_CPUS|PREDICTOR=1|ZSTD_LEVEL=1|BIGTIFF=IF_SAFER|TILED=YES'
finalCompressOptions =  'COMPRESS=LZW|PREDICTOR=2|NUM_THREADS=ALL_CPUS|BIGTIFF=IF_SAFER|TILED=YES|PHOTOMETRIC=RGB'
gdalOptions =           '--config GDAL_NUM_THREADS ALL_CPUS -overwrite'


"""
##########################################################
Set up some variables
"""

#For use when getting the alpha band to be 255
multiplyTo255 = 255 / fadeDistance

#Set up the layer name for the raster calculations
inImageName = inImage.split("/")
inImageName = inImageName[-1]
inImageName = inImageName[:len(inImageName)-4]
outImageName = inImageName

#Making a folder for processing
rootProcessDirectory = str(Path(inImage).parent.absolute()).replace('\\','/') + '/'
processDirectory = rootProcessDirectory + inImageName + 'FadeProcess' + '/'
if not os.path.exists(processDirectory):        os.mkdir(processDirectory)

#Get the pixel size and coordinate system of the raster
ras = QgsRasterLayer(inImage)
pixelSizeX = ras.rasterUnitsPerPixelX()
pixelSizeY = ras.rasterUnitsPerPixelY()
pixelSizeAve = (pixelSizeX + pixelSizeY) / 2
rasExtent = ras.extent()


"""
####################################################################################
Main work to create a fading alpha band
"""

#Get the alpha band out
processing.run("gdal:translate", {'INPUT':inImage,'TARGET_CRS':None,'NODATA':None,'COPY_SUBDATASETS':False,'OPTIONS':compressOptions,'EXTRA':'-b 4 -scale_1 128 255 -1000 1255',
    'DATA_TYPE':0,'OUTPUT':processDirectory + 'AlphaClean.tif'})

#Then turn this into polygons
processing.run("gdal:polygonize", {'INPUT':processDirectory + 'AlphaClean.tif','BAND':1,'FIELD':'DN','EIGHT_CONNECTEDNESS':False,'EXTRA':'','OUTPUT':processDirectory + 'Extent.gpkg'})

#Fix it up in case there are any issues
processing.run("native:fixgeometries", {'INPUT':processDirectory + 'Extent.gpkg','OUTPUT':processDirectory + 'ExtentFix.gpkg'})

#Only get the areas with alpha that says it should be opaque
processing.run("native:extractbyexpression", {'INPUT':processDirectory + 'ExtentFix.gpkg','EXPRESSION':' \"DN\" > 200','OUTPUT':processDirectory + 'ExtentFixFilt.gpkg'})

#Buffer this inwards a touch
processing.run("native:buffer", {'INPUT':processDirectory + 'ExtentFixFilt.gpkg','DISTANCE':pixelSizeAve * -0.25,'SEGMENTS':5,'END_CAP_STYLE':0,'JOIN_STYLE':0,
    'MITER_LIMIT':2,'DISSOLVE':False,'OUTPUT':processDirectory + 'ExtentFixFiltBuffer.gpkg'})

#Convert the polygon to lines
processing.run("native:polygonstolines", {'INPUT':processDirectory + 'ExtentFixFiltBuffer.gpkg','OUTPUT':processDirectory + 'ExtentFixFiltBufferLines.gpkg'})

#If you've opted to edit the fade boundary then there is a prompt to do so
if editFadeBoundary:
    box = QMessageBox()
    box.setIcon(QMessageBox.Question)
    box.setWindowTitle("Ok time to do edits")
    box.setText("The boundary lines have been created, so open up\n\n" + processDirectory + "ExtentFixFiltBufferLines.gpkg\n\nin a separate instance of QGIS, edit the lines, then save them.\n\nOnce you're done hit 'Good to go'.")
    box.setStandardButtons(QMessageBox.Yes)
    buttonY = box.button(QMessageBox.Yes)
    buttonY.setText('Good to go')
    box.exec_()

#Rasterise these lines
processing.run("gdal:rasterize", {'INPUT':processDirectory + 'ExtentFixFiltBufferLines.gpkg','FIELD':'','BURN':1,'UNITS':1,'WIDTH':pixelSizeX,'HEIGHT':pixelSizeY,'EXTENT':rasExtent,
    'NODATA':None,'OPTIONS':compressOptions,'DATA_TYPE':0,'INIT':None,'INVERT':False,'EXTRA':'','OUTPUT':processDirectory + 'ExtentFixFiltBufferLinesRasterize.tif'})

#Create a euclidean distance raster
processing.run("gdal:proximity", {'INPUT':processDirectory + 'ExtentFixFiltBufferLinesRasterize.tif','BAND':1,'VALUES':'1','UNITS':1,'MAX_DISTANCE':fadeDistance,'REPLACE':None,'NODATA':fadeDistance,
    'OPTIONS':compressOptions,'EXTRA':'','DATA_TYPE':1,'OUTPUT':processDirectory + 'ExtentFixFiltBufferLinesRasterizeDistance.tif'})

#Change this to have values between 0 and 255ish
processing.run("gdal:rastercalculator", {'INPUT_A':processDirectory + 'ExtentFixFiltBufferLinesRasterizeDistance.tif','BAND_A':1,'INPUT_B':processDirectory + 'AlphaClean.tif','BAND_B':1
    ,'FORMULA':'(A.astype(numpy.float64) * ' + str(multiplyTo255) + ') * (B>127)','RTYPE':2,'NO_DATA':-1,'OPTIONS':compressOptions,'EXTRA':'','OUTPUT':processDirectory + 'NewAlphaBand.tif'})
 
#Ensure the values are legitimately 0-255
processing.run("gdal:warpreproject", {'INPUT':processDirectory + 'NewAlphaBand.tif','SOURCE_CRS':None,'TARGET_CRS':None,'RESAMPLING':0,'NODATA':None,'TARGET_RESOLUTION':None,
    'OPTIONS':compressOptions,'DATA_TYPE':1,'TARGET_EXTENT':rasExtent,'TARGET_EXTENT_CRS':None,'MULTITHREADING':True,'EXTRA':gdalOptions,'OUTPUT':processDirectory + 'NewAlphaBandByte.tif'})

"""
#######################################################################
Bringing all the bands together
"""

#Get the red, green and blue bands of the original raster just as vrts
processing.run("gdal:translate", {'INPUT':inImage,'TARGET_CRS':None,'NODATA':None,'COPY_SUBDATASETS':False,'OPTIONS':'','EXTRA':'-b 1','DATA_TYPE':0,'OUTPUT':processDirectory + 'Band1Virtual.vrt'})
processing.run("gdal:translate", {'INPUT':inImage,'TARGET_CRS':None,'NODATA':None,'COPY_SUBDATASETS':False,'OPTIONS':'','EXTRA':'-b 2','DATA_TYPE':0,'OUTPUT':processDirectory + 'Band2Virtual.vrt'})
processing.run("gdal:translate", {'INPUT':inImage,'TARGET_CRS':None,'NODATA':None,'COPY_SUBDATASETS':False,'OPTIONS':'','EXTRA':'-b 3','DATA_TYPE':0,'OUTPUT':processDirectory + 'Band3Virtual.vrt'})

#Combine the original rgb bands plus the new alpha band into a vrt
processing.run("gdal:buildvirtualraster", {'INPUT':[processDirectory + 'Band1Virtual.vrt',processDirectory + 'Band2Virtual.vrt',processDirectory + 'Band3Virtual.vrt',processDirectory + 'NewAlphaBandByte.tif'],
    'RESOLUTION':2,'SEPARATE':True,'PROJ_DIFFERENCE':True,'ADD_ALPHA':False,'ASSIGN_CRS':None,'RESAMPLING':0,'SRC_NODATA':'','EXTRA':gdalOptions,'OUTPUT':processDirectory + 'Band123A.vrt'})

#Render out the vrt as a final image
processing.run("gdal:warpreproject", {'INPUT':processDirectory + 'Band123A.vrt','SOURCE_CRS':None,'TARGET_CRS':None,'RESAMPLING':0,'NODATA':None,'TARGET_RESOLUTION':None,
'OPTIONS':finalCompressOptions,'DATA_TYPE':0,'TARGET_EXTENT':None,'TARGET_EXTENT_CRS':None,'MULTITHREADING':True,'EXTRA':gdalOptions + ' -srcalpha -dstalpha','OUTPUT':rootProcessDirectory + inImageName + 'Faded.tif'})

#Build pyramid layers so that you can browse easily
processing.run("gdal:overviews", {'INPUT':rootProcessDirectory + inImageName + 'Faded.tif','CLEAN':False,'LEVELS':'','RESAMPLING':0,'FORMAT':1,'EXTRA':'--config COMPRESS_OVERVIEW JPEG'})


"""
#########################################################################
All done
"""

endTime = time.time()
totalTime = endTime - startTime
print("Done, this took " + str(int(totalTime)) + " seconds")


