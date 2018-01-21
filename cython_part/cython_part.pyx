#cython: boundscheck=False
#cython: wraparound=False

import numpy as np
cimport numpy as np

import math
from lib.qthreading import interruption_point

"""def cy_update(np.ndarray[double, ndim=2] u, double test1, double test2):
    cdef unsigned int i, j
    for i in xrange(1,u.shape[0]-1):
        for j in xrange(1, u.shape[1]-1):
            u[i,j] = ((u[i+1, j] + u[i-1, j]) * dy2 +
                      (u[i, j+1] + u[i, j-1]) * dx2) / (2*(dx2+dy2))"""

#returns state
#ctypedef np.ndarray[np.float32_t, ndim=2] Array2D_f
ctypedef np.float32_t f32
#Array2D_f = np.ndarray[f32, ndim=2]

def compute_old(r, np.ndarray[f32, ndim=3] reference, kernel):
	cdef np.ndarray[f32, ndim=3] state = reference
	cdef np.ndarray[f32, ndim=3] r_xshifted
	cdef np.ndarray[f32, ndim=3] r_shifted
	for x in xrange(-r, r+1):
		r_xshifted = np.roll(reference, x, 0)
		for y in xrange(-r, r+1):
			r_shifted = np.roll(r_xshifted, y, 1)
			dist = math.hypot(x, y)
			state = np.maximum(state, r_shifted * kernel(dist))
			#interruption_point()
				
	return state
	
def compute(int r, np.ndarray[f32, ndim=3] reference, kernel):
	cdef np.ndarray[f32, ndim=3] state = reference.copy()
	cdef float dist
	cdef int rx, ry, x, y, c
	cdef float kernel_val
	for x in xrange(0, reference.shape[0]):
		for y in xrange(0, reference.shape[1]):
			for rx in xrange(-r, r+1):
				for ry in xrange(-r, r+1):
					if x+rx < 0 or x+rx > reference.shape[0] - 1 or y+ry < 0 or y+ry > reference.shape[1] - 1:
						continue
					dist = math.hypot(rx, ry)
					kernel_val = kernel(dist)
					for c in xrange(3):
						state[x, y, c] = max(state[x, y, c], reference[x+rx, y+ry, c] * kernel_val)
		interruption_point()

	return state

def compute_(r, reference, kernel):
	state = reference.copy()
	for rx in xrange(-r, r+1):
		for ry in xrange(-r, r+1):
			dist = math.hypot(rx, ry)
			
			for x in xrange(r, reference.shape[0]-r-1):
				for y in xrange(r, reference.shape[1]-r-1):
					state[x, y] = np.maximum(state[x, y], reference[x+rx, y+ry] * kernel(dist))
			#interruption_point()
				
	return state