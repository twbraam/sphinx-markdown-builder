"""Configuration file for the Sphinx documentation builder."""
import os

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


def ism_location(dir_name):
    """Calculate the intersphinx_mapping location to use for a book.

    `dir_name` is the directory name under edx-documentation/en_us for the book.
    """
    objects_inv = f"../../{dir_name}/build/html/objects.inv"
    if os.path.exists(objects_inv):
        return (objects_inv, None)
    else:
        return None


intersphinx_mapping = {
    "python": ("https://docs.python.org/3/", None),
    "torch": ("https://pytorch.org/docs/stable/", None),
    "opencoursestaff": (
        openedx_rtd_url("open-edx-building-and-running-a-course"),
        ism_location("open_edx_course_authors"),
    ),
    "data": (edx_rtd_url("devdata"), ism_location("data")),
    "partnercoursestaff": (edx_rtd_url("edx-partner-course-staff"), ism_location("course_authors")),
    "insights": (edx_rtd_url("edx-insights"), None),
    "xblockapi": (edx_rtd_url("xblock"), None),
    "xblocktutorial": (edx_rtd_url("xblock-tutorial"), ism_location("xblock-tutorial")),
    "installation": (openedx_rtd_url("edx-installing-configuring-and-running"), ism_location("install_operations")),
    "olx": (edx_rtd_url("edx-open-learning-xml"), ism_location("olx")),
    "learners": ("", ism_location("students_redirect")),
    "openlearners": (openedx_rtd_url("open-edx-learner-guide"), ism_location("open_edx_students")),
    "opendevelopers": (edx_rtd_url("edx-developer-guide"), ism_location("developers")),
    "opendataapi": (edx_rtd_url("edx-data-analytics-api"), None),
    "openreleasenotes": (edx_rtd_url("open-edx-release-notes"), ism_location("open_edx_release_notes")),
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
