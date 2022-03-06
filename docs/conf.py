import sys

sys.path.append('..')

import gtt

project = 'gtt-drivers'
author = 'Yook74'
version = gtt.__version__
copyright = '2022, Andrew Blomenberg'

extensions = ['sphinx.ext.autodoc']
html_theme = 'classic'
html_sidebars = {'**': ['globaltoc.html', 'relations.html', 'sourcelink.html', 'searchbox.html']}
