"""
docutils XML to markdown translator.
"""
import os
import posixpath
import re
from textwrap import dedent
from typing import List, Dict, Union, TYPE_CHECKING

from docutils import languages, nodes
from sphinx.util.docutils import SphinxTranslator

from sphinx_markdown_builder.contexts import (
    WrappedContext,
    IndentContext,
    SubContext,
    TableContext,
    UniqueString,
    CommaSeparatedContext,
)

if TYPE_CHECKING:
    from sphinx_markdown_builder import MarkdownBuilder

# Characters that should be escaped in Markdown:
# ----------------------------------------------
# Emphasis chars: * and _
#   Emphasis char prefix/postfix should have a non-space char to its right/left.
#   _ prefix/postfix must have a space char to its left/right (or beginning/end of the text).
#   We cannot make the destination between prefix/postfix in regular expression, so we will enforce both for all.
# Quote/Title: > and #
#   Should only precede by space chars in the line.
# Block char: `
#   One ` only requires not to have double line break in between
#   Double `` seems to be ignored
#   Three ``` must be at the beginning of the line
# Title: ----
#   A line that only have - or =
#   No spaces between them
# Horizontal line: ----
#   A line that only have 3 consecutive -, _, or * or more.
#   Precedes an empty line or beginng of text.
# Links: [text](link)
# Images: ![alt](link)
# Lists: +, -, *, 1.
# Tables: |
# Anything starting with 4 spaces is considered a block.
#   Should add force spaces (\ ) to avoid it.
# Escape char: \
#   Should be followed by:
#   Character Name
#   \         backslash
#   `         backtick (see also escaping backticks in code)
#   *         asterisk
#   _         underscore
#   { }       curly braces
#   [ ]       brackets
#   < >       angle brackets
#   ( )       parentheses
#   #         pound sign
#   +         plus sign
#   -         minus sign (hyphen)
#   .         dot
#   !         exclamation mark
#   |         pipe (see also escaping pipe in tables)
ESCAPE_RE = re.compile(r"([\\*`]|(?:^|(?<=\s|_))_)", re.M)

DOC_SECTION_ORDER = "head", "body", "foot"

VISIT_DEPART_PATTERN = re.compile("(visit|depart)_(.+)")


def escape_chars(txt: str):
    # Escape (some) characters with special meaning for Markdown
    return ESCAPE_RE.sub(r"\\\1", txt)


SKIP = UniqueString("skip")

PREDEFINED_ELEMENTS = dict(  # pylint: disable=use-dict-literal
    # Doctree elements for which Markdown element is <prefix><content><suffix>
    emphasis=(WrappedContext, "*"),  # _ is more restrictive
    strong=(WrappedContext, "**"),  # _ is more restrictive
    subscript=(WrappedContext, "<sub>", "</sub>"),
    superscript=(WrappedContext, "<sup>", "</sup>"),
    desc_annotation=(WrappedContext, "*"),  # _ is more restrictive
    field_name=(WrappedContext, "**"),  # e.g 'returns', 'parameters'
    literal_strong=(WrappedContext, "**"),
    literal_emphasis=(WrappedContext, "*"),
    # Doctree elements to skip subtree
    autosummary_toc=SKIP,
    nbplot_epilogue=SKIP,
    nbplot_not_rendered=SKIP,
    nbplot_container=SKIP,
    code_links=SKIP,
    index=SKIP,
    substitution_definition=SKIP,  # the doctree already contains the text with substitutions applied.
    runrole_reference=SKIP,
    # Doctree elements to ignore
    document=None,
    container=None,
    inline=None,
    definition_list=None,
    definition_list_item=None,
    term=None,
    field_list_item=None,
    mpl_hint=None,
    pending_xref=None,
    compound=None,
    line=None,
    line_block=None,
    desc_addname=None,  # module pre-roll for class/method
    desc_content=None,  # the description of the class/method
    desc_name=None,  # name of the class/method
    title_reference=None,
    autosummary_table=None,  # Sphinx autosummary
    # See https://www.sphinx-doc.org/en/master/usage/extensions/autosummary.html.
    # Ignored table elements
    raw=None,
    tabular_col_spec=None,
    colspec=None,
    tgroup=None,
)


class MarkdownTranslator(SphinxTranslator):  # pylint: disable=too-many-instance-attributes,too-many-public-methods
    def __init__(self, document: nodes.document, builder: "MarkdownBuilder"):
        super().__init__(document, builder)
        self.builder: "MarkdownBuilder" = builder
        self.language = languages.get_language(self.settings.language_code, document.reporter)
        # Warn only once per writer about unsupported elements
        self._warned = set()
        # Lookup table to get section list from name (default is ordered dict)
        # FIFO Sub context allow us to handle unique cases when post-processing is required.
        self._sections: Dict[str, List[SubContext]] = dict.fromkeys(DOC_SECTION_ORDER, None)

        # Current section heading level during writing
        self.section_level = 0

        # Flag indicating we are processing docinfo items
        self._in_docinfo = False

        # Flag for whether to escape characters
        self._escape_text = True

        self.list_context: List[Union[str, int]] = []

        # Saves the current descriptor type
        self.desc_context: List[str] = []

        # Reset attributes modified by reading
        self.reset()

    def reset(self):
        """Initialize object for fresh read."""
        for k in DOC_SECTION_ORDER:
            self._sections[k] = [SubContext()]

        self.section_level = 0
        self._in_docinfo = False
        self._escape_text = True
        self.list_context = []
        self.desc_context = []

    def ctx(self, section="body") -> SubContext:
        return self._sections[section][-1]

    def astext(self):
        """Return the final formatted document as a string."""
        for section in self._sections:
            self._pop_context(count=2**31, section=section)

        parts = (self.ctx(section).make().strip() for section in DOC_SECTION_ORDER)
        return "\n\n".join(parts).strip() + "\n"

    def add(self, value: str, section="body"):
        """
        Add `value` to `section`.

        Parameters
        ----------
        value : str
            String to add to output document
        section : {'body', 'head', 'foot'}, optional
            Section of document that generated text should be appended to.
        """
        self.ctx(section).add(value)

    def ensure_eol(self, count=1, section="body"):
        """Ensure the last line in current base is terminated by X new lines."""
        self.ctx(section).ensure_eol(count)

    def _push_context(self, ctx: SubContext, section="body"):
        self._sections[section].append(ctx)

    def _pop_context(self, _node=None, count=1, section="body"):
        for _ in range(count):
            if len(self._sections[section]) <= 1:
                break
            content = self._sections[section].pop().make()
            self.add(content)

    def _start_level(self, prefix: str):
        """Create a new IndentLevel with `prefix` and `first_prefix`"""
        self._push_context(IndentContext(prefix))

    _finish_level = _pop_context

    def _pass(self, _node=None):
        pass

    def _skip(self, _node=None):
        raise nodes.SkipNode

    def _has_attr(self, item):
        try:
            super().__getattribute__(item)
            return True
        except AttributeError:
            return False

    def __getattribute__(self, item):
        # First try to get an existing attribute
        try:
            return super().__getattribute__(item)
        except AttributeError as ex:
            exp = ex

        match = VISIT_DEPART_PATTERN.fullmatch(item)
        if match is None:
            raise exp

        state, element = match.groups()
        if element in PREDEFINED_ELEMENTS:
            action = PREDEFINED_ELEMENTS[element]
            if action is None:
                return self._pass
            if action is SKIP:
                return self._skip
            if isinstance(action, (list, tuple)) and isinstance(action[0], type) and issubclass(action[0], SubContext):
                if state == "visit":
                    sub_context, *args = action
                    return lambda _node: self._push_context(sub_context(*args))
                return self._pop_context

        # If one of the handlers is defined, automatically add the other
        if self._has_attr(f"visit_{element}") or self._has_attr(f"depart_{element}"):
            return self._pass

        raise exp

    ################################################################################
    # visit/depart handlers
    ################################################################################

    def visit_warning(self, _node):
        """Sphinx warning directive."""
        self.add("**WARNING**: ")

    def visit_note(self, _node):
        """Sphinx note directive."""
        self.add("**NOTE**: ")

    def visit_seealso(self, _node):
        self.add("**SEE ALSO**: ")

    def visit_attention(self, _node):
        self.add("**ATTENTION**: ")

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

    # noinspection PyPep8Naming
    def visit_Text(self, node):  # pylint: disable=invalid-name
        text = node.astext().replace("\r", "")
        if self._escape_text:
            text = escape_chars(text)
        self.add(text)

    def visit_comment(self, _node):
        self.ensure_eol()
        self._escape_text = False
        self._push_context(WrappedContext("<!-- ", " -->"))

    def depart_comment(self, _node):
        self._pop_context()
        self._escape_text = True

    def visit_paragraph(self, _node):
        self.ensure_eol(2)

    depart_paragraph = visit_paragraph
    visit_compact_paragraph = visit_paragraph
    depart_compact_paragraph = depart_paragraph

    def visit_docinfo(self, _node):
        self._in_docinfo = True

    def depart_docinfo(self, _node):
        self._in_docinfo = False

    def _process_docinfo_item(self, node):
        """Called explicitly from methods in this class."""
        self.ensure_eol(1, section="head")
        self.add(f"% {node.astext()}\n", section="head")
        raise nodes.SkipNode

    def visit_definition(self, _node):
        self.ensure_eol(2)
        self._start_level("    ")

    depart_definition = _finish_level

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
        self.ensure_eol()
        self.add("```python")
        self.ensure_eol()

    depart_doctest_block = depart_literal_block

    def visit_block_quote(self, _node):
        self.ensure_eol()
        self._start_level("> ")

    depart_block_quote = _finish_level

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

    def visit_section(self, node):
        if self.config.markdown_anchor_sections:
            for anchor in node.get("ids", []):
                self._add_anchor(anchor)

        self.section_level += 1
        self.ensure_eol(2)

    def depart_section(self, _node):
        self.section_level -= 1

    def visit_title(self, _node):
        self.ensure_eol(2)
        self.add((self.section_level * "#") + " ")

    def depart_title(self, _node):
        self.ensure_eol(2)

    def visit_subtitle(self, _node):
        self.ensure_eol(2)
        self.add((self.section_level + 2) * "#" + " ")

    depart_subtitle = depart_title

    def visit_rubric(self, _node):
        """Sphinx Rubric, a heading without relation to the document sectioning
        https://docutils.sourceforge.net/docs/ref/rst/directives.html#rubric."""
        self.ensure_eol(2)
        self.add("### ")

    depart_rubric = depart_title

    def visit_transition(self, _node):
        # Simply replace a transition by a horizontal rule.
        # Could use three or more '*', '_' or '-'.
        self.ensure_eol(2)
        self.add("---")
        self.ensure_eol(1)
        raise nodes.SkipNode

    def _adjust_url(self, url: str):
        """Replace `refuri` in reference with HTTP address, if possible"""
        if not self.config.markdown_http_base:
            return url

        # If HTTP page build URL known, make link relative to that.
        this_doc = self.builder.current_doc_name
        if url == "":  # Reference to this doc
            url = self.builder.get_target_uri(this_doc)
        else:  # URL is relative to the current docname.
            this_dir = posixpath.dirname(this_doc)
            if this_dir:
                url = posixpath.normpath(f"{this_dir}/{url}")
        return f"{self.config.markdown_http_base}/{url}"

    def _fetch_ref_uri(self, node):
        uri = node.get("refuri", "")

        # Do not modify external URL in any way
        if not node.get("internal", False):
            return uri

        uri = self._adjust_url(uri)

        # Whatever the URL is, add the anchor to it
        ref_id = node.get("refid", None)
        if ref_id is not None:
            uri = f"#{ref_id}"

        return uri

    def visit_reference(self, node):
        url = self._fetch_ref_uri(node)
        self._push_context(WrappedContext("[", f"]({url})"))

    depart_reference = _pop_context

    def visit_download_reference(self, node):
        filename = self._adjust_url(node.get("filename", ""))
        self._push_context(WrappedContext("[", f"]({filename})"))

    depart_download_reference = _pop_context

    def _add_anchor(self, anchor: str):
        self._escape_text = False
        self.ensure_eol()
        self.add(f'<a id="{anchor}"></a>')
        self.ensure_eol()
        self._escape_text = True

    def visit_target(self, node):
        ref_id = node.get("refid", None)
        if ref_id is None:
            return
        self._add_anchor(ref_id)

    def visit_only(self, node):
        if node["expr"] != "markdown":
            raise nodes.SkipNode
        self.add(dedent(node.astext()))
        self.ensure_eol()

    def unknown_visit(self, node):
        """Warn once per instance for unsupported nodes.
        Intercept docinfo items if in docinfo block.
        """
        if self._in_docinfo:
            self._process_docinfo_item(node)
            return
        # We really don't know this node type, warn once per node type
        node_type = node.__class__.__name__
        if node_type not in self._warned:
            self.document.reporter.warning("The " + node_type + " element not yet supported in Markdown.")
            self._warned.add(node_type)
        raise nodes.SkipNode

    ################################################################################
    # desc
    ################################################################################
    # desc (desctype: {function, class, method, etc.)
    #   desc_signature
    #     desc_name
    #       desc_annotation (optional)
    #     desc_parameterlist
    #       desc_parameter
    #   desc_content
    #     field_list
    #       field
    #         field_name (e.g 'returns/parameters/raises')
    #         field_body
    ################################################################################

    def visit_desc(self, node):
        self.desc_context.append(node.attributes.get("desctype", ""))

    def depart_desc(self, _node):
        self.desc_context.pop()

    def visit_desc_signature(self, node):
        """the main signature of class/method"""

        # Insert anchors if enabled by the config
        if self.config.markdown_anchor_signatures:
            for anchor in node.get("ids", []):
                self._add_anchor(anchor)

        # We don't want methods to be at the same level as classes,
        # If signature has a non-null class, that's means it is a signature
        # of a class method
        self.ensure_eol()
        if node.attributes.get("class", None):
            self.add("#### ")
        else:
            self.add("### ")

    def visit_desc_parameterlist(self, _node):
        self._push_context(WrappedContext("(", ")", wrap_empty=True))
        self._push_context(CommaSeparatedContext(", "))

    def depart_desc_parameterlist(self, _node):
        self._pop_context(count=2)

    def depart_desc_signature(self, _node):
        """the main signature of class/method"""
        self.ensure_eol()

    def sep_ctx(self, section="body") -> CommaSeparatedContext:
        ctx = self.ctx(section)
        assert isinstance(ctx, CommaSeparatedContext)
        return ctx

    def visit_desc_parameter(self, _node):
        """single method/class ctr param"""
        self.sep_ctx().enter_parameter()

    def depart_desc_parameter(self, _node):
        self.sep_ctx().exit_parameter()

    def visit_field_list(self, _node):
        self._start_list("*")

    def depart_field_list(self, _node):
        self._end_list()

    def visit_field(self, _node):
        self._start_list_item()

    def depart_field(self, _node):
        self._end_list_item()

    def visit_field_body(self, _node):
        self.ensure_eol(1)
        self._push_context(SubContext())

    def depart_field_body(self, _node):
        self._pop_context()
        self.ensure_eol(1)

    def visit_versionmodified(self, node):
        """
        Node for version change entries.
        Currently used for “versionadded”, “versionchanged” and “deprecated” directives.
        Type will hold something like 'deprecated'
        """
        node_type = node.attributes["type"].capitalize()
        self.ensure_eol(1)
        self.add(f"**{node_type}:** ")
        self.ensure_eol(1)
        self._push_context(SubContext())

    def depart_versionmodified(self, _node):
        self._pop_context()
        self.ensure_eol(1)

    ################################################################################
    # tables
    ################################################################################
    # table
    #   tgroup [cols=x]
    #     colspec
    #     thead
    #       row
    #         entry
    #           paragraph (optional)
    #     tbody
    #       row
    #         entry
    #           paragraph (optional)
    ###############################################################################

    def table_ctx(self, section="body") -> TableContext:
        ctx = self.ctx(section)
        assert isinstance(ctx, TableContext)
        return ctx

    def visit_table(self, _node):
        self._push_context(TableContext())

    depart_table = _pop_context

    def visit_thead(self, _node):
        self.table_ctx().enter_head()

    def depart_thead(self, _node):
        self.table_ctx().exit_head()

    def visit_tbody(self, _node):
        self.table_ctx().enter_body()

    def depart_tbody(self, _node):
        self.table_ctx().exit_body()

    def visit_row(self, _node):
        self.table_ctx().enter_row()

    def depart_row(self, _node):
        self.table_ctx().exit_row()

    def visit_entry(self, _node):
        self.table_ctx().enter_entry()

    def depart_entry(self, _node):
        self.table_ctx().exit_entry()

    ################################################################################
    # lists
    ################################################################################
    # enumerated_list/bullet_list
    #     list_item
    #       paragraph (optional)
    ###############################################################################

    def _start_list(self, marker: Union[int, str]):
        self.ensure_eol()
        if isinstance(marker, str) and marker[-1] != " ":
            marker += " "
        self.list_context.append(marker)

    def _end_list(self):
        self.list_context.pop()
        # We need two line breaks to make sure the next paragraph will not merge into the list
        self.ensure_eol(2)

    def _start_list_item(self):
        marker = self.list_context[-1]
        if isinstance(marker, int):
            marker = f"{marker}. "
            self.list_context[-1] += 1
        # Make sure the list item prefix starts at a new line
        self.ensure_eol()
        self._push_context(IndentContext(marker, only_first=True))

    def _end_list_item(self):
        self._pop_context()
        # Make sure the list item ends with a new line
        self.ensure_eol()

    def visit_enumerated_list(self, _node):
        self._start_list(1)

    def depart_enumerated_list(self, _node):
        self._end_list()

    def visit_bullet_list(self, node):
        self._start_list(node.attributes.get("bullet", "*"))

    depart_bullet_list = depart_enumerated_list

    def visit_list_item(self, _node):
        self._start_list_item()

    def depart_list_item(self, _node):
        self._end_list_item()
