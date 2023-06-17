"""
Context handlers.
"""
from tabulate import tabulate


class SubContext:
    def __init__(self):
        self.body = []

    @property
    def content(self):
        return self.body

    def __getitem__(self, index):
        return self.content[index]

    def __len__(self):
        return len(self.content)

    def __bool__(self):
        return len(self) != 0

    def add(self, value: str):
        self.content.append(value)

    def make(self):
        return "".join(self.content)


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
    def __init__(self):
        super().__init__()
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

    @property
    def content(self):
        return self.active_output[-1][-1]

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
        self.content.append(value)

    @staticmethod
    def make_row(row):
        return ["".join(entries).replace("\n", "<br/>") for entries in row]

    def make(self):
        if len(self.headers) == 0 and len(self.body) == 0:
            return ""

        if len(self.headers) == 0:
            self.headers = [self.body[0]]
            self.body = self.body[1:]

        assert len(self.headers) == 1
        headers = self.make_row(self.headers[0])

        body = list(map(self.make_row, self.body))
        return tabulate(body, headers=headers, tablefmt="github")


class IndentContext(SubContext):
    """Class to hold text being written for a certain indentation level.

    For example, all text in list_elements need to be indented.  A list_element
    creates one of these indentation levels, and all text contained in the
    list_element gets written to this IndentLevel.  When we leave the
    list_element, we ``write`` the text with suitable prefixes to the next
    level down, which might be the base of the document (document body) or
    another indentation level, if this is - for example - a nested list.

    In most respects, IndentLevel behaves like a list.
    """

    def __init__(self, prefix, first_prefix=None):
        super().__init__()
        self.prefix = prefix  # Text prepended to lines
        # Text prepended to first list
        self.first_prefix = prefix if first_prefix is None else first_prefix
        # Our own list to which we append before doing a ``write``

    def append(self, new):
        self.body.append(new)

    def make(self):
        """Add ``self.contents`` with current ``prefix`` and ``first_prefix``

        Add processed ``self.contents`` to ``self.base``.  The first line has
        ``first_prefix`` prepended, further lines have ``prefix`` prepended.

        Empty (all whitespace) lines get written as bare carriage returns, to
        avoid ugly extra whitespace.
        """
        content = super().make()
        lines = content.splitlines(True)
        if len(lines) == 0:
            return ""
        texts = [self.first_prefix + lines[0]]
        for line in lines[1:]:
            if line.strip() == "":  # avoid prefix for empty lines
                texts.append("\n")
            else:
                texts.append(self.prefix + line)
        return "".join(texts)


class Depth:
    def __init__(self):
        self.sub_depth = {}

    def get(self, name: str):
        return self.sub_depth.get(name, 0)

    def descend(self, name: str):
        self.sub_depth[name] = self.sub_depth.get(name, 0) + 1
        return self.get(name)

    def ascend(self, name: str):
        self.sub_depth[name] = max(0, self.sub_depth.get(name, 0) - 1)
        return self.get(name)
