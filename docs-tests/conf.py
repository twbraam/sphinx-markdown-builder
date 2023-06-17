"""Configuration file for the Sphinx documentation builder."""

project = "sphinx_markdown_builder"
copyright = "Copyright (c) 2006-2023, Liran Funaro."
author = "Liran Funaro"
version = "0.5.5"

extensions = [
    "sphinx.ext.napoleon",
    "sphinx.ext.autodoc",  # Core library for html generation from docstrings
    "sphinx.ext.autosummary",  # Create neat summary tables
    "sphinx.ext.intersphinx",  # Link to other project's documentation (see mapping below)
    "sphinx_markdown_builder",
]

intersphinx_mapping = {
    "python": ("https://docs.python.org/3/", None),
    "torch": ("https://pytorch.org/docs/stable/", None),
}

autosummary_generate = True  # Turn on sphinx.ext.autosummary
autoclass_content = "both"  # Add __init__ doc (i.e., params) to class summaries
html_show_sourcelink = True  # Remove 'view source code' from top of page (for html, not python)
html_copy_source = True
autodoc_inherit_docstrings = True  # If no docstring, inherit from base class
set_type_checking_flag = True  # Enable 'expensive' imports for sphinx_autodoc_typehints
autodoc_typehints = "description"  # Sphinx-native method. Not as good as sphinx_autodoc_typehints
add_module_names = False  # Remove namespaces from class/method signatures
autodoc_member_order = "bysource"

templates_path = []
exclude_patterns = []

language = "en"
