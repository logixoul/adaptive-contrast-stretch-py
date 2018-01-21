#! /usr/bin/python

import sys
sys.path.append('C:/Users/logix/Desktop/code_/from_linux/py_include/')

import colorama
import os, subprocess
import lib.ip_gui as ip_gui
import implementation2
import lib.gui as tgui
tgui.init() #before import windows

print(colorama.Fore.CYAN + colorama.Style.BRIGHT)
os.chdir("cython_part")
subprocess.call("./setup.py build_ext --inplace", shell=True)
os.chdir("..")
print(colorama.Style.RESET_ALL)

app = ip_gui.App(implementation2.ContrastOperator)
DEFAULT_QUALITY = 1.0/4.0
#tgui.addSlider("power", 0, 200, 100,
#	valueMapper=lambda value: value / 100.0)
tgui.addSlider("contrast", 0, 100, 100,
	valueMapper=lambda value: value / 100.0) #stretchArrayLocally
tgui.addSlider("quality", 0, 32, 1, lambda x: x * 2 + 1) #
tgui.addSlider("divide_by_255", 0, 1, 0)
tgui.addSlider("awb", 0, 1, 0)
tgui.addSlider("method2_stElement_diam", 1, 32, 1,
	lambda value: value * 2 + 1)
#tgui.addSlider("smoothing", 0, 10, 0)
tgui.addSlider("d", 1, 40, 24)
tgui.addSlider("dscale", 1, 40, 8)
#tgui.addSlider("step", 1, 100, 10, lambda x: x / 10.0)
tgui.addSlider("iterations", 1, 300, 30)
#tgui.addSlider("invRh_max", 1, 1000, 1)

#tgui.addSlider("method3_power", 0, 200, 100,
#	valueMapper=lambda value: value / 100.0)
tgui.addSlider("thres", 1, 100, 4, lambda x: x / 100.0)
ip_gui.app.run()
		