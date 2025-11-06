import re


def _sort_key(s: str) -> tuple[bool, float, str]:
    v = eval(re.search(r"price=([^\s,]+)", s, re.MULTILINE).group(1))
    max_count = re.search(r"max_count=([^\s,]+)", s, re.MULTILINE)
    return (
        bool(max_count and max_count.group(1) == "0"),
        1 - 1 / v if v is not None else 1,
        re.search(r"^(\S+) = UnitBlueprint", s, re.MULTILINE).group(1),
    )


def sort_blueprint():
    with open("game/units/blueprince.py", "r") as f:
        s = f.read()

    fragments = re.split("\n{2,}", s)

    with open("game/units/blueprince.py", "w") as f:
        f.write(
            "\n\n".join([fragments[0] + "\n", *sorted(fragments[1:], key=_sort_key)])
        )


if __name__ == "__main__":
    sort_blueprint()
