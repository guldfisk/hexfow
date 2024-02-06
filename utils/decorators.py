import typing as t

T = t.TypeVar("T")


class ClassProperty(t.Generic[T]):
    def __init__(self, f: t.Callable[..., T]):
        self.f = f

    def __get__(self, instance, owner) -> T:
        return self.f(owner)



class A:

    @ClassProperty
    def v(cls) -> int:
        return 10


# A.v