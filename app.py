"""Local Streamlit entry point: run with `streamlit run app.py`."""

from __future__ import annotations

from html import escape
from pathlib import Path

import streamlit as st

from tunebench.dashboard import (
    MODES,
    PRESETS,
    default_model_path,
    historical_reports,
    read_artifact,
    replay_records,
    replay_result,
    report_summary,
)

st.set_page_config(
    page_title="TuneBench · Tool-calling workbench",
    page_icon="↗",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """<style>
    :root { color-scheme: light; }
    .stApp, [data-testid="stAppViewContainer"] { background: #f7f6f2; color: #172734; }
    [data-testid="stHeader"] { background: rgba(247,246,242,.92); }
    [data-testid="stAppDeployButton"], .stDeployButton { display:none; }
    [data-testid="stSidebar"] { background: #efeee9; border-right: 1px solid #dedfd9; }
    .block-container { padding-top: 4.25rem; padding-bottom: 3rem; max-width: 1400px; }
    h1,h2,h3 { color: #142633; letter-spacing: -.035em; }
    h1 { font-weight: 650 !important; font-size: 3.35rem !important; line-height: 1.05 !important; }
    h2 { font-size: 1.85rem !important; } h3 { font-size: 1.15rem !important; }
    p, li, label { color: #344955; }
    [data-testid="stCaptionContainer"] p { color: #61717b; }
    .eyebrow { font-size: .71rem; font-weight: 750; letter-spacing: .16em; color: #245cde;
      margin-bottom: .85rem; }
    .intro { font-size: 1.08rem; color: #586a76; line-height: 1.65; max-width: 700px; }
    .brand { display:flex; align-items:center; gap:.7rem; margin: .7rem 0 1.6rem; }
    .brand-mark { color:white; background:#245cde; border-radius:12px; padding:11px 10px;
      font-size:1rem; font-weight:800; letter-spacing:-.03em; }
    .brand-name { font-size:1.25rem; font-weight:750; color:#172734; letter-spacing:-.04em; }
    .side-note { font-size:.8rem; line-height:1.6; color:#64737b; margin-bottom:1.5rem; }
    .hero-note { background:#eaf0fe; border:1px solid #d5dffa; color:#284779; border-radius:16px;
      padding:1.15rem 1.25rem; font-size:.9rem; line-height:1.6; margin-top: .4rem; }
    .hero-note strong { display:block; margin-bottom:.35rem; font-size:1rem; color:#173877; }
    [data-testid="stTabs"] { margin-top:1.25rem; }
    button[data-baseweb="tab"] { font-size:.95rem; padding: .85rem 1.2rem; }
    button[data-baseweb="tab"][aria-selected="true"] { color:#245cde; }
    [data-baseweb="tab-highlight"] { background:#245cde; }
    .stButton button[kind="primary"] { background:#245cde; border-color:#245cde;
      border-radius:9px; }
    .stButton button[kind="primary"], .stButton button[kind="primary"] p,
    .stButton button[kind="primary"] span { color:#fff !important; }
    .stButton button { border-radius:9px; }
    [data-testid="stVerticalBlockBorderWrapper"] > div { border-color:#dde1de !important;
      border-radius:14px !important; }
    [data-testid="stMetricValue"] { font-size:2.1rem; letter-spacing:-.04em; color:#172734; }
    .result-label { color:#245cde; font-size:.72rem; font-weight:750; letter-spacing:.11em;
      text-transform:uppercase; margin: .1rem 0 .5rem; }
    .result-title { color:#142633; font-size:1.5rem; letter-spacing:-.035em;
      font-weight:650; line-height:1.25; margin-bottom:.65rem; }
    .step { border-top:2px solid #d8e0ef; padding-top:.7rem; margin:.4rem 0 1rem; }
    .step b { display:block; color:#245cde; font-size:.7rem; letter-spacing:.12em;
      margin-bottom:.5rem; }
    .step span { color:#172734; font-size:1.05rem; font-weight:650; }
    [data-testid="stTextArea"] textarea { background:#fff; color:#172734; line-height:1.7; }
    [data-testid="stTextInput"] input { background:#fff; color:#172734; }
    @media (max-width: 640px) {
      .block-container { padding-left:1.2rem; padding-right:1.2rem; }
      h1 { font-size:2.5rem !important; }
    }
    </style>""",
    unsafe_allow_html=True,
)


def choose_preset() -> None:
    st.session_state["request_text"] = PRESETS[st.session_state["preset"]]


def show_result(result: dict, mode: str) -> None:
    status = result.get("status", "error")
    outcome = result.get("outcome")
    titles = {
        "executed": "A tool ran in the simulation",
        "clarification": "A little more information is needed",
        "no_tool": "No tool is needed",
        "blocked": "Execution stopped at a guardrail",
        "error": "The request could not run",
        "recorded": "An original model response",
    }
    st.markdown('<div class="result-label">DECISION TRACE</div>', unsafe_allow_html=True)
    st.markdown(
        f'<div class="result-title">{escape(titles.get(status, status))}</div>',
        unsafe_allow_html=True,
    )
    timing_label = "recorded generation time" if status == "recorded" else "elapsed"
    st.caption(f"{mode} · {result.get('elapsed_ms', 0) / 1000:.2f}s {timing_label} · {status}")
    if result.get("user_message"):
        if status in {"blocked", "error"}:
            st.warning(result["user_message"])
        else:
            st.info(result["user_message"])
    if status == "clarification":
        st.caption(
            "Add the missing details to the full request and run it again. "
            "This workbench handles one complete request at a time."
        )
    if outcome:
        label = outcome.get("type", "unrecognized") if isinstance(outcome, dict) else "invalid"
        st.markdown(f"**Decision:** `{label}`")
        if isinstance(outcome, dict) and outcome.get("type") == "tool_call":
            st.markdown(f"**Tool:** `{outcome.get('tool_name', 'unknown')}`")
            st.json(outcome.get("arguments", {}), expanded=True)
        else:
            st.json(outcome, expanded=True)
    errors = result.get("validation_errors") or []
    if errors:
        st.error("The response did not pass validation. It was not accepted for execution.")
        for error in errors:
            st.caption(str(error))
    elif outcome:
        st.success("Output contract passed")
    if result.get("tool_result") is not None:
        st.markdown("**Simulated tool result**")
        st.json(result["tool_result"], expanded=True)
    with st.expander("Raw responses & validation trace", expanded=False):
        st.caption("Original response text is preserved. Each attempt and its errors are visible.")
        for index, attempt in enumerate(result.get("attempts") or [], 1):
            st.markdown(f"**Attempt {index}**")
            st.code(attempt.get("raw_output", ""), language="json", wrap_lines=True)
            attempt_errors = attempt.get("validation_errors") or attempt.get("errors") or []
            if attempt_errors:
                st.json(attempt_errors)
        st.caption("Submitted request")
        st.code(result.get("input", ""), language=None, wrap_lines=True)


def metric_row(summary: dict) -> None:
    total = summary["examples"]
    for column, (label, key) in zip(
        st.columns(3),
        [
            ("Full success", "strict_correct"),
            ("Right outcome", "outcome_correct"),
            ("Valid output", "valid_predictions"),
        ],
        strict=True,
    ):
        with column:
            st.metric(label, f"{summary[key]}/{total}")


with st.sidebar:
    st.markdown(
        '<div class="brand"><span class="brand-mark">TB↗</span>'
        '<span class="brand-name">TuneBench</span></div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="side-note">A small workbench for reliable<br>tool-calling decisions.</div>',
        unsafe_allow_html=True,
    )
    st.markdown("**A safe place to experiment**")
    st.caption("Synthetic orders. Simulated tools. No real payments or customer data.")
    st.divider()
    st.markdown("**Demo order book**")
    try:
        from tunebench.mock_tools import load_demo_orders, load_demo_policy

        orders = load_demo_orders()
        for order in orders:
            order_id = order.get("order_id", order.get("id", "Order"))
            order_status = order.get("status", "")
            st.markdown(f"`{order_id}` · {order_status}")
        with st.expander("Inspect simulated records"):
            st.json(orders, expanded=False)
        policy = load_demo_policy()
        st.caption(f"Repeatable policy date: {policy['as_of']} · version {policy['version']}")
        with st.expander("Read the demo refund policy"):
            for rule in policy["rules"]:
                st.caption(rule)
    except ImportError:
        st.caption("The mock tool module is not installed in this checkout.")
    st.divider()
    st.caption("LOCAL-FIRST · ONE DECISION PER REQUEST")
    st.caption("Live Qwen runs on your machine. CPU responses can take a minute or longer.")

hero, note = st.columns([2.1, 1], gap="large")
with hero:
    st.markdown('<div class="eyebrow">GENAI ENGINEERING WORKBENCH</div>', unsafe_allow_html=True)
    st.title("One request.\nThe right next action.")
    st.markdown(
        '<div class="intro">Choose a tool, ask for missing details, or leave tools alone. '
        "See the decision, validation, and simulated result in one place.</div>",
        unsafe_allow_html=True,
    )
with note:
    st.markdown(
        '<div class="hero-note"><strong>Tool-calling workbench</strong>'
        "Three decisions. Three mock tools.<br>"
        "A clear trail from input to outcome.<br><br>"
        "Start with the instant deterministic demo, or inspect a real model response.</div>",
        unsafe_allow_html=True,
    )

playground, evaluation, project = st.tabs(["Playground", "Evaluation", "Project"])

with playground:
    st.write("")
    left, right = st.columns([1.08, 1], gap="large")
    with left:
        st.subheader("Try a request")
        mode = st.selectbox("Run mode", MODES, key="run_mode")
        model_path = ""
        selected_record = None
        if mode == "Saved model replay":
            st.info("Recorded Qwen output · fixed historical inputs · no new inference or tool run")
            records = replay_records()
            if records:
                selected_index = st.selectbox(
                    "Recorded example",
                    list(range(len(records))),
                    format_func=lambda i: f"{i + 1:02d} · {records[i]['task']['prompt'][:82]}",
                    key="replay_index",
                )
                selected_record = records[selected_index]
                request = selected_record["task"]["prompt"]
                st.text_area("Recorded request", request, height=155, disabled=True)
                st.caption(
                    "Historical synthetic IDs are separate from the current demo order book."
                )
            else:
                request = ""
                st.warning("Saved model artifacts are unavailable in this checkout.")
        else:
            if mode == "Quick demo":
                st.caption("Deterministic rules baseline · instant · this mode does not use an LLM")
            else:
                st.caption(
                    "Real Qwen model · CPU · constrained JSON · at most one validation retry"
                )
                model_path = st.text_input(
                    "Local model directory", value=default_model_path(), key="model_path"
                )
                st.caption(
                    "An existing downloaded snapshot is required. This app never downloads models."
                )
            st.selectbox(
                "Start with an example", list(PRESETS), key="preset", on_change=choose_preset
            )
            if "request_text" not in st.session_state:
                st.session_state["request_text"] = next(iter(PRESETS.values()))
            request = st.text_area(
                "Your request",
                key="request_text",
                height=155,
                max_chars=4000,
                placeholder="For example: check the status of order TB-1001.",
            )
        invalid = not request.strip() or len(request) > 4000
        if len(request) > 4000:
            st.error("Please keep the request within 4,000 characters.")
        missing_model = mode == "Live local Qwen" and not Path(model_path).is_dir()
        if mode == "Live local Qwen" and (not model_path or missing_model):
            st.warning("Choose an existing local model directory before running Qwen.")
            missing_model = True
        run = st.button(
            "View recorded response" if mode == "Saved model replay" else "Run request →",
            type="primary",
            key="run_request",
            use_container_width=True,
            disabled=invalid or missing_model,
        )
        st.caption("Everything stays in the simulation. A refund proposal never moves money.")
        if run:
            if mode == "Saved model replay" and selected_record:
                result = replay_result(selected_record)
            else:
                from tunebench.assistant import respond

                with st.spinner(
                    "Running the local model…"
                    if mode == "Live local Qwen"
                    else "Deciding and validating…"
                ):
                    try:
                        result = respond(
                            request.strip(),
                            backend="model" if mode == "Live local Qwen" else "rules",
                            model_path=model_path or None,
                            max_repairs=1,
                        )
                    except Exception as exc:
                        result = {
                            "status": "error",
                            "backend": mode,
                            "input": request,
                            "user_message": (
                                "The request could not run. Check the local setup and try again."
                            ),
                            "validation_errors": [type(exc).__name__],
                            "attempts": [],
                        }
            st.session_state["last_result"] = result
            st.session_state["last_result_mode"] = mode
    with right:
        with st.container(border=True):
            if "last_result" in st.session_state:
                show_result(st.session_state["last_result"], st.session_state["last_result_mode"])
            else:
                st.markdown(
                    '<div class="result-label">YOUR RESULT WILL APPEAR HERE</div>',
                    unsafe_allow_html=True,
                )
                st.subheader("A decision you can inspect")
                st.write("Run a sample to follow the full path from request to validated outcome.")
                st.markdown(
                    "1. **Decide** — tool call, clarification, or no tool.\n"
                    "2. **Validate** — check the schema and required arguments.\n"
                    "3. **Simulate** — run a supported action on the demo orders."
                )
                st.caption("Quick demo is a rules baseline. It does not measure model quality.")

with evaluation:
    st.write("")
    st.subheader("Evidence, with the context attached")
    st.write("Actual saved model runs. Deterministic demo scores are kept separate.")
    versions = read_artifact("artifacts/portfolio-version-comparison/comparison.json")
    if versions:
        st.markdown("**System comparison · the same 20 fresh test questions**")
        st.caption(
            "Both versions use the same Qwen weights on CPU. v0.4 changes the prompt, "
            "JSON constraints, grounding checks and repair feedback."
        )
        for stage, label in (("raw-first", "Raw first answer"), ("final", "Accepted final answer")):
            st.markdown(f"**{label}**")
            for column, (key, title) in zip(
                st.columns(2), [("legacy", "v0.3"), ("candidate", "v0.4")], strict=True
            ):
                report = read_artifact(
                    f"artifacts/portfolio-version-comparison/{key}/{stage}.report.json"
                )
                if report:
                    with column, st.container(border=True):
                        st.markdown(f"**{title}**")
                        metric_row(report_summary(report))
        st.caption(
            "Final answers include validation and at most one repair; blocked cases count "
            "as failures. These are small, assistant-authored test data. No tool executed "
            "during scoring, and no weights were trained."
        )
        st.divider()
    reports = historical_reports()
    if reports["strong"] and reports["strong-v2"]:
        st.markdown("**A paired prompt experiment · the same 12 development cases**")
        for column, (key, label) in zip(
            st.columns(2), [("strong", "Legacy strong"), ("strong-v2", "Strong v2")], strict=True
        ):
            with column, st.container(border=True):
                st.markdown(f"**{label}**")
                metric_row(report_summary(reports[key]))
        st.info(
            "Four improvements, one regression. These are 12 targeted development cases, "
            "not a representative or untouched final test. Both use the same base model; "
            "no weights were trained."
        )
        comparison = reports.get("comparison")
        if comparison:
            interval = comparison["cluster_bootstrap_95_percent_interval"]
            st.caption(
                f"Strict-success difference: {comparison['accuracy_delta']:+.0%} points. "
                f"Descriptive interval: {interval[0]:+.1%} to {interval[1]:+.1%}; "
                "it includes zero. This does not establish general improvement."
            )
    if reports["smoke"]:
        with st.expander("Earlier smoke run · 20 different examples", expanded=False):
            st.markdown("**Initial strong prompt · real Qwen CPU run**")
            metric_row(report_summary(reports["smoke"]))
            st.caption(
                "This 7/20 result uses different questions. Compare the paired 12-case "
                "runs with each other; do not interpret 7/20 to 5/12 as improvement."
            )
    portfolio = read_artifact("artifacts/portfolio-evaluation/summary.json")
    if portfolio and portfolio.get("results"):
        st.divider()
        st.markdown(f"**{portfolio.get('title', 'Portfolio evaluation')}**")
        st.caption(portfolio.get("dataset_label", "Separate reviewed portfolio dataset"))
        for row in portfolio["results"]:
            with st.container(border=True):
                st.markdown(f"**{row['label']}** · {row.get('backend', 'recorded run')}")
                metric_row(row)
        for limitation in portfolio.get("limitations", []):
            st.caption(limitation)
    with st.expander("How to read these metrics"):
        st.markdown(
            "**Full success** requires the correct decision and all its required details. "
            "**Right outcome** checks only tool call / clarification / no tool. "
            "**Valid output** checks the response contract; valid JSON can still be wrong."
        )
        st.caption(
            "Raw outputs, model revision, prompt hashes, decoding settings, and "
            "per-example failures are retained under artifacts/."
        )

with project:
    st.write("")
    st.subheader("A small system, built all the way through")
    st.write(
        "TuneBench connects a model decision to something you can validate, measure, and inspect."
    )
    for column, number, title in zip(
        st.columns(4),
        ["01", "02", "03", "04"],
        ["User request", "Model or rules", "Schema + policy", "Mock tool result"],
        strict=True,
    ):
        with column:
            st.markdown(
                f'<div class="step"><b>{number}</b><span>{title}</span></div>',
                unsafe_allow_html=True,
            )
    first, second = st.columns(2, gap="large")
    with first:
        st.markdown("**What is implemented**")
        st.markdown(
            "- Three outcome contracts and a canonical tool registry.\n"
            "- Strict parsing, validation, and raw-response capture.\n"
            "- Deterministic simulated order tools.\n"
            "- Real local Qwen inference and versioned prompts.\n"
            "- Repeatable evaluation, tests, and continuous integration."
        )
    with second:
        st.markdown("**Where the boundaries are**")
        st.markdown(
            "- Orders are synthetic; no external accounts or payments.\n"
            "- Quick demo is rules, not a language model.\n"
            "- Replay is recorded output, not live inference.\n"
            "- Small development scores do not prove generalization.\n"
            "- GPU fine-tuning has not been run; no trained adapter is claimed."
        )
    st.divider()
    st.markdown("**Explore the engineering**")
    st.code(
        "bash scripts/setup.sh --app\nbash scripts/check.sh\nbash scripts/start_demo.sh",
        language="bash",
    )
    st.caption(
        "Start with README.md; inspect docs/model-workflow.md, docs/dataset.md, "
        "and the preserved experiment artifacts for the decisions and limitations."
    )
