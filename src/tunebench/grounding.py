"""Evidence extraction and transparent decision checks for fictional order tools.

This is a deterministic domain policy, not another language model. It records
literal evidence and exact calculations, resolves explicit authoritative
corrections, and leaves unresolved alternatives ambiguous. It never changes a
model's outcome. The benchmark schemas and historical research runner are separate.
"""

from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation
from typing import Any

from tunebench.contracts import load_tool_registry, validate_prediction
from tunebench.mock_tools import load_demo_orders

POLICY_VERSION = "structured-evidence-v2"
_NUM = r"-?\d+(?:,\d{3})*(?:\.\d+)?"
_WORDS = {
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
    "eleven": 11,
    "twelve": 12,
    "fifteen": 15,
    "twenty": 20,
    "twenty-five": 25,
    "thirty": 30,
    "forty": 40,
    "fifty": 50,
    "sixty": 60,
    "seventy": 70,
    "eighty": 80,
    "ninety": 90,
    "hundred": 100,
}
_QTY = r"(?:\d+|" + "|".join(sorted(_WORDS, key=len, reverse=True)) + r")"
_QUOTE = re.compile(r'"([^"\n]+)"|“([^”\n]+)”|(?<!\w)\'([^\'\n]+)\'(?!\w)')
_UNCERTAIN = re.compile(
    r"\b(?:unresolved|uncertain|unconfirmed|equally|alternatives?|undecided)\b|"
    r"\b(?:cannot|can't|can not)\s+(?:confirm|choose|distinguish)|"
    r"\bneither\b.{0,55}\b(?:priority|authoritative|confirmed|selected)|"
    r"\b(?:might|may)\s+(?:be|instead)",
    re.I,
)
_REASON_PATTERNS = {
    "damaged_item": (
        r"\bdamaged(?:_item)?\b|\bdamage\b|\bbroken\b|\bcracked\b|"
        r"\bshattered\b|\bdented\b|\bdefective\b"
    ),
    "wrong_item": (
        r"\bwrong[_ ](?:item|product|model|size|colour|color)\b|\bincorrect item\b|"
        r"\b(?:completely )?different item\b|\bincorrectly supplied\b"
    ),
    "not_received": (
        r"\bnot[_ ]received\b|\bnon[- ]?receipt\b|"
        r"\bnever\s+(?:arrived|received|reached(?: me| us)?|delivered)\b|"
        r"\b(?:has not|hasn't|did not|didn't|not)\s+(?:arrive(?:d)?|been delivered|received)\b|"
        r"\bno\s+(?:item|parcel|package|part)\b.{0,50}\b(?:arrived|delivered|received)\b"
    ),
    "changed_mind": (
        r"\bchanged[_ ](?:my[_ ]|their[_ ]|our[_ ])?mind\b|"
        r"\bno longer\s+(?:need|want)\b"
    ),
}


def _blank(text: str) -> str:
    return "".join("\n" if character == "\n" else " " for character in text)


def _trusted(message: str) -> tuple[str, list[dict[str, Any]]]:
    """Mask explicitly quoted untrusted instructions while retaining literal data."""
    chars = list(message)
    ignored = []
    for match in _QUOTE.finditer(message):
        content = next(group for group in match.groups() if group is not None)
        prefix = message[max(0, match.start() - 130) : match.start()]
        suffix = message[match.end() : match.end() + 130]
        instruction = re.search(
            r"\b(?:ignore|disregard|SYSTEM\s*:|call\s+\w+|get_order_status|propose_refund)\b",
            content,
            re.I,
        )
        marked = re.search(
            r"\b(?:untrusted|spam|forged|pasted|quoted|banner|injection)\b",
            prefix + " " + suffix,
            re.I,
        )
        if instruction and marked:
            chars[match.start() : match.end()] = _blank(match.group())
            ignored.append({"text": content, "start": match.start(), "end": match.end()})
    return "".join(chars), ignored


def _current_request(text: str) -> tuple[str, str, int]:
    markers = list(
        re.finditer(
            r"(?:^|\n)(?:(?:earlier|current|later|previous|latest|final)\s+)?"
            r"(?:customer|user|assistant|agent)\s*:",
            text,
            re.I,
        )
    )
    if not markers:
        return text, text, 0
    user_chunks = []
    last_offset = 0
    current = ""
    for index, marker in enumerate(markers):
        end = markers[index + 1].start() if index + 1 < len(markers) else len(text)
        if re.search(r"(?:customer|user)\s*:", marker.group(), re.I):
            current = text[marker.end() : end]
            last_offset = marker.end()
            user_chunks.append(current)
    # Preserve positions while excluding statements authored by an earlier assistant.
    evidence = list(_blank(text))
    for index, marker in enumerate(markers):
        end = markers[index + 1].start() if index + 1 < len(markers) else len(text)
        if re.search(r"(?:customer|user)\s*:", marker.group(), re.I):
            evidence[marker.end() : end] = text[marker.end() : end]
    return current or text, "".join(evidence), last_offset


def _negative_action(text: str, start: int) -> bool:
    prefix = re.split(r"[.;\n]|\bbut\b|\binstead\b", text[:start], flags=re.I)[-1][-100:]
    return bool(
        re.search(
            r"\b(?:do not|don't|never|without|not asking|not requesting|not a|not an|"
            r"not to|no need to)\b|\bno\s+(?:action|status|tracking|lookup|proposal)\b|"
            r"\bno\s+(?:(?:order|refund)\s+)?$|"
            r"\bnot\s+(?:an?\s+)?(?:decision about\s+)?$",
            prefix,
            re.I,
        )
    )


def _intent(request: str) -> tuple[str, list[dict[str, Any]]]:
    text = request.casefold()
    actions = []
    patterns = {
        "get_order_status": r"\border[- ]status\b|\bstatus\b|\btracking\b|\btrack\b|"
        r"\bwhere\b.{0,30}\b(?:order|parcel|package)\b",
        "check_refund_eligibility": r"\beligib\w*\b|\bqualif\w*\b",
        "propose_refund": r"\bpropos(?:e|al|als|ing)\b|\bdraft\b.{0,25}\brefund\b|"
        r"\b(?:simulated|mock)\s+refund\b",
        "unsupported": r"\bcancel\w*\b|\bexchange\b|\bdelete\b.{0,25}\baccount\b|"
        r"\b(?:change|replace|update)\b.{0,35}\b(?:address|password|delivery date)\b|"
        r"\b(?:execute|process|issue|pay|transfer|send|credit)\b.{0,45}"
        r"\b(?:refund|funds|money|payment|back|bank|card|account)\b|\brefund me\b",
    }
    for tool, pattern in patterns.items():
        for match in re.finditer(pattern, text, re.I):
            negative = _negative_action(text, match.start())
            actions.append(
                {
                    "tool": tool,
                    "text": request[match.start() : match.end()],
                    "start": match.start(),
                    "end": match.end(),
                    "negated": negative,
                }
            )
    positive = {action["tool"] for action in actions if not action["negated"]}
    closure = re.search(
        r"\b(?:withdraw|withdrawn|take no action|leave everything|nothing else|"
        r"for your records only|no action is (?:needed|required)|no reply)\b",
        text,
    )
    information = re.search(
        r"\b(?:explain|define|meaning|mean|conceptually|terminology|in general|generally|"
        r"typical|difference|features|advice|recommend)\b|\bhow\b.{0,30}\b(?:differ|work)\b",
        text,
    )
    explicit_action = re.search(
        r"\b(?:check|fetch|retrieve|look up|lookup|show|get|track|tell me|create|prepare|"
        r"make|record|propose|requesting|want|need)\b",
        text,
    )
    if closure:
        return "none", actions
    if "unsupported" in positive and not information:
        return "unsupported", actions
    if information:
        # An explicit later imperative may follow an informational background clause.
        last_info = max(match.start() for match in re.finditer(information.re, text))
        later = re.search(
            r"\b(?:but|and|then)\s+(?:please\s+)?(?:check|fetch|retrieve|create|prepare|propose)\b",
            text[last_info:],
        )
        if not later:
            return "informational", actions
    if re.search(r"\bhypothetical(?:ly)?\b|\bwhat if\b", text) and not information:
        return "none", actions
    supported = positive - {"unsupported"}
    if supported and explicit_action:
        return (next(iter(supported)) if len(supported) == 1 else "ambiguous"), actions
    if "get_order_status" in supported and re.search(r"\bwhere\b|\bwhat\b", text):
        return "get_order_status", actions
    if "check_refund_eligibility" in supported and re.search(r"\b(?:is|am|does|can)\b", text):
        return "check_refund_eligibility", actions
    if any(action["negated"] for action in actions) and not supported:
        return "none", actions
    if re.search(r"\b(?:thanks|thank you|that is all|that's all|no action)\b", text):
        return "none", actions
    if re.search(r"\b(?:order|refund|action|help)\b", text):
        return "ambiguous", actions
    return "informational", actions


def _references(text: str) -> list[dict[str, Any]]:
    records = []
    for quote in _QUOTE.finditer(text):
        value = next(group for group in quote.groups() if group is not None)
        before = text[max(0, quote.start() - 100) : quote.start()]
        if re.search(r"\b(?:order|identifier|reference|receipt)\b", before, re.I) and (
            len(value) < 120 and not re.search(r"\b(?:says|saying|term|word)\s*$", before, re.I)
        ):
            records.append(
                {
                    "value": value,
                    "start": quote.start() + 1,
                    "end": quote.end() - 1,
                    "source": "quoted",
                }
            )
    tokens = re.finditer(r"(?<![\w:/-])[A-Za-z0-9][A-Za-z0-9_:/.-]*(?![\w:/-])", text)
    for token in tokens:
        value = token.group().rstrip(".,;:!?")
        if not value or any(r["start"] <= token.start() < r["end"] for r in records):
            continue
        prefix = text[max(0, token.start() - 55) : token.start()]
        labelled = re.search(
            r"\b(?:order(?:[- ](?:id|identifier|reference|number))?|identifier|reference)"
            r"\s*(?:is|:|=|#)?\s*$",
            prefix,
            re.I,
        )
        shaped = bool(
            re.search(r"[A-Za-z]", value)
            and re.search(r"\d", value)
            and (re.search(r"[-_:/]", value) or re.fullmatch(r"[A-Z]{1,5}\d{2,}", value))
        )
        if (labelled and (re.search(r"\d", value) or re.search(r"[-_:/]", value))) or shaped:
            if not re.fullmatch(r"(?:INR|USD|EUR|GBP|Rs)\d+(?:\.\d+)?", value, re.I):
                records.append(
                    {
                        "value": value,
                        "start": token.start(),
                        "end": token.start() + len(value),
                        "source": "labelled" if labelled else "bare",
                    }
                )
    for record in records:
        prefix = text[max(0, record["start"] - 65) : record["start"]]
        suffix = text[record["end"] : record["end"] + 70]
        excluded = bool(
            re.search(
                r"\bsupport(?:\s+(?:ticket|reference))?(?:\s+(?:id|number))?\s*[:#=]?\s*$|"
                r"\b(?:ignore|disregard|not)\s+(?:order\s+)?[\"']?$",
                prefix,
                re.I,
            )
            or re.search(r"^\s*(?:is\s+)?(?:only\s+)?a support\b", suffix, re.I)
        )
        record["excluded"] = excluded
    return sorted(records, key=lambda r: r["start"])


def _selected(records: list[dict[str, Any]], text: str) -> list[dict[str, Any]]:
    active = [record for record in records if not record.get("excluded")]
    choices = []
    for record in active:
        before = text[max(0, record["start"] - 140) : record["start"]]
        after = text[record["end"] : record["end"] + 70]
        cue = re.search(
            r"\b(?:use|choose|select|only)\s+(?:only\s+)?(?:order\s+)?[\"']?$|"
            r"\breplace\b.{0,100}\bwith\s+(?:order\s+)?[\"']?$|"
            r"\b(?:correction|actually)\s*:\s*(?:order\s+)?[\"']?$|"
            r"\b(?:new|corrected|current)\s+(?:amount|order(?: id)?)\s*(?:is|:)?\s*[\"']?$",
            before,
            re.I,
        ) or re.search(r"^\s*[\"']?\s+instead\b", after, re.I)
        if cue and not _UNCERTAIN.search(before[-60:] + after):
            choices.append(record)
    return [choices[-1]] if choices else active


def _reasons(text: str) -> tuple[list[str], list[dict[str, Any]]]:
    records = []
    for reason, pattern in _REASON_PATTERNS.items():
        for match in re.finditer(pattern, text, re.I):
            prefix = text[max(0, match.start() - 45) : match.start()]
            negated = bool(
                reason != "not_received"
                and re.search(
                    r"\b(?:not|isn't|wasn't|is not|was not|never)\s+"
                    r"(?:(?:at all|actually|really|physically|visibly|even)\s+)*(?:an?\s+)?$",
                    prefix,
                    re.I,
                )
            )
            records.append(
                {
                    "value": reason,
                    "text": match.group(),
                    "start": match.start(),
                    "end": match.end(),
                    "excluded": negated,
                }
            )
    # A contrast between the product ordered and the product delivered is explicit
    # wrong-item evidence; it does not require a phrase from the enum itself.
    contrast = re.search(
        r"\b(?:I\s+)?ordered\s+(.{2,65}?)\s+(?:but|yet)\s+(?:I\s+)?received\s+(.{2,65}?)(?:[.;\n]|$)",
        text,
        re.I,
    )
    if contrast and contrast.group(1).casefold() != contrast.group(2).casefold():
        records.append(
            {
                "value": "wrong_item",
                "text": contrast.group(),
                "start": contrast.start(),
                "end": contrast.end(),
                "excluded": False,
            }
        )
    active = [record for record in records if not record["excluded"]]
    # Confirmed corrections supersede earlier descriptions; uncertain corrections do not.
    correction = list(
        re.finditer(
            r"\b(?:that was (?:a mistake|wrong)|correction\s*:|actually|instead|"
            r"use this corrected account|the corrected reason is)\b",
            text,
            re.I,
        )
    )
    if correction and not _UNCERTAIN.search(text[correction[-1].start() :]):
        later = [record for record in active if record["start"] >= correction[-1].end()]
        if not later:
            # A final 'use this corrected account' confirms the immediately preceding correction.
            start = max(0, correction[-1].start() - 150)
            later = [record for record in active if record["start"] >= start]
            if later:
                later = [later[-1]]
        if later:
            active = later
    return sorted({record["value"] for record in active}), records


def _quantity(value: str) -> Decimal:
    return Decimal(_WORDS[value.casefold()]) if value.casefold() in _WORDS else Decimal(value)


def _currency(before: str, after: str) -> str | None:
    match = re.search(r"(₹|\$|€|£|INR|Rs\.?|USD|EUR|GBP)\s*$", before, re.I)
    match = match or re.match(r"\s*(INR|rupees?|USD|dollars?|EUR|GBP)\b", after, re.I)
    if not match:
        return None
    token = match.group(1).casefold().rstrip(".")
    return (
        "INR"
        if token in {"₹", "inr", "rs", "rupee", "rupees"}
        else ("USD" if token in {"$", "usd", "dollar", "dollars"} else token.upper())
    )


def _amounts(
    text: str,
    references: list[dict[str, Any]],
    intent: str,
) -> tuple[list[Decimal], list[dict[str, Any]], list[dict[str, Any]], bool, bool]:
    records = []
    for match in re.finditer(_NUM, text):
        if any(record["start"] <= match.start() < record["end"] for record in references):
            continue
        if match.start() and text[match.start() - 1].isalnum():
            continue
        value = Decimal(match.group().replace(",", ""))
        before = text[max(0, match.start() - 110) : match.start()]
        before_clause = re.split(r"(?<!\d)\.(?!\d)|[;\n]", before)[-1]
        after = text[match.end() : match.end() + 55]
        currency = _currency(before, after)
        role = "background"
        if re.match(r"\s*(?:%|percent\b|per cent\b)", after, re.I):
            role = "percentage"
        elif re.match(r"\s*(?:each\b|apiece\b|per\s+(?:item|unit)\b)", after, re.I) or re.search(
            r"\b(?:unit price|price per unit|each (?:costs|priced at))"
            r"\s*(?:is|of|:)?\s*(?:INR|₹)?\s*$",
            before,
            re.I,
        ):
            role = "unit_price"
        elif re.search(r"\b(?:shipping|tax|fee|fees|charge)\b[^.;\n]{0,30}$", before, re.I):
            role = "excluded_charge"
        elif re.search(
            r"\b(?:total|base|order price|item price)\s*(?:is|of|:)?\s*(?:INR|₹)?\s*$", before, re.I
        ) or re.match(r"\s*(?:item |order )?total\b", after, re.I):
            role = "base_total"
        elif re.search(
            r"\b(?:amounts?|refund|proposal|propose|requested)\b[^;\n]{0,85}$",
            before_clause,
            re.I,
        ) and not re.match(r"\s+(?:items?|units?|frames?|stools?|pieces?)\b", after, re.I):
            role = "requested"
        elif (
            currency
            and intent == "propose_refund"
            and not re.search(
                r"\b(?:old|previous|background|charge|total|paid)\b[^.;\n]*$",
                before,
                re.I,
            )
        ):
            role = "requested"
        records.append(
            {
                "value": value,
                "text": match.group(),
                "start": match.start(),
                "end": match.end(),
                "role": role,
                "currency": currency,
            }
        )
    calculations = []
    calculation_ambiguity = False
    percent_pattern = rf"\b(?P<pct>{_QTY})(?:\s*%|\s+percent|\s+per cent)\s+of\b"
    percentages = list(re.finditer(percent_pattern, text, re.I))
    for match in percentages:
        percent = _quantity(match.group("pct"))
        # References have already been excluded from monetary records. Searching
        # those records prevents an order number from becoming the percent base.
        candidates = [
            record
            for record in records
            if match.end() <= record["start"] <= match.end() + 100
            and not re.search(r"(?<!\d)\.(?!\d)|[;\n]", text[match.end() : record["start"]])
            and record["role"] not in {"percentage", "unit_price", "excluded_charge"}
            and (record["currency"] or record["role"] == "base_total")
        ]
        if not candidates or not (0 < percent <= 100):
            calculation_ambiguity = True
            continue
        base_record = candidates[0]
        base = base_record["value"]
        if base <= 0:
            calculation_ambiguity = True
            continue
        result = percent * base / Decimal(100)
        calculations.append(
            {
                "operation": "percentage",
                "operands": [str(percent), str(base)],
                "result": result,
                "text": text[match.start() : base_record["end"]],
                "currency": base_record["currency"],
            }
        )
        for record in records:
            if match.start() <= record["start"] < base_record["end"]:
                record["role"] = "calculation_operand"
    for unit in [record for record in records if record["role"] == "unit_price"]:
        beginning = max(0, unit["start"] - 150)
        before_chars = list(text[beginning : unit["start"]])
        for reference in references:
            left = max(beginning, reference["start"])
            right = min(unit["start"], reference["end"])
            if left < right:
                before_chars[left - beginning : right - beginning] = " " * (right - left)
        before = "".join(before_chars)
        quantities = list(
            re.finditer(
                rf"\b(?P<qty>{_QTY})\s+(?P<rest>(?:[A-Za-z-]+\s+){{0,4}}[A-Za-z-]+)",
                before,
                re.I,
            )
        )
        quantities = [
            match
            for match in quantities
            if not re.match(
                r"(?:equally\s+)?(?:invoices?|prices?|reports?|notes?|days?|percent|charges?)\b",
                match.group("rest"),
                re.I,
            )
        ]
        if quantities:
            quantity = _quantity(quantities[-1].group("qty"))
            count_offsets = {beginning + quantities[-1].start("qty")}
            # The requested subset takes precedence over the inventory count.
            # If its product or quantity cannot be reconciled, ask rather than
            # treating every item on the order as authorized for a refund.
            requested_quantities = list(
                re.finditer(
                    rf"\b(?:propos(?:e|al)|refund)\b[^.;\n]{{0,90}}?"
                    rf"\b(?:for|cover(?:ing)?)\s+(?:only\s+)?(?:all\s+)?"
                    rf"(?P<qty>{_QTY})\s+(?P<item>[A-Za-z-]+)",
                    text,
                    re.I,
                )
            )
            requested_quantities = [
                requested
                for requested in requested_quantities
                if requested.group("item").casefold() not in {"inr", "rupees", "percent"}
            ]
            if requested_quantities:
                count_offsets.update(requested.start("qty") for requested in requested_quantities)
                choices = {_quantity(requested.group("qty")) for requested in requested_quantities}
                requested = requested_quantities[-1]
                item = requested.group("item").casefold().removesuffix("s")
                inventory_words = {
                    word.casefold().removesuffix("s")
                    for word in re.findall(r"[A-Za-z-]+", quantities[-1].group("rest"))
                }
                if (
                    len(choices) != 1
                    or next(iter(choices)) > quantity
                    or (item not in inventory_words and item not in {"item", "unit", "piece"})
                ):
                    calculation_ambiguity = True
                    continue
                quantity = next(iter(choices))
            if quantity > 0:
                # Counts in an explicitly requested calculation are operands,
                # even when an adjective separates the number from its noun.
                # They must not also become independent monetary alternatives.
                for record in records:
                    if record["start"] in count_offsets and not record["currency"]:
                        record["role"] = "calculation_operand"
                calculations.append(
                    {
                        "operation": "quantity_times_unit_price",
                        "operands": [str(quantity), str(unit["value"])],
                        "result": quantity * unit["value"],
                        "text": quantities[-1].group() + " ... " + unit["text"],
                        "currency": unit["currency"],
                    }
                )
    requested = [record for record in records if record["role"] == "requested"]
    selected = _selected(requested, text)
    values = {record["value"] for record in selected}
    if calculations:
        values.update(calculation["result"] for calculation in calculations)
    currencies = {record["currency"] for record in selected if record["currency"]}
    currencies.update(
        calculation["currency"] for calculation in calculations if calculation["currency"]
    )
    unresolved = bool(
        calculation_ambiguity
        or len(values) > 1
        or (
            not values
            and len({record["value"] for record in records if record["role"] == "unit_price"}) > 1
        )
    )
    exact = []
    for value in sorted(values):
        try:
            if value == value.quantize(Decimal("0.01")):
                exact.append(value)
            else:
                unresolved = True
        except InvalidOperation:
            unresolved = True
    return exact, records, calculations, bool(currencies - {"INR"}), unresolved


def analyze(message: str) -> dict[str, Any]:
    """Extract explicit domain evidence without benchmark IDs, labels or lookups."""
    if not isinstance(message, str):
        raise TypeError("message must be text")
    trusted, ignored = _trusted(message)
    request, evidence_text, request_offset = _current_request(trusted)
    intent, actions = _intent(request)
    references = _references(evidence_text)
    selected = _selected(references, evidence_text)
    current_refs = [record for record in selected if record["start"] >= request_offset]
    if request_offset and current_refs and not _UNCERTAIN.search(request):
        selected = current_refs
    ids = list(dict.fromkeys(record["value"] for record in selected))
    reasons, reason_records = _reasons(evidence_text)
    amounts, amount_records, calculations, foreign, amount_ambiguity = _amounts(
        evidence_text,
        references,
        intent,
    )
    return {
        "policy_version": POLICY_VERSION,
        "intent": intent,
        "order_ids": ids,
        "reasons": reasons,
        "amounts": amounts,
        "foreign_currency": foreign,
        "references": references,
        "ambiguities": {
            "order_id": len(ids) > 1,
            "reason": len(reasons) > 1,
            "refund_amount": amount_ambiguity,
            "intent": intent == "ambiguous",
        },
        "evidence": {
            "actions": actions,
            "reasons": reason_records,
            "amounts": [dict(record, value=str(record["value"])) for record in amount_records],
            "calculations": [dict(record, result=str(record["result"])) for record in calculations],
            "ignored_untrusted_quotes": ignored,
            "current_request": request,
        },
    }


def rule_outcome(analysis: dict[str, Any]) -> dict[str, Any]:
    """A separately labelled deterministic baseline using extracted evidence."""
    intent = analysis["intent"]
    no_tool = {
        "unsupported": "unsupported_request",
        "informational": "informational_request",
        "none": "no_action_requested",
    }
    if intent in no_tool:
        return {"type": "no_tool", "reason_code": no_tool[intent]}
    if intent == "ambiguous":
        return {
            "type": "clarification",
            "target_tool_name": None,
            "missing_fields": [],
            "reason_code": "ambiguous_intent",
            "question": "Which supported action do you want?",
        }
    missing = []
    if len(analysis["order_ids"]) != 1:
        missing.append("order_id")
    if intent != "get_order_status" and len(analysis["reasons"]) != 1:
        missing.append("reason")
    if intent == "propose_refund" and (
        len(analysis["amounts"]) != 1
        or analysis["amounts"][0] <= 0
        or analysis["ambiguities"].get("refund_amount")
    ):
        missing.append("refund_amount")
    if missing:
        ambiguous = any(analysis["ambiguities"].get(field, False) for field in missing)
        return {
            "type": "clarification",
            "target_tool_name": intent,
            "missing_fields": missing,
            "reason_code": "ambiguous_reference" if ambiguous else "missing_required_information",
            "question": "Please specify " + ", ".join(missing) + ".",
        }
    arguments: dict[str, Any] = {"order_id": analysis["order_ids"][0]}
    if intent != "get_order_status":
        arguments["reason"] = analysis["reasons"][0]
    if intent == "propose_refund":
        arguments["refund_amount"] = float(analysis["amounts"][0])
    return {"type": "tool_call", "tool_name": intent, "arguments": arguments}


def ground_outcome(
    outcome: dict[str, Any],
    analysis: dict[str, Any],
    execute_tools: bool = True,
) -> list[str]:
    """Check a supplied model decision and explain mismatches; never rewrite it."""
    errors = validate_prediction(
        {"example_id": "grounding-check", "outcome": outcome},
        load_tool_registry(),
    )
    if errors or outcome is None:
        return errors or ["No outcome to ground"]
    intent = analysis["intent"]
    no_tool_reasons = {
        "unsupported": "unsupported_request",
        "informational": "informational_request",
        "none": "no_action_requested",
    }
    if outcome["type"] == "no_tool":
        if intent not in no_tool_reasons:
            errors.append("The request seeks a supported action or clarification, not no_tool")
        elif outcome["reason_code"] != no_tool_reasons[intent]:
            errors.append("No-tool reason does not match the requested action evidence")
        return errors
    if outcome["type"] == "clarification":
        if intent in no_tool_reasons:
            return ["The request is informational, unsupported, or withdrawn; no action to clarify"]
        if intent == "ambiguous":
            if outcome["target_tool_name"] is not None:
                errors.append("The action is unresolved; a particular target tool is not supported")
            if outcome["reason_code"] != "ambiguous_intent":
                errors.append("Unresolved action choice requires the ambiguous_intent reason")
            return errors
        if outcome["target_tool_name"] != intent:
            errors.append("Clarification target does not match the explicitly requested action")
        unresolved = set()
        if len(analysis["order_ids"]) != 1:
            unresolved.add("order_id")
        if intent != "get_order_status" and len(analysis["reasons"]) != 1:
            unresolved.add("reason")
        if intent == "propose_refund" and (
            len(analysis["amounts"]) != 1
            or analysis["amounts"][0] <= 0
            or analysis["ambiguities"].get("refund_amount")
        ):
            unresolved.add("refund_amount")
        supplied = set(outcome["missing_fields"])
        if supplied - unresolved:
            errors.append(
                "These fields are already resolved by the request: "
                + ", ".join(sorted(supplied - unresolved))
            )
        if unresolved - supplied:
            errors.append(
                "These required fields remain unresolved: "
                + ", ".join(sorted(unresolved - supplied))
            )
        ambiguous = any(analysis["ambiguities"].get(field, False) for field in unresolved)
        reason = "ambiguous_reference" if ambiguous else "missing_required_information"
        if outcome["reason_code"] != reason:
            errors.append(
                "Clarification reason does not distinguish absent from conflicting values"
            )
        return errors
    if outcome["tool_name"] != intent:
        errors.append("Requested action does not support this tool; no action substitution")
    arguments = outcome["arguments"]
    if len(analysis["order_ids"]) != 1 or arguments["order_id"] not in analysis["order_ids"]:
        errors.append("order_id must match the resolved literal order reference")
    if execute_tools and arguments["order_id"] not in {
        order["order_id"] for order in load_demo_orders()
    }:
        errors.append("order_id is not in the fictional demo order store")
    if outcome["tool_name"] != "get_order_status" and (
        len(analysis["reasons"]) != 1 or arguments["reason"] not in analysis["reasons"]
    ):
        errors.append("reason is not supported by the resolved request evidence")
    if outcome["tool_name"] == "propose_refund":
        if (
            len(analysis["amounts"]) != 1
            or (Decimal(str(arguments["refund_amount"])) not in analysis["amounts"])
            or analysis["ambiguities"].get("refund_amount")
        ):
            errors.append("refund_amount must match explicit or exactly derived monetary evidence")
        if analysis["foreign_currency"]:
            errors.append("Demo proposals use INR only; currency conversion is unsupported")
    return errors
