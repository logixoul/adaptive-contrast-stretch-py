from PyQt4 import QtGui, QtCore
import sys, ctypes, os
import numpy
import cv2
import lib.interop
from third_party.imageviewer import ImageViewer
import sched
import lib
from lib import threadtasks
from lib.lang import StaticMethod

app = QtGui.QApplication(sys.argv)
    
def init():
	import signal
	signal.signal(signal.SIGINT, signal.SIG_DFL)
#	#app = QtGui.QApplication(sys.argv)

def mainLoop():
    app.exec_()

_this_module = sys.modules[__name__]

class SliderSet:
	WINDOW_NAME = "slider"
	def __init__(self):
		self.widget = QtGui.QWidget()
		self.widget.setMinimumWidth(300)
		self.layout = QtGui.QFormLayout(self.widget)
		
		# =========== PUBLIC SIGNALS ===========
		self.onMoved = lambda name, value: None
	
	def addSlider(self, name, min, max, initialValue, valueMapper=lambda x: x):
		def forwardOnmoved(slider, value):
			global mdi
			setattr(mdi.options, name, valueMapper(value))
			self.onMoved(name, valueMapper(value))
			status(str(valueMapper(value)))
		slider = QtGui.QSlider(QtCore.Qt.Horizontal)
		slider.setRange(min, max)
		self.layout.addRow(name, slider)
		slider.setTracking(False)
		slider.sliderMoved.connect(lambda value: forwardOnmoved(slider, value))
		slider.setValue(initialValue)
		global mdi
		setattr(mdi.options, name, valueMapper(initialValue))

class MDI(QtGui.QWidget):
	class OptionsClass:
		pass
	def __init__(self):
		super(MDI, self).__init__()
		
		#self.setWindowTitle("_py2_")
		
		#===================== PUBLIC EVENTS ==========================
		self.onNewImage = lambda img: None
		self.onKey = lambda key: None
		#==============================================================
		self.options = MDI.OptionsClass()
		
		
		self.layout = QtGui.QHBoxLayout()
		
		self.sidebar = QtGui.QVBoxLayout()
		self.layout.addLayout(self.sidebar)
		
		self.sliders = SliderSet()
		
		self.setLayout(self.layout)
		self.tabWidget = QtGui.QTabWidget()
		self.layout.addWidget(self.tabWidget, 1)
		
		paste = QtGui.QPushButton("paste")
		paste.clicked.connect(self.pasteImage)
		self.sidebar.addWidget(paste)
		
		zoomToFit = QtGui.QPushButton("actual size")
		zoomToFit.clicked.connect(self.zoomToFit)
		self.sidebar.addWidget(zoomToFit)
		self.progressbar = QtGui.QProgressBar()
		self.progressbar.setMinimum(0)
		self.progressbar.setMaximum(0)
		
		self.statusbar = QtGui.QLabel("-")
		self.sidebar.addWidget(self.statusbar)
		self.sidebar.addWidget(self.sliders.widget, 10)
		self.sidebar.addWidget(self.progressbar)
		self.show()
		self.setAcceptDrops(True)
		#shortcut = QtGui.QShortcut(QtGui.QKeySequence(QtGui.QKeySequence.Copy), self)
		shortcut = QtGui.QShortcut(QtGui.QKeySequence(QtGui.QKeySequence.Paste), self)
		shortcut.activated.connect(self.pasteImage)
		self.connectShortcut(QtGui.QKeySequence(QtCore.Qt.Key_Left), lambda: self.prevNextTab(-1))
		self.connectShortcut(QtGui.QKeySequence(QtCore.Qt.Key_Right), lambda: self.prevNextTab(1))
		self.connectShortcut(QtGui.QKeySequence(QtCore.Qt.Key_Up), lambda: self.quickJump(0))
		self.connectShortcut(QtGui.QKeySequence(QtCore.Qt.Key_Down), lambda: self.quickJumpBack())
		#self.connectShortcut(QtGui.QKeySequence(Qt.QtGui.Key_Control, Qt.QtGui.Key_Plus),
		#	lambda: 
		self.setWindowState(QtCore.Qt.WindowMaximized)
		self.imageViewers = []
		#self.toolbar = QtGui.QToolBar()
		#self.installEventFilter(self)
		self.animation = None
		self.tabs = { } # dict from name to widget
		
		self.setInProgress(False)
		
	"""def flashStatus(self):
		del self.animation
		self._status_color = QtGui.QColor(255,0,0)
		self.animation = QtCore.QPropertyAnimation(self, "status_color", self)
		self.animation.setDuration(2000)
		self.animation.setStartValue(QtGui.QColor(255,0,0,255))
		self.animation.setEndValue(QtGui.QColor(255,0,0,0))

		self.animation.start()
	
	@QtCore.pyqtProperty(QtGui.QColor)
	def status_color(self):
		return self._status_color
	
	@StaticMethod
	def fmt_css_color(c):
		return "rgba(%s, %s, %s, %s)" % (c.red(), c.green(), c.blue(), c.alpha())
	
	@status_color.setter
	def status_color(self, value):
		self._status_color = value
		self.statusbar.setStyleSheet("background-color: " + Static.fmt_css_color(value))"""
		
	def setInProgress(self, enable):
		if enable:
			self.progressbar.setMaximum(0)
		else:
			if self.progressbar.maximum() == 0:
				self.progressbar.setMaximum(1)
		
	def prevNextTab(self, offset):
		index = self.tabWidget.currentIndex() + offset
		index %= self.tabWidget.count()
		self.tabWidget.setCurrentIndex(index)
		
	def quickJump(self, index):
		if self.tabWidget.currentIndex() == index:
			return
		self.beforeQuickJump = self.tabWidget.currentIndex()
		self.tabWidget.setCurrentIndex(index)
		
	def quickJumpBack(self):
		if not hasattr(self, "beforeQuickJump"):
			return
		self.tabWidget.setCurrentIndex(self.beforeQuickJump)
		
	def connectShortcut(self, keyseq, callback): # keyseq is e.g. QtGui.QKeySequence.Paste
		shortcut = QtGui.QShortcut(QtGui.QKeySequence(keyseq), self)
		shortcut.activated.connect(callback)
	
	#def eachViewer(self, func):
		#for viewer in self.imageViewers:
			#
		
	def zoomToFit(self):
		for viewer in self.imageViewers:
			#viewer.actualSize()
			viewer._view.fitInView(viewer._pixmapItem, QtCore.Qt.KeepAspectRatio)
		lib.write("zoomtofit")
	
	def synchViews(self, srcView, name):
		pass
		"""if hasattr(self, 'currentlySynching') and self.currentlySynching:
			return
		self.currentlySynching = True
		for viewer in self.imageViewers:
			if viewer is srcView:
				continue
			viewer.zoomFactor = srcView.zoomFactor
			viewer.scrollState = srcView.scrollState
		self.currentlySynching = False"""
	
	def pasteImage(self):
		self.status("getting image from clipboard")
		clipboard = QtGui.QApplication.clipboard()
		image = clipboard.image()
		if image.isNull():
			return
		self.status("converting to cv format")
		cvImage = lib.interop.all.image_qt2cv(image)
		lib.write("loaded with depth", cvImage.dtype)

		self.status("calling onNewImage")
		self.onNewImage(cvImage)
		self.status("done")
	
	@threadtasks.as_task
	def status(self, text):
		self.statusbar.setText(text)
		QtGui.QApplication.processEvents()
		
	def dragEnterEvent(self, e):
		lib.write("dragenter")
		e.acceptProposedAction()
	
	def dropEvent(self, e):
		lib.write("dropEvent. mime formats:", e.mimeData().formats()[0])
		lib.write("hasimage? ", e.mimeData().hasImage())
		if not e.mimeData().hasImage():
			if e.mimeData().formats().contains("text/uri-list"):
				filePath=e.mimeData().data("text/uri-list")
				filePath=str(filePath)[7:-2].replace("%20", " ")
				#def bytes(s):
				#	return "[%s]" % ", ".join(str(ord(c)) for c in s)
				image = cv2.imread(filePath, cv2.CV_LOAD_IMAGE_UNCHANGED)
				print "imgshape", image.shape
				import lib.cv2 as cv2
				#r,g,b=cv2.split(image)
				#image = cv2.merge((b,g,r))
				self.onNewImage(image)
				return
			else:
				msgbox("mimedata.hasimage=false")
		qvariant = e.mimeData().imageData()
		lib.write('variant type=', qvariant.type())
		image = QtGui.QImage(qvariant)
		lib.write('width=', image.width())
		lib.write('converted,saving')
		cvImage = lib.interop.all.image_qt2cv(image)
		self.onNewImage(cvImage)
		
		
	def keyPressEvent(self, e):
		if e.key() == QtCore.Qt.Key_Escape:
			QtGui.QApplication.exit()
		else:
			self.onKey(e.key())
			
	def closeEvent(self, e):
		QtGui.QApplication.exit()
	
	def addTab(self, widget, name):
		self.tabs[name] = widget
		self.imageViewers.append(widget)
		
		tabNames = (self.tabWidget.tabText(i) for i in xrange(self.tabWidget.count()))
		index = self.tabWidget.addTab(widget, name)
		
		# fix imagewidget fitToWindow problem before tab is first selected
		self.tabWidget.setCurrentIndex(index)
		QtGui.QApplication.processEvents()
		
		#widget.transformChanged.connect(lambda: self.synchViews(widget, name))
		#widget.scrollChanged.connect(lambda: self.synchViews(widget, name))
	
	@threadtasks.as_task
	def imshow(self, name, image):
		widget = None
		if name in self.tabs:
			widget = self.tabs[name]
		else:
			widget = ImageViewer()
			widget.enableHandDrag(True)
			self.addTab(widget, name)
		widget.pixmap = lib.interop.all.image_cv2qt(image)
		#widget.antigc = qpixmap.antigc
		
mdi = MDI()

def status(text):
	global mdi
	mdi.status(text)
		
def imshow(name, image):
	global mdi
	mdi.imshow(name, image)
	
def addSlider(name, min, max, initialValue, valueMapper=lambda x: x):
	global mdi
	mdi.sliders.addSlider(name, min, max, initialValue, valueMapper)
	
def msgbox(text):
	def task():
		global mdi
		#QtGui.QMessageBox.information(mdi, "main.py", text)

		msgbox = QtGui.QMessageBox(mdi)
		msgbox.setWindowTitle("main.py")
		msgbox.setText(text)
		msgbox.setMinimumWidth(1100)
		#msgbox.exec_()
		msgbox.show()
	lib.threadtasks.post(task)