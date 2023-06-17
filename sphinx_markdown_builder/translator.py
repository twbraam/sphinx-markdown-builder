"""
docutils XML to markdown translator.
"""
import os
import posixpath
import re
from textwrap import dedent
from typing import List

from docutils import languages, nodes

from sphinx_markdown_builder.contexts import AnnotationContext, IndentContext, SubContext, TableContext, Depth
from sphinx_markdown_builder.decorators import PASS_THRU_ELEMENTS, PREF_SUFF_ELEMENTS, add_pass_thru, add_pref_suff

__docformat__ = "reStructuredText"

# Characters that should be escaped in Markdown
ESCAPE_RE = re.compile(r"([\\*`])")

DOC_SECTION_ORDER = "head", "body", "foot"


def escape_chars(txt: str):
    # Escape (some) characters with special meaning for Markdown
    return ESCAPE_RE.sub(r"\\\1", txt)


@add_pass_thru(PASS_THRU_ELEMENTS)
@add_pref_suff(PREF_SUFF_ELEMENTS)
class MarkdownTranslator(nodes.NodeVisitor):  # pylint: disable=too-many-instance-attributes,too-many-public-methods
    def __init__(self, document, builder=None):
        super().__init__(document)
        self.builder = builder
        self.settings = settings = document.settings
        lcode = settings.language_code
        self.language = languages.get_language(lcode, document.reporter)
        # Not-None here indicates Markdown should use HTTP for internal and download links.
        self.markdown_http_base = builder.config.markdown_http_base if builder else None
        # Warn only once per writer about unsupported elements
        self._warned = set()
        # Lookup table to get section list from name (default is ordered dict)
        self._sections = dict.fromkeys(DOC_SECTION_ORDER, None)

        # Current section heading level during writing
        self.section_level = 0

        # Flag indicating we are processing docinfo items
        self._in_docinfo = False

        # Flag for whether to escape characters
        self._escape_text = True

        self.depth = Depth()
        self.enumerated_count = {}
        # FIFO Sub context allow us to handle unique cases when post-processing is required.
        self.sub_contexts: List[SubContext] = []
        # Saves the current descriptor type
        self.desc_context: List[str] = []

        # Reset attributes modified by reading
        self.reset()

    def reset(self):
        """Initialize object for fresh read."""
        for k in self._sections:
            self._sections[k] = []

        self.section_level = 0
        self._in_docinfo = False
        self._escape_text = True

        self.depth = Depth()
        self.enumerated_count = {}
        self.sub_contexts: List[SubContext] = []
        self.desc_context: List[str] = []

    def astext(self):
        """Return the final formatted document as a string."""
        parts = ["".join(self._sections[section]).strip() for section in DOC_SECTION_ORDER]
        parts = [part + "\n\n" for part in parts if part]
        return "".join(parts).strip() + "\n"

    def _iter_content(self, section="body"):
        """We iterate over the content from the most recent context to the least"""
        for ctx in reversed(self.sub_contexts):
            yield ctx.content

        yield self._sections[section]

    def count_prev_eol(self, section="body"):
        line_break_count = 0
        for out_list in self._iter_content(section):
            for out in reversed(out_list):
                for char in reversed(out):
                    if char == "\n":
                        line_break_count += 1
                    else:
                        return line_break_count
        return line_break_count

    def ensure_eol(self, count=1, section="body"):
        """Ensure the last line in current base is terminated by X new lines."""
        missing_eol = count - self.count_prev_eol(section)
        if missing_eol > 0:
            self.add("\n" * missing_eol)

    def add(self, value, section="body"):
        """Add `string` to `section` or current output.

        Parameters
        ----------
        value : str
            String to add to output document
        section : {'body', 'head', 'foot'}, optional
            Section of document that generated text should be appended to, if
            not already appending to an indent level.  If already appending to
            an indent level, method will ignore `section`.  Use
            :meth:`add_section` to append to a section unconditionally.
        """
        if len(self.sub_contexts) > 0:
            self.sub_contexts[-1].add(value)
        else:
            self._sections[section].append(value)

    def add_section(self, value: str, section="body"):
        """Add `string` to `section` regardless of current output.

        Can be useful when forcing write to header or footer.

        Parameters
        ----------
        value : str
            String to add to output document
        section : {'body', 'head', 'foot'}, optional
            Section of document that generated text should be appended to.
        """
        self._sections[section].append(value)

    def add_context(self, ctx: SubContext):
        self.sub_contexts.append(ctx)

    def pop_context(self, _node):
        content = self.sub_contexts.pop().make()
        self.add(content)

    def start_level(self, prefix, first_prefix=None):
        """Create a new IndentLevel with `prefix` and `first_prefix`"""
        self.add_context(IndentContext(prefix, first_prefix))

    finish_level = pop_context

    @property
    def ctx(self) -> SubContext:
        if len(self.sub_contexts) == 0:
            raise nodes.SkipNode
        return self.sub_contexts[-1]

    ################################################################################
    # visit/depart handlers
    ################################################################################

    def visit_autosummary_toc(self, _node):
        raise nodes.SkipNode

    def depart_autosummary_toc(self, _node):
        raise nodes.SkipNode

    def visit_title(self, _node):
        self.ensure_eol(2)
        self.add((self.section_level * "#") + " ")

    def visit_desc(self, node):
        self.desc_context.append(node.attributes.get("desctype", ""))

    def depart_desc(self, _node):
        self.desc_context.pop()

    def visit_desc_annotation(self, _node):
        # annotation, e.g 'method', 'class', or a signature
        self.add_context(AnnotationContext())

    depart_desc_annotation = pop_context

    def visit_desc_name(self, node):
        # name of the class/method
        # Escape "__" which is a formatting string for markdown
        if node.rawsource.startswith("__"):
            self.add("\\")

    def depart_desc_name(self, _node):
        if self.desc_context[-1] in ("function", "method", "class"):
            self.add("(")

    def visit_desc_signature(self, node):
        # the main signature of class/method

        # Insert anchors if enabled by the builder
        if self.builder.insert_anchors_for_signatures:
            for sig_id in node.get("ids", ()):
                self.add(f'<a name="{sig_id}"></a>')

        # We don't want methods to be at the same level as classes,
        # If signature has a non-null class, that's means it is a signature
        # of a class method
        self.ensure_eol()
        if "class" in node.attributes and node.attributes["class"]:
            self.add("#### ")
        else:
            self.add("### ")

    def depart_desc_signature(self, _node):
        # the main signature of class/method
        if self.desc_context[-1] in ("function", "method", "class"):
            self.add(")")
        self.ensure_eol()

    def visit_desc_parameter(self, node):
        # single method/class ctr param
        pass

    def depart_desc_parameter(self, node):
        # single method/class ctr param
        # if there are additional params, include a comma
        if node.next_node(descend=False, siblings=True):
            self.add(", ")

    # list of parameters/return values/exceptions
    #
    # field_list
    #   field
    #       field_name (e.g 'returns/parameters/raises')
    #

    def visit_field_list(self, _node):
        self.ensure_eol(2)

    def depart_field_list(self, _node):
        self.ensure_eol(2)

    def visit_field(self, _node):
        self.ensure_eol(2)

    def depart_field(self, _node):
        self.ensure_eol(1)

    def visit_field_name(self, _node):
        # field name, e.g 'returns', 'parameters'
        self.add("* **")

    def depart_field_name(self, _node):
        self.add("**")

    def visit_field_body(self, _node):
        self.ensure_eol(1)
        self.start_level("    ")

    depart_field_body = finish_level

    def visit_literal_strong(self, _node):
        self.add("**")

    def depart_literal_strong(self, _node):
        self.add("**")

    def visit_literal_emphasis(self, _node):
        self.add("*")

    def depart_literal_emphasis(self, _node):
        self.add("*")

    def visit_title_reference(self, node):
        pass

    def depart_title_reference(self, node):
        pass

    def visit_versionmodified(self, node):
        """
        deprecation and compatibility messages
        type will hold something like 'deprecated'
        """
        node_type = node.attributes["type"].capitalize()
        self.add(f"**{node_type}:** ")

    def depart_versionmodified(self, node):
        """deprecation and compatibility messages"""

    def visit_warning(self, _node):
        """Sphinx warning directive."""
        self.add("**WARNING**: ")

    def depart_warning(self, node):
        """Sphinx warning directive."""

    def visit_note(self, _node):
        """Sphinx note directive."""
        self.add("**NOTE**: ")

    def depart_note(self, node):
        """Sphinx note directive."""

    def visit_seealso(self, _node):
        self.add("**SEE ALSO**: ")

    def depart_seealso(self, _node):
        pass

    def visit_attention(self, _node):
        self.add("**ATTENTION**: ")

    def depart_attention(self, _node):
        pass

    def visit_rubric(self, _node):
        """Sphinx Rubric, a heading without relation to the document sectioning
        https://docutils.sourceforge.net/docs/ref/rst/directives.html#rubric."""
        self.ensure_eol(2)
        self.add("### ")

    def depart_rubric(self, _node):
        """Sphinx Rubric, a heading without relation to the document sectioning
        https://docutils.sourceforge.net/docs/ref/rst/directives.html#rubric."""
        self.ensure_eol(2)

    def visit_image(self, node):
        """Image directive."""
        uri = node.attributes["uri"]
        doc_folder = os.path.dirname(self.builder.current_doc_name)
        if uri.startswith(doc_folder):
            # drop docname prefix
            doc_folder_len = len(doc_folder)
            uri = uri[doc_folder_len:]
            if uri.startswith("/"):
                uri = "." + uri

        alt = node.attributes.get("alt", "image")
        # We don't need to add EOL before/after the image.
        # It will be handled by the visit/depart handlers of the paragraph.
        self.add(f"![{alt}]({uri})")

    def depart_image(self, node):
        """Image directive."""

    def visit_autosummary_table(self, node):
        """Sphinx autosummary See https://www.sphinx-doc.org/en/master/usage/extensions/autosummary.html."""

    def depart_autosummary_table(self, node):
        """Sphinx autosummary See https://www.sphinx-doc.org/en/master/usage/extensions/autosummary.html."""

    ################################################################################
    # tables
    #
    # docutils.nodes.table
    #     docutils.nodes.tgroup [cols=x]
    #       docutils.nodes.colspec
    #
    #       docutils.nodes.thead
    #         docutils.nodes.row
    #         docutils.nodes.entry
    #         docutils.nodes.entry
    #         docutils.nodes.entry
    #
    #       docutils.nodes.tbody
    #         docutils.nodes.row
    #         docutils.nodes.entry

    def visit_raw(self, _node):
        self.depth.descend("raw")

    def depart_raw(self, _node):
        self.depth.ascend("raw")

    def visit_tabular_col_spec(self, node):
        pass

    def depart_tabular_col_spec(self, node):
        pass

    def visit_colspec(self, node):
        pass

    def depart_colspec(self, node):
        pass

    def visit_tgroup(self, _node):
        self.depth.descend("tgroup")

    def depart_tgroup(self, _node):
        self.depth.ascend("tgroup")

    @property
    def table_ctx(self) -> TableContext:
        ctx = self.ctx
        assert isinstance(ctx, TableContext)
        return ctx

    def visit_table(self, _node):
        self.add_context(TableContext())

    depart_table = pop_context

    def visit_thead(self, _node):
        self.table_ctx.enter_head()

    def depart_thead(self, _node):
        self.table_ctx.exit_head()

    def visit_tbody(self, _node):
        self.table_ctx.enter_body()

    def depart_tbody(self, _node):
        self.table_ctx.exit_body()

    def visit_row(self, _node):
        self.table_ctx.enter_row()

    def depart_row(self, _node):
        self.table_ctx.exit_row()

    def visit_entry(self, _node):
        self.table_ctx.enter_entry()

    def depart_entry(self, _node):
        self.table_ctx.exit_entry()

    def visit_enumerated_list(self, _node):
        self.depth.descend("list")
        self.depth.descend("enumerated_list")

    def depart_enumerated_list(self, _node):
        self.enumerated_count[self.depth.get("list")] = 0
        self.depth.ascend("enumerated_list")
        self.depth.ascend("list")

    def visit_bullet_list(self, _node):
        self.depth.descend("list")
        self.depth.descend("bullet_list")

    def depart_bullet_list(self, _node):
        self.depth.ascend("bullet_list")
        self.depth.ascend("list")

    def visit_list_item(self, node):
        self.depth.descend("list_item")
        depth = self.depth.get("list")
        depth_padding = "    " * (depth - 1)
        marker = "*"
        if node.parent.tagname == "enumerated_list":
            if depth not in self.enumerated_count:
                self.enumerated_count[depth] = 1
            else:
                self.enumerated_count[depth] = self.enumerated_count[depth] + 1
            marker = str(self.enumerated_count[depth]) + "."
        # Make sure the list item prefix starts at a new line
        self.ensure_eol()
        self.add(depth_padding + marker + " ")

    def depart_list_item(self, _node):
        self.depth.ascend("list_item")
        # Make sure the list item ends with a new line
        self.ensure_eol()

    ##########################################################################
    # doctree2md
    ##########################################################################

    # noinspection PyPep8Naming
    def visit_Text(self, node):  # pylint: disable=invalid-name
        text = node.astext().replace("\r", "")
        if self._escape_text:
            text = escape_chars(text)
        self.add(text)

    # noinspection PyPep8Naming
    def depart_Text(self, node):  # pylint: disable=invalid-name
        pass

    def visit_comment(self, node):
        txt = node.astext()
        if txt.strip():
            self.add(f"<!-- {txt} -->\n")
        raise nodes.SkipNode

    def visit_docinfo(self, _node):
        self._in_docinfo = True

    def depart_docinfo(self, _node):
        self._in_docinfo = False

    def process_docinfo_item(self, node):
        """Called explicitly from methods in this class."""
        self.add_section(f"% {node.astext()}\n", section="head")
        raise nodes.SkipNode

    def visit_definition(self, _node):
        self.ensure_eol(2)
        self.start_level("    ")

    depart_definition = finish_level

    @classmethod
    def is_paragraph_requires_eol(cls, node):
        """
        - entry (table)
          ==> No new line
        - list_item/field_name/field_body
          ==> New line is handled at its visit/depart handlers
        """
        return not isinstance(
            node.parent,
            (nodes.entry, nodes.list_item, nodes.field_name, nodes.field_body),
        )

    def visit_paragraph(self, node):
        if self.is_paragraph_requires_eol(node):
            self.ensure_eol(2)

    depart_paragraph = visit_paragraph

    def visit_math_block(self, _node):
        # docutils math block
        self._escape_text = False
        self.ensure_eol()
        self.add("$$")
        self.ensure_eol()

    def depart_math_block(self, _node):
        self._escape_text = True
        self.ensure_eol()
        self.add("$$")
        self.ensure_eol(2)

    def visit_displaymath(self, node):
        """sphinx math blocks become displaymath"""
        self.ensure_eol()
        latex = node["latex"]
        self.add(f"$$\n{latex}\n$$")
        self.ensure_eol(2)
        raise nodes.SkipNode

    def visit_math(self, node):
        """sphinx math node has 'latex' attribute, docutils does not"""
        if "latex" in node:  # sphinx math node
            latex = node["latex"]
            self.add(f"${latex}$")
            raise nodes.SkipNode
        # docutils math node
        self._escape_text = False
        self.add("$")

    def depart_math(self, _node):
        # sphinx node skipped in visit, only docutils gets here
        self._escape_text = True
        self.add("$")

    def visit_literal(self, _node):
        self._escape_text = False
        self.add("`")

    def depart_literal(self, _node):
        self.add("`")
        self._escape_text = True

    def visit_literal_block(self, node):
        self._escape_text = False
        code_type = node["classes"][1] if "code" in node["classes"] else ""
        if "language" in node:
            code_type = node["language"]
        self.ensure_eol()
        self.add("```" + code_type)
        self.ensure_eol()

    def depart_literal_block(self, _node):
        self._escape_text = True
        self.ensure_eol()
        self.add("```")
        self.ensure_eol(2)

    def visit_doctest_block(self, _node):
        self._escape_text = False
        self.ensure_eol(1)
        self.add("```python")
        self.ensure_eol(1)

    depart_doctest_block = depart_literal_block

    def visit_block_quote(self, _node):
        self.start_level("> ")

    depart_block_quote = finish_level

    def visit_section(self, _node):
        self.section_level += 1
        self.ensure_eol(2)

    def depart_section(self, _node):
        self.section_level -= 1

    def visit_problematic(self, node):
        self.ensure_eol(2)
        self.add(f"```\n{node.astext()}\n```")
        self.ensure_eol(2)
        raise nodes.SkipNode

    def visit_system_message(self, node):
        if node["level"] < self.document.reporter.report_level:
            # Level is too low to display
            raise nodes.SkipNode
        line = node["line"] if node.hasattr("line") else ""
        line = f", line {line}"
        source = node["source"]
        self.ensure_eol(2)
        self.add(f"```System Message: {source}:{line}\n\n{node.astext()}\n```")
        self.ensure_eol(2)
        raise nodes.SkipNode

    def depart_title(self, _node):
        self.ensure_eol(2)

    def visit_subtitle(self, _node):
        self.ensure_eol(2)
        self.add((self.section_level + 2) * "#" + " ")

    depart_subtitle = depart_title

    def visit_transition(self, _node):
        # Simply replace a transition by a horizontal rule.
        # Could use three or more '*', '_' or '-'.
        self.ensure_eol()
        self.add("---")
        self.ensure_eol(2)
        raise nodes.SkipNode

    def _refuri2http(self, node):
        # Replace 'refuri' in reference with HTTP address, if possible
        # None for no possible address
        url = node.get("refuri") or ""

        # Do not modify external URL in any way
        if not node.get("internal"):
            return url

        # If HTTP page build URL known, make link relative to that.
        if self.markdown_http_base:
            this_doc = self.builder.current_doc_name
            if url == "":  # Reference to this doc
                url = self.builder.get_target_uri(this_doc)
            else:  # URL is relative to the current docname.
                this_dir = posixpath.dirname(this_doc)
                if this_dir:
                    url = posixpath.normpath(f"{this_dir}/{url}")
            url = f"{self.markdown_http_base}/{url}"

        # Whatever the URL is, add the anchor to it
        if "refid" in node:
            url += "#" + node["refid"]

        return url

    def visit_reference(self, node):
        # If no target possible, pass through.
        url = self._refuri2http(node)
        if url is None:
            return
        self.add("[")
        for child in node.children:
            child.walkabout(self)
        self.add(f"]({url})")
        raise nodes.SkipNode

    def depart_reference(self, node):
        pass

    def visit_nbplot_epilogue(self, node):
        raise nodes.SkipNode

    def visit_nbplot_not_rendered(self, node):
        raise nodes.SkipNode

    def visit_code_links(self, node):
        raise nodes.SkipNode

    def visit_index(self, node):
        # Drop index entries
        raise nodes.SkipNode

    def visit_substitution_definition(self, node):
        # Drop substitution definitions - the doctree already contains the text
        # with substitutions applied.
        raise nodes.SkipNode

    def visit_only(self, node):
        if node["expr"] == "markdown":
            self.add(dedent(node.astext()))
            self.ensure_eol()
        raise nodes.SkipNode

    def visit_runrole_reference(self, node):
        raise nodes.SkipNode

    def visit_download_reference(self, node):
        # If not resolving internal links, or there is no filename specified,
        # pass through.
        filename = node.get("filename")
        if None in (self.markdown_http_base, filename):
            return
        target_url = f"{self.markdown_http_base}/_downloads/{filename}"
        self.add(f"[{node.astext()}]({target_url})")
        raise nodes.SkipNode

    def depart_download_reference(self, node):
        pass

    visit_compact_paragraph = visit_paragraph

    depart_compact_paragraph = depart_paragraph

    def visit_nbplot_container(self, node):
        pass

    def depart_nbplot_container(self, node):
        pass

    def unknown_visit(self, node):
        """Warn once per instance for unsupported nodes.

        Intercept docinfo items if in docinfo block.
        """
        if self._in_docinfo:
            self.process_docinfo_item(node)
            return
        # We really don't know this node type, warn once per node type
        node_type = node.__class__.__name__
        if node_type not in self._warned:
            self.document.reporter.warning("The " + node_type + " element not yet supported in Markdown.")
            self._warned.add(node_type)
        raise nodes.SkipNode
