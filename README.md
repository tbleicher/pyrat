## pyrat

This project aims to provide applications to simplify the use of the Radiance lighting simulation tools.
The focus is on usability improvements and platform independence.

## Current Tools

### falsecolor2.py

My extensions of the original csh falsecolor now converted to Python. Python is just much less
complicated to handle than csh and it will run on Windows, too. The original announcement and
home page is here (needs update to reflect the different command line parameters):

http://sites.google.com/site/tbleicher/radiance/falsecolor2

### wxfalsecolor.py
Graphical frontend to falsecolor2.py. I keep the documentation on a separate web site because
I haven't figured out yet how to integrate images in this document:

http://sites.google.com/site/tbleicher/radiance/wxfalsecolor

## Future Tools and Ideas

### rad2/wxrad2

A new (graphical) rif file processor. I already had written parts of rad in
Python for my old Blender exporter. It's basically there to avoid the need for
a command line. You should be able to explore the dependency tree, the individual
calculation steps and progress of running jobs. There are a couple of advanced calculation
methods out there (like stencil) that could be easily supported by a frontend like this.

Similar to trad and Ecotect's Radiance Control Panel.

### render daemon

A small app that sits in your task bar and watches your running simulations and
incoming rif or makefile-type render jobs. Could also have a network component
which offloads the work to a render server or farm. I need something like this as
a starting point for scenes exported from SketchUp?.

### Python bindings for HDR images

falsecolor2 uses the subprocess module and pvalue to read image data. That takes
a long time and is needlessly complicated. I would like to try to compile the few
methods necessary as C Python extensions. After that the functionality of pcompos,
pcomb and other psomething apps could be reimplemented in pure Python (or these apps
could be made Python extensions as well).

### Bits and Pieces

A couple of scripts to create plots and PDF reports from grids.

## History

Automatically exported from code.google.com/p/pyrat in March 2015.

