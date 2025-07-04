def description_from_docstring(docstring: str) -> str:
    return "\n".join(ln.strip() for ln in docstring.split("\n")).strip()
