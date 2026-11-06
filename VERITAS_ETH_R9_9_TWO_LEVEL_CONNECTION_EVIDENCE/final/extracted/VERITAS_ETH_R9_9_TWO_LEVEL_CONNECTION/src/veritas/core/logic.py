"""Deterministic propositional parser. NOT an English understanding system."""
from __future__ import annotations
import re
from dataclasses import dataclass
from veritas.core.cnf import CNF

TOKEN = re.compile(r"\s*(->|=>|\(|\)|!|~|&|\||\bAND\b|\bOR\b|\bNOT\b|\bTRUE\b|\bFALSE\b|[A-Za-z][A-Za-z0-9_]*)", re.I)

@dataclass(frozen=True)
class Expr:
    op: str
    args: tuple["Expr", ...] = ()
    name: str = ""

    def variables(self) -> set[str]:
        return {self.name} if self.op == "var" else set().union(*(arg.variables() for arg in self.args))

    def eval(self, model: dict[str, bool]) -> bool:
        if self.op == "var": return model[self.name]
        if self.op == "const": return self.name == "TRUE"
        if self.op == "not": return not self.args[0].eval(model)
        if self.op == "and": return self.args[0].eval(model) and self.args[1].eval(model)
        if self.op == "or": return self.args[0].eval(model) or self.args[1].eval(model)
        if self.op == "implies": return not self.args[0].eval(model) or self.args[1].eval(model)
        raise AssertionError(self.op)


class Parser:
    def __init__(self, src: str):
        if not src or len(src) > 5_000:
            raise ValueError("expression must be 1..5,000 characters")
        self.tokens = []
        pos = 0
        while pos < len(src):
            if not src[pos:].strip(): break
            match = TOKEN.match(src, pos)
            if not match:
                raise ValueError(f"unrecognized token at position {pos}: {src[pos:pos+15]!r}")
            self.tokens.append(match.group(1))
            pos = match.end()
            if len(self.tokens) > 1000:
                raise ValueError("too many expression tokens")
        self.pos = 0

    def peek(self): return self.tokens[self.pos] if self.pos < len(self.tokens) else None
    def take(self):
        token = self.peek()
        if token is None: raise ValueError("unexpected end of formula")
        self.pos += 1
        return token

    def parse(self) -> Expr:
        expr = self.implication()
        if self.peek() is not None:
            raise ValueError(f"unexpected token {self.peek()!r}")
        return expr

    def implication(self):
        lhs = self.disjunction()
        if self.peek() in ("->", "=>"):
            self.take()
            return Expr("implies", (lhs, self.implication()))
        return lhs

    def disjunction(self):
        lhs = self.conjunction()
        while self.peek() is not None and self.peek().upper() in ("OR", "|"):
            self.take(); lhs = Expr("or", (lhs, self.conjunction()))
        return lhs

    def conjunction(self):
        lhs = self.unary()
        while self.peek() is not None and self.peek().upper() in ("AND", "&"):
            self.take(); lhs = Expr("and", (lhs, self.unary()))
        return lhs

    def unary(self):
        t = self.take()
        if t.upper() in ("!", "~", "NOT"):
            return Expr("not", (self.unary(),))
        if t == "(":
            inner = self.implication()
            if self.take() != ")": raise ValueError("expected closing parenthesis")
            return inner
        if t.upper() in ("TRUE", "FALSE"):
            return Expr("const", name=t.upper())
        if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*", t) or t.upper() in ("AND", "OR", "NOT"):
            raise ValueError(f"invalid identifier {t!r}")
        return Expr("var", name=t)


def parse(src: str) -> Expr:
    return Parser(src).parse()


def encode(expr: Expr) -> tuple[CNF, dict[str, int]]:
    """Definitional Tseitin encoding, unique extension for every primary valuation.

    IMPORTANT: A model count over the encoding counts aux variables too; the
    unique-extension guarantee makes its count equal to that of the original
    expression, but callers must preserve this invariant.
    """
    names = sorted(expr.variables())
    if len(names) > 160:
        raise ValueError("too many primary variables")
    mapping = {name: i+1 for i, name in enumerate(names)}
    clauses: list[tuple[int, ...]] = []
    next_var = len(mapping)
    def aux():
        nonlocal next_var
        next_var += 1
        return next_var
    def visit(e: Expr) -> int:
        if e.op == "var": return mapping[e.name]
        v = aux()
        if e.op == "const":
            clauses.append((v,) if e.name == "TRUE" else (-v,))
        elif e.op == "not":
            a = visit(e.args[0])
            clauses.extend([(-v, -a), (v, a)])
        else:
            a, b = (visit(c) for c in e.args)
            if e.op == "and":
                clauses.extend([(-v, a), (-v, b), (v, -a, -b)])
            elif e.op == "or":
                clauses.extend([(v, -a), (v, -b), (-v, a, b)])
            elif e.op == "implies":
                clauses.extend([(v, a), (v, -b), (-v, -a, b)])
            else: raise AssertionError(e.op)
        return v
    clauses.append((visit(expr),))
    return CNF(next_var, tuple(clauses)), mapping


def entailment_query(premises: list[str], conclusion: str):
    if len(premises) > 60:
        raise ValueError("too many premises")
    parsed_premises = [parse(p) for p in premises]
    target = parse(conclusion)
    query = Expr("not", (target,))
    for premise in reversed(parsed_premises):
        query = Expr("and", (premise, query))
    cnf, mapping = encode(query)
    return cnf, mapping, parsed_premises, target
