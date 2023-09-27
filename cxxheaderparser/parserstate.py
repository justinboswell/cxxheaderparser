import typing

if typing.TYPE_CHECKING:
    from .visitor import CxxVisitor  # pragma: nocover

from .errors import CxxParseError
from .lexer import LexToken, Location
from .types import ClassDecl, NamespaceDecl


class ParsedTypeModifiers(typing.NamedTuple):
    vars: typing.Dict[str, LexToken]  # only found on variables
    both: typing.Dict[str, LexToken]  # found on either variables or functions
    meths: typing.Dict[str, LexToken]  # only found on methods

    def validate(self, *, var_ok: bool, meth_ok: bool, msg: str) -> None:
        # Almost there! Do any checks the caller asked for
        if not var_ok and self.vars:
            for tok in self.vars.values():
                raise CxxParseError(f"{msg}: unexpected '{tok.value}'")

        if not meth_ok and self.meths:
            for tok in self.meths.values():
                raise CxxParseError(f"{msg}: unexpected '{tok.value}'")

        if not meth_ok and not var_ok and self.both:
            for tok in self.both.values():
                raise CxxParseError(f"{msg}: unexpected '{tok.value}'")


#: custom user data for this state type
T = typing.TypeVar("T")

#: type of custom user data for a parent state
PT = typing.TypeVar("PT")


class State(typing.Generic[T, PT]):
    #: Uninitialized user data available for use by visitor implementations. You
    #: should set this in a ``*_start`` method.
    user_data: T

    #: parent state
    parent: typing.Optional["State[PT, typing.Any]"]

    #: Approximate location that the parsed element was found at
    location: Location

    #: internal detail used by parser
    _prior_visitor: "CxxVisitor"

    def __init__(self, parent: typing.Optional["State[PT, typing.Any]"]) -> None:
        self.parent = parent

    def _finish(self, visitor: "CxxVisitor") -> None:
        pass


class ExternBlockState(State[T, PT]):
    parent: State[PT, typing.Any]

    #: The linkage for this extern block
    linkage: str

    def __init__(self, parent: typing.Optional[State], linkage: str) -> None:
        super().__init__(parent)
        self.linkage = linkage

    def _finish(self, visitor: "CxxVisitor") -> None:
        visitor.on_extern_block_end(self)


class NamespaceBlockState(State[T, PT]):
    parent: State[PT, typing.Any]

    #: The incremental namespace for this block
    namespace: NamespaceDecl

    def __init__(
        self, parent: typing.Optional[State], namespace: NamespaceDecl
    ) -> None:
        super().__init__(parent)
        self.namespace = namespace

    def _finish(self, visitor: "CxxVisitor") -> None:
        visitor.on_namespace_end(self)


class ClassBlockState(State[T, PT]):
    parent: State[PT, typing.Any]

    #: class decl block being processed
    class_decl: ClassDecl

    #: Current access level for items encountered
    access: str

    #: Currently parsing as a typedef
    typedef: bool

    #: modifiers to apply to following variables
    mods: ParsedTypeModifiers

    def __init__(
        self,
        parent: typing.Optional[State],
        class_decl: ClassDecl,
        access: str,
        typedef: bool,
        mods: ParsedTypeModifiers,
    ) -> None:
        super().__init__(parent)
        self.class_decl = class_decl
        self.access = access
        self.typedef = typedef
        self.mods = mods

    def _set_access(self, access: str) -> None:
        self.access = access

    def _finish(self, visitor: "CxxVisitor") -> None:
        visitor.on_class_end(self)
