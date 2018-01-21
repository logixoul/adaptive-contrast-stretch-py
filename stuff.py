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
		d = self.options.d
		r = d//2
		
		if np.amax(srcImage) > 1.0:
			tgui.msgbox("detected hdr, applying reinhard")
			srcImage = hdr.luminanceReinhard(srcImage)
		#else:
			#tgui.msgbox("not hdr, max is " + np.amax(srcImage))
		
		def kernel_(x, k): return math.exp(-k * (x**2))
		#def kernel_(x, k): return math.pow(1.0 / (1.0 + k * (x ** 2)), self.options.power)
		#def kernel_(x, k): return math.pow(1.0 / (1.0 + k * x), self.options.power)
		THRES = 0.1
		k = Static.choose_k(kernel_, THRES, r)
		print "chosen k ", k
		#k = (1.0/self.options.sigma_scale) * (1.0/THRES-1.0)/(r**2)
		def kernel(x):
			return kernel_(x, k)
		
		d += self.options.dscale - 1
		r = d//2
		
		stElement = cv2.getStructuringElement(cv2.MORPH_RECT, (downscale, downscale))
		preDownsize = { cv2.min: cv2.erode, cv2.max: cv2.dilate }[func]
		srcImage2 = preDownsize(srcImage, stElement)
		
		srcImageSmall = cv2.resize(srcImage2, (0,0), None, 1.0/downscale, 1.0/downscale, cv2.INTER_NEAREST)
		reference = srcImageSmall
		if func == cv2.min:
			reference = 1.0 - reference
		
		import cython_part as cy
		state = [ None ]
		
		def toTime():
			state[0] = cy.compute(r, reference, kernel)
		def toTimeOld():
			state[0] = self.old_compute(r, reference, kernel)
		import timeit
		print "old: ", timeit.Timer(toTimeOld).timeit(1)
		#print "new: ", timeit.Timer(toTime).timeit(1)
		
		if func == cv2.min:
			state[0] = 1.0 - state[0]
		result = cv2.resize(state[0], (srcImage.shape[1], srcImage.shape[0]), None, 0, 0, cv2.INTER_CUBIC)
		result = np.roll(result, -self.options.offsetfix, 0)
		result = np.roll(result, -self.options.offsetfix, 1)
		result = np.minimum(1.0, np.maximum(0.0, result)) #lanczos overshoot
		return result
	
@StaticMethod
def profile(func):
	import cProfile
	cProfile.runctx('do()', {}, {'do':func}, "cProfile_data.txt")
	import pstats
	p = pstats.Stats("cProfile_data.txt")
	p.sort_stats('cumulative')
	p.print_stats(10)
	

	def old_compute(self, r, reference, kernel):
		state = reference
		for x in xrange(-r, r+1):
			r_xshifted = np.roll(reference, x, 0)
			for y in xrange(-r, r+1):
				r_shifted = np.roll(r_xshifted, y, 1)
				dist = math.hypot(x, y)
				state = np.maximum(state, r_shifted * kernel(dist))
				interruption_point()
		return state
	
	@StaticMethod
	def smoothen(image, iterations):
		image2 = image
		for i in xrange(iterations):
			tgui.status("smoothing iteration %s/%s" % (i, iterations))
			blurred = cv2.GaussianBlur(image2, (0, 0), 2.0)
			#blurred = cv2.blur(image2, (13, 13))
			absdiff = np.absolute(blurred - image)
			isDiffSmall = np.less_equal(absdiff, 1.0 / 255.0).astype(np.float32)
			image2 = image2 + (blurred - image2) * isDiffSmall
		tgui.status("smoothing done")
		return image2
	
	# wCoef -> 1: wider. wCoef -> 0: narrower
	@StaticMethod
	def poissonConvolve(img, wCoef, iterations = 50):
		kernel = np.array(
			[[ 0, 1, 0 ],
			 [ 1, 0, 1 ],
			 [ 0, 1, 0 ]], dtype=np.float32
			 ) / 4.0
		state = img
		for i in xrange(iterations):
			state = wCoef * cv2.filter2D(state, -1, kernel, borderType=cv2.BORDER_REPLICATE) +\
				(1.0 - wCoef) * img
		return state
	