import sys
from typing import Sequence

from sphinx.cmd import build

from sphinx_markdown_builder import concat


def main(argv: Sequence[str] = (), /) -> int:
    argv = list(argv)
    argv[1:] = ["-b", "markdown", "source", "build/markdown"]

    exit_code = build.main(argv)
    if exit_code:
        return exit_code
    return concat.main()


if __name__ == '__main__':
    raise SystemExit(main(sys.argv[1:]))
