"""
Context handlers.
"""
from tabulate import tabulate


class SubContext:
    def __init__(self, node):
        self.node = node
        self.body = []

    def add(self, value: str):
        self.body.append(value)

    def make(self):
        return "".join(self.body)


class AnnotationContext(SubContext):
    def make(self):
        content = super().make()
        # We want to make the text italic. We need to make sure the _ mark is near a non-space char,
        # but we want to preserve the existing spaces.
        prefix_spaces = len(content) - len(content.lstrip())
        suffix_spaces = len(content) - len(content.rstrip())
        annotation_mark = "_"
        content = (
            f"{annotation_mark:>{prefix_spaces + 1}}"
            f"{content[prefix_spaces:len(content) - suffix_spaces]}"
            f"{annotation_mark:<{suffix_spaces + 1}}"
        )
        return content


class TableContext(SubContext):
    def __init__(self, node):
        super().__init__(node)
        self.headers = []

        self.is_head = False
        self.is_body = False
        self.is_row = False
        self.is_entry = False

    @property
    def active_output(self):
        if self.is_head:
            return self.headers

        assert self.is_body
        return self.body

    def enter_head(self):
        assert not self.is_body
        self.is_head = True

    def exit_head(self):
        assert self.is_head
        self.is_head = False

    def enter_body(self):
        assert not self.is_head
        self.is_body = True

    def exit_body(self):
        assert self.is_body
        self.is_body = False

    def enter_row(self):
        assert self.is_head or self.is_body
        self.is_row = True
        self.active_output.append([])

    def exit_row(self):
        assert self.is_row
        self.is_row = False

    def enter_entry(self):
        assert self.is_row
        self.is_entry = True
        self.active_output[-1].append([])

    def exit_entry(self):
        assert self.is_entry
        self.is_entry = False

    def add(self, value: str):
        assert self.is_entry
        self.active_output[-1][-1].append(value)

    @staticmethod
    def make_row(row):
        return ["".join(entries) for entries in row]

    def make(self):
        if len(self.headers) == 0 and len(self.body) == 0:
            return ""

        if len(self.headers) == 0:
            headers = [""]
        else:
            assert len(self.headers) == 1
            headers = self.make_row(self.headers[0])

        body = list(map(self.make_row, self.body))
        return tabulate(body, headers=headers, tablefmt="github")


class IndentLevel:
    """Class to hold text being written for a certain indentation level.

    For example, all text in list_elements need to be indented.  A list_element
    creates one of these indentation levels, and all text contained in the
    list_element gets written to this IndentLevel.  When we leave the
    list_element, we ``write`` the text with suitable prefixes to the next
    level down, which might be the base of the document (document body) or
    another indentation level, if this is - for example - a nested list.

    In most respects, IndentLevel behaves like a list.
    """

    def __init__(self, base, prefix, first_prefix=None):
        self.base = base  # The list to which we eventually write
        self.prefix = prefix  # Text prepended to lines
        # Text prepended to first list
        self.first_prefix = prefix if first_prefix is None else first_prefix
        # Our own list to which we append before doing a ``write``
        self.content = []

    def append(self, new):
        self.content.append(new)

    def __getitem__(self, index):
        return self.content[index]

    def __len__(self):
        return len(self.content)

    def __bool__(self):
        return len(self) != 0

    def write(self):
        """Add ``self.contents`` with current ``prefix`` and ``first_prefix``

        Add processed ``self.contents`` to ``self.base``.  The first line has
        ``first_prefix`` prepended, further lines have ``prefix`` prepended.

        Empty (all whitespace) lines get written as bare carriage returns, to
        avoid ugly extra whitespace.
        """
        string = "".join(self.content)
        lines = string.splitlines(True)
        if len(lines) == 0:
            return
        texts = [self.first_prefix + lines[0]]
        for line in lines[1:]:
            if line.strip() == "":  # avoid prefix for empty lines
                texts.append("\n")
            else:
                texts.append(self.prefix + line)
        self.base.append("".join(texts))


class Depth:
    def __init__(self):
        self.depth = 0
        self.sub_depth = {}

    def get(self, name=None):
        if name:
            return self.sub_depth[name] if name in self.sub_depth else 0
        return self.depth

    def descend(self, name=None):
        self.depth = self.depth + 1
        if name:
            sub_depth = (self.sub_depth[name] if name in self.sub_depth else 0) + 1
            self.sub_depth[name] = sub_depth
        return self.get(name)

    def ascend(self, name=None):
        self.depth = max(0, self.depth - 1)
        if name:
            sub_depth = max(0, (self.sub_depth[name] if name in self.sub_depth else 0) - 1)
            self.sub_depth[name] = sub_depth
        return self.get(name)
