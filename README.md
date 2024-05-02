This script runs in QGIS's python console and fades the alpha band around the edge by a specified amount of pixels

This is able to handle images with complex borders (i.e not rectangular)

_________________

This only works on RGBA rasters

It assumes that the original alpha band is either 0 or 255

Make sure the pixel fading distance is an int that is greater than 0, but not so great that it's as big as the image is wide

This script could be improved to allow the user to smooth the corners

_________________

Any issues let me know

