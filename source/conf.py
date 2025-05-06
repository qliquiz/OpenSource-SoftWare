# -- Project information -----------------------------------------------------

project = 'OpenSource SoftWare'
copyright = '2025, Artem'
author = 'Artem'

# -- General configuration ---------------------------------------------------

extensions = [
    "myst_parser",
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
]

templates_path = ['_templates']
exclude_patterns = []
autodoc_mock_imports = ["questionary", "fastapi"]

import os
import sys
sys.path.insert(0, os.path.abspath("../TestingMocks"))

language = 'ru'

# -- Options for HTML output -------------------------------------------------

html_theme = 'alabaster'
html_static_path = ['_static']
