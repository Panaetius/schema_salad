from typing import List, Optional, Sequence, Tuple, Union

from .sourceline import SourceLine, reflow_all, strip_duplicated_lineno


class SchemaSaladException(Exception):
    """Base class for all schema-salad exceptions."""

    def __init__(
        self,
        msg: str,
        sl: Optional[SourceLine] = None,
        children: Optional[Sequence["SchemaSaladException"]] = None,
        bullet_for_children: str = "",
    ) -> None:
        super(SchemaSaladException, self).__init__(msg)
        self.message = self.args[0]
        self.file = None  # type: Optional[str]
        self.start = None  # type: Optional[Tuple[int, int]]
        self.end = None  # type: Optional[Tuple[int, int]]

        # It will be set by its parent
        self.bullet = ""  # type: str

        def simplify(exc: "SchemaSaladException") -> List["SchemaSaladException"]:
            return [exc] if len(exc.message) else exc.children

        def with_bullet(
            exc: "SchemaSaladException", bullet: str
        ) -> "SchemaSaladException":
            if exc.bullet == "":
                exc.bullet = bullet
            return exc

        if children is None:
            self.children = []  # type: List["SchemaSaladException"]
        elif len(children) <= 1:
            self.children = sum((simplify(c) for c in children), [])
        else:
            self.children = sum(
                (simplify(with_bullet(c, bullet_for_children)) for c in children), []
            )

        self.with_sourceline(sl)
        self.propagate_sourceline()

    def propagate_sourceline(self) -> None:
        if self.file is None:
            return
        for c in self.children:
            if c.file is None:
                c.file = self.file
                c.start = self.start
                c.end = self.end
                c.propagate_sourceline()

    def with_sourceline(self, sl: Optional[SourceLine]) -> "SchemaSaladException":
        if sl and sl.file():
            self.file = sl.file()
            self.start = sl.start()
            self.end = sl.end()
        else:
            self.file = None
            self.start = None
            self.end = None
        return self

    def leaves(self) -> List["SchemaSaladException"]:
        if len(self.children):
            return sum((c.leaves() for c in self.children), [])
        elif len(self.message):
            return [self]
        else:
            return []

    def prefix(self) -> str:
        if self.file:
            linecol0 = ""  # type: Union[int, str]
            linecol1 = ""  # type: Union[int, str]
            if self.start:
                linecol0, linecol1 = self.start
            return "{}:{}:{}: ".format(self.file, linecol0, linecol1)
        else:
            return ""

    def summary(self, level: int = 0, with_bullet: bool = False) -> str:
        indent_per_level = 2
        spaces = (level * indent_per_level) * " "
        bullet = self.bullet + " " if len(self.bullet) and with_bullet else ""
        return "{}{}{}{}".format(self.prefix(), spaces, bullet, self.message)

    def __str__(self) -> str:
        return str(self.pretty_str())

    def pretty_str(self, level: int = 0) -> str:
        messages = len(self.message)
        my_summary = [self.summary(level, True)] if messages else []
        next_level = level + 1 if messages else level

        ret = "\n".join(
            (e for e in my_summary + [c.pretty_str(next_level) for c in self.children])
        )
        if level == 0:
            return strip_duplicated_lineno(reflow_all(ret))
        else:
            return ret


class SchemaException(SchemaSaladException):
    """Indicates error with the provided schema definition."""

    pass


class ValidationException(SchemaSaladException):
    """Indicates error with document against the provided schema."""

    pass


class ClassValidationException(ValidationException):
    pass


def to_one_line_messages(exc: SchemaSaladException) -> str:
    return "\n".join((c.summary() for c in exc.leaves()))
