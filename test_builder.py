"""
Unit tests for the markdown builder
"""
import os
import shutil
from pathlib import Path

from sphinx.cmd.build import main

DOCS_PATH = "./docs-tests"
BUILD_PATH = "./docs-build"
ARGS = ["-M", "markdown", DOCS_PATH, BUILD_PATH]


def test_builder():
    main([*ARGS, "-a"])


def test_builder_updated():
    for file in os.listdir(DOCS_PATH):
        Path(DOCS_PATH, file).touch()
        break
    main(ARGS)


def test_builder_missing():
    shutil.rmtree(BUILD_PATH)
    main(ARGS)
