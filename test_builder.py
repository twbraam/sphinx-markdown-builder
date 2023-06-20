"""
Unit tests for the markdown builder
"""
import os
from pathlib import Path

from sphinx.cmd.build import main

DOCS_PATH = "./docs-tests"
ARGS = ["-M", "markdown", DOCS_PATH, "./docs-build"]


def test_builder():
    main([*ARGS, "-a"])


def test_builder_missing():
    for file in os.listdir(DOCS_PATH):
        Path(DOCS_PATH, file).touch()
        break
    main(ARGS)
