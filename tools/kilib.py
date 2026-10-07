"""Minimal KiCad S-expression reader/writer and symbol-library helpers for the VanController generators."""
import os
import re

KICAD = r"C:\Program Files\KiCad\10.0\share\kicad"
SYMDIR = os.path.join(KICAD, "symbols")
FPDIR = os.path.join(KICAD, "footprints")

_tok = re.compile(r'\s*(\(|\)|"(?:\\.|[^"\\])*"|[^\s()]+)', re.S)


class Sym(str):
    """An unquoted atom (keyword or number), as opposed to a quoted string (plain str)."""


def parse(text):
    stack, cur = [], []
    for m in _tok.finditer(text):
        t = m.group(1)
        if t == "(":
            stack.append(cur)
            cur = []
        elif t == ")":
            done = cur
            cur = stack.pop()
            cur.append(done)
        elif t.startswith('"'):
            cur.append(t[1:-1].replace('\\"', '"').replace("\\\\", "\\"))
        else:
            cur.append(Sym(t))
    return cur[0]


def dump(node, indent=0):
    """Serialise back to KiCad's tab-indented style."""
    if not isinstance(node, list):
        if isinstance(node, Sym):
            return str(node)
        return '"' + node.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n") + '"'
    if all(not isinstance(c, list) for c in node):
        return "(" + " ".join(dump(c) for c in node) + ")"
    pad = "\t" * (indent + 1)
    head = []
    rest = []
    for c in node:
        (rest if (isinstance(c, list) or rest) else head).append(c)
    s = "(" + " ".join(dump(c) for c in head)
    for c in rest:
        s += "\n" + pad + dump(c, indent + 1)
    return s + "\n" + "\t" * indent + ")"


def find(node, key):
    return [c for c in node if isinstance(c, list) and c and c[0] == key]


def first(node, key):
    r = find(node, key)
    return r[0] if r else None


_libcache = {}


def load_lib(lib):
    if lib not in _libcache:
        with open(os.path.join(SYMDIR, lib + ".kicad_sym"), encoding="utf-8") as f:
            tree = parse(f.read())
        _libcache[lib] = {c[1]: c for c in find(tree, "symbol")}
    return _libcache[lib]


def _rename_units(sym, old, new):
    for c in find(sym, "symbol"):
        if c[1].startswith(old + "_"):
            c[1] = new + c[1][len(old):]


def flat_symbol(lib_id):
    """Return a deep-copied, flattened (no 'extends') symbol named 'Lib:Name' ready for lib_symbols."""
    import copy
    lib, name = lib_id.split(":")
    syms = load_lib(lib)
    sym = copy.deepcopy(syms[name])
    ext = first(sym, "extends")
    if ext:
        parent = copy.deepcopy(syms[ext[1]])
        while first(parent, "extends"):
            parent = copy.deepcopy(syms[first(parent, "extends")[1]])
        pname = parent[1]
        child_props = {p[1]: p for p in find(sym, "property")}
        out = [Sym("symbol"), name]
        for c in parent[2:]:
            if isinstance(c, list) and c[0] == "property" and c[1] in child_props:
                out.append(child_props.pop(c[1]))
            else:
                out.append(c)
        # child-only properties go after the inherited ones
        idx = max(i for i, c in enumerate(out) if isinstance(c, list) and c[0] == "property") + 1
        for p in child_props.values():
            out.insert(idx, p)
            idx += 1
        sym = out
        _rename_units(sym, pname, name)
    sym[1] = lib_id
    return sym


def pins(sym, unit=1):
    """Pins of the given unit (unit 0 = common to all units), body style 1."""
    out = []
    for u in find(sym, "symbol"):
        m = re.search(r"_(\d+)_(\d+)$", u[1])
        uu, style = int(m.group(1)), int(m.group(2))
        if uu not in (0, unit) or style not in (0, 1):
            continue
        for p in find(u, "pin"):
            at = first(p, "at")
            out.append({
                "type": str(p[1]),
                "name": first(p, "name")[1],
                "number": first(p, "number")[1],
                "x": float(at[1]), "y": float(at[2]), "angle": int(float(at[3])) if len(at) > 3 else 0,
                "hidden": any(isinstance(c, list) and c[0] == "hide" and c[1] == "yes" for c in p)
                or "hide" in [c for c in p if isinstance(c, Sym)],
            })
    return out


def units(sym):
    us = set()
    for u in find(sym, "symbol"):
        m = re.search(r"_(\d+)_(\d+)$", u[1])
        if int(m.group(1)):
            us.add(int(m.group(1)))
    return sorted(us) or [1]


def prop(sym, name):
    p = [c for c in find(sym, "property") if c[1] == name]
    return p[0][2] if p else ""


def fp_pads(fpid):
    lib, name = fpid.split(":")
    with open(os.path.join(FPDIR, lib + ".pretty", name + ".kicad_mod"), encoding="utf-8") as f:
        tree = parse(f.read())
    return sorted({str(p[1]) for p in find(tree, "pad") if p[1] != ""})
