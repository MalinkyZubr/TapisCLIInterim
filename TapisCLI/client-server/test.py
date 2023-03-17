from TypeEnforcement.type_enforcer import TypeEnforcer as t
import typing


if __name__ == "__main__":
    class Silly:
        pass

    class Doof(Silly):
        pass

    @t.enforcer(recursive=True)
    def foo(n, t: tuple[int, str], h: dict[str,int], v: typing.Callable, f: list[str], x: typing.Any, y: str, z: typing.Optional[bool]=True, a: str="hello") -> tuple[str, int]:
        return ("hi", "x")
    
    class zeugma:
        @t.enforcer(recursive=True)
        def foo(self, n, t: tuple[int, str], h: dict[str,int], v: typing.Callable, f: list[str], x: typing.Any, y: str, z: typing.Optional[bool]=True, a: str="hello") -> tuple[str, int]:
            return ("hi", "x", 1)

    def zoo():
        pass

    z = zeugma()
    x = z.foo(Doof(), (2,"hi"), {"x":1} , zoo, ['r', 'r'], 1, "hi", z=None)
    print(x)
