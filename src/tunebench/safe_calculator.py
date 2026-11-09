"""Bounded Decimal arithmetic for model-supplied expressions, never Python eval.

Input-number presence does not prove that the correct facts or scope were chosen;
that alignment remains a fallible model-review responsibility.
"""

import ast
import re
from decimal import Decimal, InvalidOperation, localcontext

_WORDS = dict(
    zip(
        (
            "zero one two three four five six seven eight nine ten "
            "eleven twelve thirteen fourteen fifteen sixteen seventeen eighteen nineteen"
        ).split(),
        range(20),
        strict=True,
    )
)
_WORDS.update(
    dict(
        zip(
            "twenty thirty forty fifty sixty seventy eighty ninety hundred thousand".split(),
            [20, 30, 40, 50, 60, 70, 80, 90, 100, 1000],
            strict=True,
        )
    )
)


def source_numbers(message, order_id):
    text = message.replace(order_id, " ")
    text = re.sub(r"\b(?:INR|USD|EUR|GBP|Rs\.?)(?=\d)", "", text, flags=re.I)
    text = re.sub(r"\b[A-Za-z][^\s,;]*\d[^\s,;]*", " ", text)
    numbers = {
        Decimal(x.replace(",", ""))
        for x in re.findall(r"(?<![\w.])\d+(?:,\d{3})*(?:\.\d+)?(?!\w|\.\d)", text)
    }
    words = re.findall(r"[a-z]+", text.casefold())
    numbers.update(Decimal(_WORDS[w]) for w in words if w in _WORDS)
    if "half" in words:
        numbers.update([Decimal(2), Decimal("0.5")])
    if "quarter" in words:
        numbers.update([Decimal(4), Decimal("0.25")])
    structural = {Decimal(0), Decimal(1)}
    if "%" in text or any(w in words for w in ["percent", "percentage"]):
        structural.add(Decimal(100))
    return numbers, structural


def calculate(expression, message, order_id=""):
    if not isinstance(expression, str) or not expression.strip() or len(expression) > 160:
        raise ValueError("Provide a bounded arithmetic expression")
    actual, structural = (
        source_numbers(message, order_id) if order_id else source_numbers(message, "\0")
    )
    tree = ast.parse(expression.strip(), mode="eval")
    if len(list(ast.walk(tree))) > 80:
        raise ValueError("Calculation is too complex")
    used = []

    def visit(node):
        if isinstance(node, ast.Constant) and type(node.value) in {int, float}:
            value = Decimal(ast.get_source_segment(expression.strip(), node))
            if (
                not value.is_finite()
                or abs(value) > Decimal("1e12")
                or value not in actual | structural
            ):
                raise ValueError("Calculation uses an unsupported or unsupplied number")
            used.append(value)
            return value
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
            val = visit(node.operand)
            return -val if isinstance(node.op, ast.USub) else val
        if isinstance(node, ast.BinOp) and isinstance(
            node.op, (ast.Add, ast.Sub, ast.Mult, ast.Div)
        ):
            left, right = visit(node.left), visit(node.right)
            if isinstance(node.op, ast.Add):
                val = left + right
            elif isinstance(node.op, ast.Sub):
                val = left - right
            elif isinstance(node.op, ast.Mult):
                val = left * right
            else:
                val = left / right
        elif (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id in {"min", "max"}
            and 1 <= len(node.args) <= 6
            and not node.keywords
        ):
            values = [visit(arg) for arg in node.args]
            val = min(values) if node.func.id == "min" else max(values)
        else:
            raise ValueError("Only numeric +, -, *, /, min and max are allowed")
        if not val.is_finite() or abs(val) > Decimal("1e12"):
            raise ValueError("Calculation exceeds the supported range")
        return val

    try:
        with localcontext() as context:
            context.prec = 40
            result = visit(tree.body)
    except (ArithmeticError, InvalidOperation) as exc:
        raise ValueError("Invalid arithmetic") from exc
    if not any(value in actual for value in used):
        raise ValueError("Calculation must use supplied numeric evidence")
    return result
