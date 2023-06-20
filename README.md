# sphinx-markdown-builder

Sphinx builder that generates markdown files from reStructuredText.

## Installation

```sh
pip3 install git+https://github.com/liran-funaro/sphinx-markdown-builder@main
```


## Usage

Add the extension to your `conf.py` file:
```python
extensions = [
    ...,
    "sphinx_markdown_builder",
    ...,
]
```

Build markdown files with `sphinx-build` command
```sh
sphinx-build -M markdown ./docs ./build
```

## Configurations

You can add the following configurations to your `conf.py` file:

* `markdown_http_base`: If set, all references will link to this prefix address
* `markdown_uri_doc_suffix`: If set, all references will link to documents with this suffix.

For example, if your `conf.py` file have the following configuration:
```python
markdown_http_base = "https://your-domain.com/docs"
markdown_uri_doc_suffix = ".html"
```

Then a reference to `your-doc-name#your-header` will be subsituted with `https://your-domain.com/docs/your-doc-name.html#your-header`. 

## Credits

* Forked from [
sphinx-markdown-builder](https://github.com/clayrisser/sphinx-markdown-builder) by [Clay Risser](https://github.com/clayrisser) under the [MIT](https://github.com/clayrisser/sphinx-markdown-builder/blob/master/LICENSE) licence
* Original author: [Jam Risser](https://codejam.ninja) © 2018
* Original implementation was based on [doctree2md](https://github.com/matthew-brett/nb2plots/blob/master/nb2plots/doctree2md.py) by [Matthew Brett](https://github.com/matthew-brett) under the [BSD-2](https://github.com/matthew-brett/nb2plots/blob/main/LICENSE) licence

## License

[MIT](LICENSE)
