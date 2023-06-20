"""Configuration file for the Sphinx documentation builder."""
import os
import sys

sys.path.insert(0, os.path.abspath("."))

project = "sphinx_markdown_builder"
copyright = "Copyright (c) 2006-2023, Liran Funaro."
author = "Liran Funaro"
version = "0.5.5"

extensions = [
    "sphinx.ext.autodoc",  # Core library for html generation from docstrings
    "sphinx.ext.autosummary",  # Create neat summary tables
    "sphinx.ext.intersphinx",  # Link to other project's documentation (see mapping below)
    "sphinx_markdown_builder",
]


# Intersphinx manages the connections between books.
# Normally the references in a book are downloaded from readthedocs.  But you
# can also provide a local file to look in.  It's easier to fix broken
# references betweeen books if you can do a local build and use the local
# reference files.  These helper functions are for both reducing the repetition
# in the mapping dictionary, and for optionally specifying a local file to look
# in if it exists.
#
# We often use the same directory to build two books (edX vs Open edX).  In
# those cases, only use ism_location for one book, not both, or we'll be
# looking for A's references in an index built for B.
#
# openedx_rtd_url is for books that are branched and built for specific Open
# edX releases.  edx_rtd_url is for books that are not.


def edx_rtd_url(slug):
    """Make an RTD URL for a book that doesn't branch for each release."""
    return f"https://edx.readthedocs.io/projects/{slug}/en/latest/"


def openedx_rtd_url(slug):
    """Make an RTD URL for a book that branches for each release."""
    return f"https://edx.readthedocs.io/projects/{slug}/en/latest/"


intersphinx_mapping = {
    "python": ("https://docs.python.org/3/", None),
    "torch": ("https://pytorch.org/docs/stable/", None),
    "opencoursestaff": (
        openedx_rtd_url("open-edx-building-and-running-a-course"),
        None,
    ),
    "data": (edx_rtd_url("devdata"), None),
    "partnercoursestaff": (edx_rtd_url("edx-partner-course-staff"), None),
    "insights": (edx_rtd_url("edx-insights"), None),
    "xblockapi": (edx_rtd_url("xblock"), None),
    "xblocktutorial": (edx_rtd_url("xblock-tutorial"), None),
    "installation": (openedx_rtd_url("edx-installing-configuring-and-running"), None),
    "olx": (edx_rtd_url("edx-open-learning-xml"), None),
    "learners": ("", None),
    "openlearners": (openedx_rtd_url("open-edx-learner-guide"), None),
    "opendevelopers": (edx_rtd_url("edx-developer-guide"), None),
    "opendataapi": (edx_rtd_url("edx-data-analytics-api"), None),
    "openreleasenotes": (edx_rtd_url("open-edx-release-notes"), None),
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

templates_path = ["_templates"]
exclude_patterns = ["_expected"]

language = "en"

markdown_anchor_sections = True
markdown_anchor_signatures = True
