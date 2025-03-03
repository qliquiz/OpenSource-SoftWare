# -- Project information -----------------------------------------------------

project = 'ourProject'
copyright = '2025, Artem Maksim'
author = 'Artem Maksim'

# -- General configuration ---------------------------------------------------

extensions = ["myst_parser"]

templates_path = ['_templates']
exclude_patterns = []

import os
import sys
sys.path.insert(0, os.path.abspath(".."))

language = 'ru'

# -- Options for HTML output -------------------------------------------------

html_theme = 'alabaster'
html_static_path = ['_static']
