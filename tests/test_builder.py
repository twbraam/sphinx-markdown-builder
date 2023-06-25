"""
Unit tests for the markdown builder
"""
import os
import shutil
from pathlib import Path
from typing import Iterable

import pytest
from sphinx.cmd.build import main

BUILD_PATH = "./tests/docs-build"
SOURCE_PATH = "./tests/source"

TEST_NAMES = ["direct", "http"]
SOURCE_FLAGS = [[], ["-D", 'markdown_http_base="https://localhost"', "-D", 'markdown_uri_doc_suffix=".html"']]
BUILD_PATH_OPTIONS = [os.path.join(BUILD_PATH, "direct"), os.path.join(BUILD_PATH, "http")]
OPTIONS = list(zip(SOURCE_FLAGS, BUILD_PATH_OPTIONS))


def run_sphinx(build_path, *flags):
    return main(["-M", "markdown", SOURCE_PATH, build_path, *flags])


@pytest.mark.parametrize(["flags", "build_path"], OPTIONS, ids=TEST_NAMES)
def test_builder_make_all(flags: Iterable[str], build_path: str):
    run_sphinx(build_path, "-a", *flags)


@pytest.mark.parametrize(["flags", "build_path"], OPTIONS, ids=TEST_NAMES)
def test_builder_make_updated(flags: Iterable[str], build_path: str):
    for file in os.listdir(SOURCE_PATH):
        Path(SOURCE_PATH, file).touch()
        break
    run_sphinx(build_path, *flags)


@pytest.mark.parametrize(["flags", "build_path"], OPTIONS, ids=TEST_NAMES)
def test_builder_make_missing(flags: Iterable[str], build_path: str):
    if os.path.exists(build_path):
        shutil.rmtree(build_path)
    run_sphinx(build_path, *flags)
