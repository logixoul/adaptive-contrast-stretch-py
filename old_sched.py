from PyQt4 import QtGui, QtCore
import lib
import sys

_threads = []
_reachedId = 0
mutex = QtCore.QMutex(QtCore.QMutex.NonRecursive)
	
def thread(runnable, desc = "<no-description>"):
	runnable()

def thread(runnable, desc = "<no-description>"):
	thread = lib.qthreading.Thread(runnable)
	thread.start()
	global _reachedId
	_reachedId_copy = _reachedId
	lib.write("[sched.thread] thread %s started (\"%s\")" % (_reachedId, desc))
	with QtCore.QMutexLocker(mutex):
		_threads.append(thread)
	def onFinished():
		lib.write("[sched.thread] thread %s ended (\"%s\")" % (_reachedId_copy, desc))
		with QtCore.QMutexLocker(mutex):
			_threads.remove(thread)
	thread.finished.connect(onFinished)
	_reachedId += 1
	
	"""def progressdlgTask():
		progressdlg = QtGui.QProgressDialog("Thread started: %s" % desc, "Cancel", 0, 100)
		progressdlg.show()
		def onFinished():
			lib.threadtasks.post(lambda: progressdlg.close())
			with QtCore.QMutexLocker(mutex):
				_threads.remove(thread)
		qrunnable.onFinished = onFinished
	lib.threadtasks.post(progressdlgTask)"""
	return thread

def as_thread(fn):
    def wrapped(*args, **kw):
		thread(lambda: fn(*args, **kw))
    return wrapped