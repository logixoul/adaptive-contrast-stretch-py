#! /usr/bin/python

"""import distutils.core
import distutils.extension
from Cython.Build import cythonize

distutils.core.setup(
  name = 'Hello world app',
  ext_modules = cythonize('cython_part.pyx'), # accepts a glob pattern
)"""

from distutils.core import setup
from distutils.extension import Extension
from Cython.Distutils import build_ext

ext_modules=[
    Extension("cython_part", ["cython_part.pyx"])
]

setup(
  name = 'MyProject',
  cmdclass = {'build_ext': build_ext},
  ext_modules = ext_modules,
)