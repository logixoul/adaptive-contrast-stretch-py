from __future__ import division
import lib
import lib.gui as tgui
import lib.ip as ip
import lib.math as lmath
import cv2, math, numpy, numpy as np, itertools
tgui.DEBUG_WINDOWS = True
import lib.cv3 as cv3
import lib.hdr as hdr
import sys
from lib.lang import StaticMethod
from PyQt5 import QtCore
import lib.cvhelpers as cvhelpers
from lib.qthreading import interruption_point
import colorama
from lib.ip_gui import ImgPack

class ContrastOperator:
	__slots__ = [
		'srcImage',
		'boundaryMaps',
		'options',
		'imgpack',
		'begin_time',
		'srcImageG'
		]
	
	def __init__(self, srcImage, options):
		self.srcImage = srcImage
		self.options = options
		self.imgpack = ImgPack()
		
	# HELPER METHODS
	@StaticMethod
	def choose_k(func, thres, r):
		import scipy.optimize
		def toMinimize(k):
			return abs(func(float(r), k) - thres)
		result = scipy.optimize.minimize(toMinimize, 0.0, method='nelder-mead',
			options={'disp':False,'ftol':.01,'maxfev':1000000,'maxiter':1000000})
		if not result.success:
			raise Exception("couldn't optimize. cause of termination: %s" % result.message)
		k = result.x[0]
		return k
	
	def makeBoundaryMap3(self, srcImage, func, iterations, downscale, blurWidth=4.0):
		#downscale = 1.0/16.0
		d = self.options.method3_d
		r = d//2
		
		def kernel_(x, k): return math.exp(-k * (x**2))
		THRES = self.options.method3_thres
		k = Static.choose_k(kernel_, THRES, r)
		print("chosen k ", k)
		def kernel(x):
			return kernel_(x, k)
		
		d += self.options.method3_dscale
		if d % 2 == 0:
			d += 1
		r = d//2
		
		#stElement = cv2.getStructuringElement(cv2.MORPH_RECT, (downscale, downscale), (0,0))
		stElement =\
			np.zeros((downscale*2-1, downscale*2-1), dtype=np.uint8)
		stElement[downscale-1:,downscale-1:]=1
		preDownsize = { cv2.min: cv2.erode, cv2.max: cv2.dilate }[func]
		srcImage2 = preDownsize(srcImage, stElement)
		srcImageSmall = cv2.resize(srcImage2, (0,0), None, 1.0/downscale, 1.0/downscale, cv2.INTER_NEAREST)
		reference = srcImageSmall
		if func == cv2.min:
			reference = 1.0 - reference
		state = reference
		for x in range(-r, r+1):
			ref_xshifted = np.roll(reference, x, 0)
			for y in range(-r, r+1):
				ref_shifted = np.roll(ref_xshifted, y, 1)
				dist = math.hypot(x, y)
				state = np.maximum(state, ref_shifted * kernel(dist))
				interruption_point()
		if func == cv2.min:
			state = 1.0 - state
		result = cv2.resize(state, (srcImage.shape[1], srcImage.shape[0]), None, 0, 0, cv2.INTER_LINEAR)
		result = np.minimum(1.0, np.maximum(0.0, result)) #lanczos overshoot
		return result
	
	makeBoundaryMapCurrent = makeBoundaryMap3
	
	# f(x)=a + b * x^c
	# f(0) = lB
	# f(1) = 1
	# f'(1) = 1
	
	# a=lB
	# a + b = 1		=> b=1-lB
	# f(x) = lB + (1-lB) * x^c
	# c * b * 1^(c-1) = 1		=> c*b=1 => c=1/(1-lB)
	# => f(x) = lB + (1-lB) * x^(1/(1-lB))
	@StaticMethod
	def contrastLimitingFunction(value, lowerBound):
		return value
		"""lB = lowerBound
		x = value
		return lB + (1-lB) * np.power(x, 1/(1-lB))"""
		#return lowerBound * value * value + (1.0-2.0*lowerBound) * value + lowerBound
	
	@StaticMethod
	def adjustRange(rangeMaps, contrast): # rangeMaps is a tuple
		minMap, maxMap = rangeMaps
		rangeMap = maxMap - minMap
		mappedContrast = lib.math.expRange(100.0, 1.0, contrast)
		rangeMap *= mappedContrast
		rangeMap = Static.contrastLimitingFunction(rangeMap, 30.0/255.0)
		middleMap = .5 * (maxMap + minMap)
		minMap = middleMap - rangeMap * .5
		maxMap = middleMap + rangeMap * .5
		#minMap = np.maximum(minMap, 0.0)
		#maxMap = np.minimum(maxMap, 1.0)
		return (minMap, maxMap)
	
	@StaticMethod
	def stretchArrayLocally(minMap, maxMap, values, contrast):
		minMap, maxMap = Static.adjustRange((minMap, maxMap), contrast)
		
		maxMap=cv2.max(maxMap,minMap)
		minMap=cv2.min(maxMap,minMap)
		result = (values-minMap)/(maxMap-minMap)
		result = np.nan_to_num(result)
		#result = lib.ip.to01(result)
		result = np.minimum(np.maximum(result, 0.0), 1.0)
		return result
	
	@StaticMethod
	def smoothGaussianBlur(img, diameter):
		ksize = int(math.ceil(diameter))
		if ksize % 2 == 0:
			ksize += 1
		return cv2.GaussianBlur(img, (ksize, ksize), lib.cvhelpers.getSigmaForDiameter(diameter))
	
	# amount=0 => no sharpening
	# amount=1 => strong sharpening
	# amount>1 => even stronger
	@StaticMethod
	def sharpen(img, radius, amount):
		diameter = 2.0 * radius + 1.0
		ksize = int(math.ceil(diameter))
		if ksize % 2 == 0:
			ksize += 1
		blurred = cv2.GaussianBlur(img, (ksize, ksize), lib.cvhelpers.getSigmaForDiameter(diameter))
		return img + (img - blurred) * amount
	
	def run(self):
		#lib.break_()
		self.srcImage = self.srcImage[:,:,:3]/(255.0 if self.options.divide_by_255 else 1.0)
		
		if self.options.awb == 1:
			avgR = np.average(self.srcImage[:,:,0])
			avgG = np.average(self.srcImage[:,:,1])
			avgB = np.average(self.srcImage[:,:,2])
			self.srcImage[:,:,1] *= avgR / avgG
			self.srcImage[:,:,2] *= avgR / avgB
		
		srcImage0 = self.srcImage.copy()
		b1 = Static.smoothGaussianBlur(self.srcImage, 4.0 * self.srcImage.shape[0] / 300.0)
		self.srcImage *= b1
		self.srcImage = np.minimum(self.srcImage, 1.0)
		
		#self.srcImage = hdr.luminanceReinhard(self.srcImage)
		def geomAverage(arr):
			return np.exp(np.average(np.log(arr+0.000001)))
		self.imgpack["src0"] = srcImage0
		self.imgpack["src"] = self.srcImage
		#self.imgpack["src[scaled]"] = hdr.luminanceReinhard(self.srcImage/geomAverage(self.srcImage))
		
		self.srcImageG = ip.linToGrayscale(self.srcImage)#, ip.METHOD_LUMINANCE)
		self.imgpack["srcImageG"] = self.srcImageG
		blurWidth = self.options.d
		minMap = self.makeBoundaryMapCurrent(self.srcImageG, cv2.min,
				iterations=self.options.iterations, downscale=self.options.quality, blurWidth=blurWidth)
		self.imgpack["min map"] = minMap
		maxMap = self.makeBoundaryMapCurrent(self.srcImageG, cv2.max,
			iterations=self.options.iterations, downscale=self.options.quality, blurWidth=blurWidth)
		self.imgpack["max map"] = maxMap
		
		result = Static.stretchArrayLocally(minMap, maxMap, self.srcImageG, self.options.contrast)
		self.imgpack["before luminance blend"] = result
		resultHLS = ip.luminanceBlendHLS(result, self.srcImage)
		lib.mm(result,"result")
		
		self.imgpack["resultHLS"] = resultHLS
		
		resultHSV = ip.luminanceBlendHSV(result, self.srcImage)
		
		self.imgpack["resultHSV"] = resultHSV
		
		resultXYZ = ip.luminanceBlendXYZ_(result, self.srcImage)
		self.imgpack["resultXYZ"] = resultXYZ
		print("done")