"""Deterministic synthetic candidates and structural dataset quality gates.

Generated data is intentionally marked as synthetic and is never automatically frozen.
Difficulty follows the reasoning in each template, not a desired distribution.
"""

import hashlib
import json
import random
import re
from collections import Counter
from copy import deepcopy
from typing import Any

from tunebench.contracts import load_tool_registry, validate_task

GENERATOR_VERSION = "0.1.0"
OUTCOMES = ("tool_call", "clarification", "no_tool")

# In the revised blueprint, family order determines its exact allocation.
FAMILIES = {
    "train": [
        ("TR_STATUS_EXPLICIT", 167),
        ("TR_ELIGIBILITY_EXPLICIT", 167),
        ("TR_REFUND_EXPLICIT", 166),
        ("TR_STATUS_MISSING_ID", 84),
        ("TR_ELIGIBILITY_MISSING_REASON", 83),
        ("TR_REFUND_MISSING_AMOUNT", 83),
        ("TR_POLICY_EXPLANATION", 63),
        ("TR_DELIVERY_ETA", 63),
        ("TR_UNSUPPORTED_CANCEL", 62),
        ("TR_PRODUCT_QUESTION", 62),
    ],
    "validation": [
        ("VA_STATUS_REFERENCE_SELECTION", 21),
        ("VA_ELIGIBILITY_WRONG_ITEM", 21),
        ("VA_REFUND_FULL", 21),
        ("VA_STATUS_AMBIGUOUS", 11),
        ("VA_ELIGIBILITY_REASON_AMBIGUOUS", 10),
        ("VA_REFUND_AMOUNT_AMBIGUOUS", 10),
        ("VA_POLICY_COMPARISON", 8),
        ("VA_HYPOTHETICAL_REFUND", 8),
        ("VA_ACCOUNT_INFO", 8),
        ("VA_SUPPORT_CONTACT", 7),
    ],
    "test": [
        ("TE_STATUS_CROSS_TURN_REFERENCE", 21),
        ("TE_ELIGIBILITY_CONTEXT_REASON", 21),
        ("TE_REFUND_DERIVED_AMOUNT", 20),
        ("TE_STATUS_CROSS_TURN_CONFLICT", 11),
        ("TE_ELIGIBILITY_CORRECTION_CONFLICT", 10),
        ("TE_REFUND_DERIVATION_CONFLICT", 10),
        ("TE_PRODUCT_RECOMMENDATION", 8),
        ("TE_REAL_REFUND_EXECUTION", 8),
        ("TE_STATUS_MEANING", 8),
        ("TE_OUT_OF_SCOPE_ACTION", 8),
    ],
}

# The proposed matrix is retained for comparison; it does not override truthful labels.
PROPOSED_DIFFICULTY = {
    "train": {"easy": 300, "medium": 450, "hard": 250},
    "validation": {"easy": 38, "medium": 56, "hard": 31},
    "test": {"easy": 37, "medium": 57, "hard": 31},
}


def _seed(seed: int) -> None:
    if isinstance(seed, bool) or not isinstance(seed, int) or seed < 0:
        raise ValueError("seed must be a nonnegative integer")


def _call(name: str, **arguments: Any) -> dict[str, Any]:
    return {"type": "tool_call", "tool_name": name, "arguments": arguments}


def _clarify(name: str, field: str, ambiguous: bool = False) -> dict[str, Any]:
    return {
        "type": "clarification",
        "target_tool_name": name,
        "missing_fields": [field],
        "reason_code": "ambiguous_reference" if ambiguous else "missing_required_information",
    }


def _template(family: str, i: int, rng: random.Random) -> tuple[str, dict[str, Any], str]:
    """Return a prompt, gold outcome, and defensible template-level difficulty."""
    order = f"{rng.choice('ABCDEFGHJKLMNPRSTUVWXYZ')}{rng.randrange(100000, 999999)}"
    other = f"X{rng.randrange(100000, 999999)}"
    while other == order:
        other = f"X{rng.randrange(100000, 999999)}"
    cents = rng.randrange(100, 20000)
    amount = cents / 100
    second = (cents + rng.randrange(100, 5000)) / 100
    product = rng.choice(("ceramic mug", "desk lamp", "linen shirt", "headphones", "backpack"))
    context = f"For context, my reference is {order} and the product is a {product}. "
    label = family.split("_", 1)[1]
    if label == "STATUS_EXPLICIT":
        texts = (
            f"Check the current status of order {order}.",
            f"Where is my order {order}? Retrieve its status.",
            f"Please look up order {order}'s current status.",
        )
        return texts[i % len(texts)], _call("get_order_status", order_id=order), "easy"
    if label == "ELIGIBILITY_EXPLICIT":
        return (
            f"My {product} for order {order} arrived damaged. Check refund eligibility.",
            _call("check_refund_eligibility", order_id=order, reason="damaged_item"),
            "easy",
        )
    if label == "REFUND_EXPLICIT":
        return (
            f"For order {order}, the {product} was damaged. Create a simulated partial refund "
            f"proposal for exactly {amount:.2f}; do not execute a real refund.",
            _call("propose_refund", order_id=order, refund_amount=amount, reason="damaged_item"),
            "easy",
        )
    if label == "STATUS_MISSING_ID":
        return (
            f"Check the status of my {product} order. I have not provided its order ID "
            f"(support reference {order} is not an order ID).",
            _clarify("get_order_status", "order_id"),
            "medium",
        )
    if label == "ELIGIBILITY_MISSING_REASON":
        return (
            f"Check refund eligibility for order {order}, containing a {product}. "
            "I have not explained why I want a refund.",
            _clarify("check_refund_eligibility", "reason"),
            "medium",
        )
    if label == "REFUND_MISSING_AMOUNT":
        return (
            f"Create a simulated refund proposal for damaged {product} in order {order}. "
            "I have not chosen an amount; do not infer the amount from the order total.",
            _clarify("propose_refund", "refund_amount"),
            "medium",
        )
    if label == "STATUS_REFERENCE_SELECTION":
        return (
            f"I have orders {other} and {order}. Ignore {other}; check the current status "
            f"of {order}, the {product} order.",
            _call("get_order_status", order_id=order),
            "medium",
        )
    if label == "ELIGIBILITY_WRONG_ITEM":
        return (
            f"Order {order} should contain a {product}, but a completely different item "
            "was delivered. Check whether it qualifies for a refund.",
            _call("check_refund_eligibility", order_id=order, reason="wrong_item"),
            "easy",
        )
    if label == "REFUND_FULL":
        return (
            f"The wrong item arrived for order {order}. I want a simulated full refund "
            f"proposal of exactly {amount:.2f}. The old order {other} is unrelated.",
            _call("propose_refund", order_id=order, refund_amount=amount, reason="wrong_item"),
            "medium",
        )
    if label == "STATUS_AMBIGUOUS":
        return (
            f"I bought a {product} in one of orders {order} or {other}. "
            "Check that order's status; I cannot tell you which order contains it.",
            _clarify("get_order_status", "order_id", True),
            "hard",
        )
    if label == "ELIGIBILITY_REASON_AMBIGUOUS":
        return (
            f"Check refund eligibility for order {order}. The support note says damaged "
            f"{product}; another equally current note says item not received. Neither "
            "note is authoritative and I cannot choose between them.",
            _clarify("check_refund_eligibility", "reason", True),
            "hard",
        )
    if label == "REFUND_AMOUNT_AMBIGUOUS":
        return (
            f"For order {order}, the {product} arrived damaged. Prepare a simulated refund "
            f"proposal. I have two unresolved requested amounts, {amount:.2f} and "
            f"{second:.2f}, and neither supersedes the other.",
            _clarify("propose_refund", "refund_amount", True),
            "hard",
        )
    if label == "STATUS_CROSS_TURN_REFERENCE":
        return (
            f"Earlier user: My {product} belongs to order {order}.\n"
            "Current user: Please retrieve the current status of that same order.",
            _call("get_order_status", order_id=order),
            "medium",
        )
    if label == "ELIGIBILITY_CONTEXT_REASON":
        return (
            f"Earlier user: The {product} for order {order} has never arrived.\n"
            "Agent: Would you like an eligibility check?\n"
            "Current user: Yes, check refund eligibility for that issue.",
            _call("check_refund_eligibility", order_id=order, reason="not_received"),
            "hard",
        )
    if label == "REFUND_DERIVED_AMOUNT":
        unit_cents = rng.randrange(100, 5000)
        quantity = rng.randrange(2, 6)
        return (
            f"Order {order} contains {quantity} damaged units of a {product}, each priced "
            f"at {unit_cents / 100:.2f}. Create a simulated refund proposal for their "
            "combined price, without fees or tax; do not execute any transaction.",
            _call(
                "propose_refund",
                order_id=order,
                refund_amount=unit_cents * quantity / 100,
                reason="damaged_item",
            ),
            "hard",
        )
    if label == "STATUS_CROSS_TURN_CONFLICT":
        return (
            f"Earlier user: My {product} may be in order {order}.\n"
            f"Later user: It may instead be in {other}; I have not checked.\n"
            "Current user: Get its order status. Neither reference is confirmed.",
            _clarify("get_order_status", "order_id", True),
            "hard",
        )
    if label == "ELIGIBILITY_CORRECTION_CONFLICT":
        return (
            f"Earlier user: Order {order}'s {product} was damaged.\n"
            "Current user: That description may be wrong: it might be the wrong item "
            "instead. Neither reason is confirmed. Check refund eligibility.",
            _clarify("check_refund_eligibility", "reason", True),
            "hard",
        )
    if label == "REFUND_DERIVATION_CONFLICT":
        return (
            f"Order {order} contains a damaged {product}. I request a simulated refund "
            f"proposal. The requested total is listed as {amount:.2f} in one record and "
            f"{second:.2f} in another. Both are equally current; no rule resolves them.",
            _clarify("propose_refund", "refund_amount", True),
            "hard",
        )

    informational = {
        "POLICY_EXPLANATION": (
            "Explain what a refund policy generally covers; do not check my order."
        ),
        "DELIVERY_ETA": "Explain typical delivery-time ranges in general; do not look up my order.",
        "PRODUCT_QUESTION": f"What materials are commonly used to make a {product}?",
        "POLICY_COMPARISON": "Compare return windows and refund processing times in general.",
        "HYPOTHETICAL_REFUND": "Hypothetically, what documents might a refund request need? "
        "Do not check an order or create a proposal.",
        "SUPPORT_CONTACT": "Explain how I could find customer-support contact information.",
        "PRODUCT_RECOMMENDATION": f"Recommend features to consider when choosing a {product}.",
        "STATUS_MEANING": "The status is already known to be 'shipped'. Explain what that "
        "word means, without retrieving a new status.",
    }
    unsupported = {
        "UNSUPPORTED_CANCEL": "Cancel this order now. I am not asking for its status or a refund.",
        "ACCOUNT_INFO": "Retrieve the email address on my customer account.",
        "REAL_REFUND_EXECUTION": f"Actually send {amount:.2f} back to my bank account now. "
        "A simulated refund proposal is not what I request.",
        "OUT_OF_SCOPE_ACTION": "Change my account password and shipping address.",
    }
    if label in informational:
        return (
            context + informational[label],
            {"type": "no_tool", "reason_code": "informational_request"},
            "medium" if label in {"HYPOTHETICAL_REFUND", "STATUS_MEANING"} else "easy",
        )
    if label in unsupported:
        return (
            context + unsupported[label],
            {"type": "no_tool", "reason_code": "unsupported_request"},
            "medium",
        )
    raise ValueError(f"Unknown family: {family}")


def _record(family: str, split: str, i: int, seed: int, tools: list[dict]) -> dict:
    rng = random.Random(f"tunebench:{GENERATOR_VERSION}:{seed}:{family}:{i}")
    prompt, outcome, difficulty = _template(family, i, rng)
    signature = json.dumps([prompt, outcome], sort_keys=True, ensure_ascii=False)
    scenario = hashlib.sha256(signature.encode()).hexdigest()[:24]
    record = {
        "schema_version": "3.0.0",
        "example_id": f"{family}-{i:04d}",
        "family_id": family,
        "scenario_id": f"scenario-{scenario}",
        "split": split,
        "difficulty": difficulty,
        "prompt": prompt,
        "tools": deepcopy(tools),
        "expected_outcome": outcome,
        "provenance": {
            "source_type": "synthetic",
            "generator": "tunebench.dataset",
            "generator_version": GENERATOR_VERSION,
            "seed": seed,
            "template_id": family,
            "source_reference": "TuneBench revised 30-family blueprint; candidate, not reviewed",
        },
    }
    return record


def generate_smoke(seed: int = 42) -> list[dict[str, Any]]:
    """Create 20 smoke tasks (10 calls, 5 clarifications, 5 no-tool decisions)."""
    _seed(seed)
    counts = (4, 3, 3, 2, 2, 1, 2, 1, 1, 1)
    tools = load_tool_registry()
    records = [
        _record("SM_" + family.split("_", 1)[1], "smoke", i, seed, tools)
        for (family, _), count in zip(FAMILIES["train"], counts, strict=True)
        for i in range(count)
    ]
    audit_dataset({"smoke": records})
    return records


def generate_dataset(seed: int = 42) -> dict[str, list[dict[str, Any]]]:
    """Create the 1,250-example *candidate* dataset; never freezes a test set."""
    _seed(seed)
    tools = load_tool_registry()
    splits = {
        split: [
            _record(family, split, i, seed, tools)
            for family, count in families
            for i in range(count)
        ]
        for split, families in FAMILIES.items()
    }
    audit_dataset(splits)
    return splits


def audit_dataset(splits: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    """Reject invalid tasks and cross-split leakage, reporting counts and limitations.

    This is a structural audit, not a semantic label or near-duplicate certification.
    Repeated normalized templates are reported for review rather than silently accepted
    as independent reasoning patterns.
    """
    if not isinstance(splits, dict) or not splits:
        raise ValueError("Provide at least one named dataset split")
    ids: set[str] = set()
    prompts: set[str] = set()
    scenarios: dict[str, str] = {}
    families: dict[str, str] = {}
    family_outcomes: dict[str, str] = {}
    summaries = {}
    for split, records in splits.items():
        if split not in {"train", "validation", "test", "smoke"}:
            raise ValueError(f"Unknown split {split!r}")
        if not records:
            raise ValueError(f"Split {split!r} has no tasks")
        outcomes: Counter = Counter()
        difficulty: Counter = Counter()
        family_counts: Counter = Counter()
        template_shapes: Counter = Counter()
        scenario_counts: Counter = Counter()
        for record in records:
            errors = validate_task(record)
            if errors:
                raise ValueError(f"Invalid task: {errors}")
            if record["split"] != split:
                raise ValueError(f"Task split mismatch for {record['example_id']}")
            example = record["example_id"]
            if example in ids:
                raise ValueError(f"Duplicate example_id: {example}")
            ids.add(example)
            normalized = " ".join(record["prompt"].casefold().split())
            if normalized in prompts:
                raise ValueError(f"Duplicate prompt: {example}")
            prompts.add(normalized)
            scenario = record["scenario_id"]
            if scenario in scenarios and scenarios[scenario] != split:
                raise ValueError(f"Scenario leakage: {scenario}")
            scenarios[scenario] = split
            scenario_counts[scenario] += 1
            if scenario_counts[scenario] > 2:
                raise ValueError(f"More than two examples per scenario: {scenario}")
            family = record["family_id"]
            if family in families and families[family] != split:
                raise ValueError(f"Family leakage: {family}")
            families[family] = split
            outcome = record["expected_outcome"]["type"]
            if family in family_outcomes and family_outcomes[family] != outcome:
                raise ValueError(f"Mixed outcomes in family: {family}")
            family_outcomes[family] = outcome
            family_counts[family] += 1
            outcomes[outcome] += 1
            difficulty[record["difficulty"]] += 1
            # Heuristic surfaces identifier/amount-only substitutions for human review.
            shape = re.sub(r"\b[a-z]*\d+(?:\.\d+)?\b", "<value>", normalized)
            template_shapes[shape] += 1
        if split == "test" and len(records) >= 50 and len(scenario_counts) < 50:
            raise ValueError("Test requires at least 50 distinct scenarios")
        summaries[split] = {
            "examples": len(records),
            "outcomes": dict(sorted(outcomes.items())),
            "difficulty": dict(sorted(difficulty.items())),
            "families": dict(sorted(family_counts.items())),
            "distinct_scenarios": len(scenario_counts),
            "max_examples_per_scenario": max(scenario_counts.values()),
            "repeated_normalized_template_groups": sum(n > 1 for n in template_shapes.values()),
            "proposed_difficulty_target": PROPOSED_DIFFICULTY.get(split),
            "difficulty_target_met": (
                dict(difficulty) == PROPOSED_DIFFICULTY[split]
                if split in PROPOSED_DIFFICULTY
                else None
            ),
        }
    return {
        "status": "structural_checks_passed",
        "dataset_status": "candidate_unreviewed",
        "generator_version": GENERATOR_VERSION,
        "total_examples": len(ids),
        "splits": summaries,
        "warnings": [
            "Synthetic candidates require independent gold-label and near-duplicate review.",
            "Difficulty follows template reasoning; proposed difficulty quotas are not forced.",
            "Family-disjoint IDs do not prove semantic independence of templates.",
            "No test freeze or model-quality claim is implied by this audit.",
        ],
    }
