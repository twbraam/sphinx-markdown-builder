"""
Taken from: nb2plots/../doctree2.md.py
"""


def _make_method(to_add):
    """Make a method that adds `to_add`"""

    def method(self, _node):
        self.add(to_add)

    return method


def add_pref_suff(pref_suff_map):
    """Decorator adds visit, depart methods for prefix/suffix pairs."""

    def dec(cls):
        # Need _make_method to ensure new variable picked up for each iteration
        # of the loop.  The defined method picks up this new variable in its
        # scope.
        for key, (prefix, suffix) in pref_suff_map.items():
            setattr(cls, "visit_" + key, _make_method(prefix))
            setattr(cls, "depart_" + key, _make_method(suffix))
        return cls

    return dec


def add_pass_thru(pass_methods):
    """Decorator adds explicit pass-through visit and depart methods."""

    def meth(_self, _node):
        pass

    def dec(cls):
        for element_name in pass_methods:
            for method_prefix in ("visit_", "depart_"):
                method_name = method_prefix + element_name
                if hasattr(cls, method_name):
                    raise ValueError(f"method name {method_name} already defined")
                setattr(cls, method_name, meth)
        return cls

    return dec


# Doctree elements for which Markdown element is <prefix><content><suffix>
PREF_SUFF_ELEMENTS = {
    "emphasis": ("*", "*"),  # Could also use ('_', '_')
    "strong": ("**", "**"),  # Could also use ('__', '__')
    "subscript": ("<sub>", "</sub>"),
    "superscript": ("<sup>", "</sup>"),
}

# Doctree elements explicitly passed through without extra markup
PASS_THRU_ELEMENTS = (
    "document",
    "container",
    "target",
    "inline",
    "definition_list",
    "definition_list_item",
    "term",
    "field_list_item",
    "mpl_hint",
    "pending_xref",
    "compound",
    "line",
    "line_block",
    "desc_addname",  # module preroll for class/method
    "desc_content",  # the description of the class/method
    "desc_parameterlist",  # method/class ctor param list
)
