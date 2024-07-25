"""
Concatenates all files in build/markdown into one large .md file.
"""

from pathlib import Path
from typing import List


def parse_toctree(file_path: Path):
    toctree_files = []
    lines = file_path.read_text().splitlines()

    toctree_active = False
    for line in lines:
        if line.strip().startswith('.. toctree::'):
            toctree_active = True
            continue
        if toctree_active:
            if line.strip().startswith(':') or line.strip() == '':
                continue
            if line.startswith(' '):
                relative_path = line.strip()
                md_path = (file_path.parent / f"{relative_path}.md").parts[1:]
                toctree_files.append(Path(*md_path))
                nested_rst_path = file_path.parent / f"{relative_path}.rst"
                if nested_rst_path.exists():
                    nested_files = parse_toctree(nested_rst_path)
                    toctree_files.extend(nested_files)
            else:
                toctree_active = False

    return toctree_files


def concatenate_files(file_list: List[Path], output_file, base_dir=Path('build/markdown')):
    with open(output_file, 'w') as outfile:
        for file in file_list:
            infile = (base_dir / file).read_text()
            outfile.write(infile)
            outfile.write("\n\n")  # Add a newline between files for clarity


def main():
    # Assuming the script is run from the root of the Sphinx project
    rst_file = Path('source/index.rst')
    output_file = Path('build/markdown/combined_document.md')

    toctree_files = parse_toctree(rst_file)
    concatenate_files(toctree_files, output_file)
    print(f"Combined markdown file created at: {output_file}")


if __name__ == "__main__":
    main()
