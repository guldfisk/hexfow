import re


def _sort_key(s: str) -> tuple[float, str]:
    v = eval(re.search(r"price=([^\s,]+)", s, re.MULTILINE).group(1))
    return (
        1 - 1 / v if v is not None else 1,
        re.search(r"^(\S+) = UnitBlueprint", s, re.MULTILINE).group(1),
    )


def sort_blueprint():
    with open("game/units/blueprints.py", "r") as f:
        s = f.read()

    fragments = re.split("\n{2,}", s)

    # for v in fragments[1:]:
    #     # print(v)
    #     # print(re.search(r'^(\S+) = UnitBlueprint', v, re.MULTILINE).group(1))
    #     print()

    with open("game/units/blueprints.py", "w") as f:
        f.write(
            "\n\n".join([fragments[0] + "\n", *sorted(fragments[1:], key=_sort_key)])
        )
    # ns = "\n\n".join([fragments[0], *sorted(fragments[1:], key=_sort_key)])
    #
    # print(ns)

    # print(len(fragments))

    # for v in fragments:
    #     print(v)


if __name__ == "__main__":
    sort_blueprint()
