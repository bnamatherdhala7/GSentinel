import json
from pathlib import Path
from langgraph.graph import StateGraph, END
from graph.state import FulfillmentState
from graph.nodes import parser_node, healer_node, critic_node, messenger_node

BASE = Path(__file__).parent


def route_after_critic(state: dict) -> str:
    return "messenger"


def build_graph():
    g = StateGraph(FulfillmentState)
    g.add_node("parser", parser_node)
    g.add_node("healer", healer_node)
    g.add_node("critic", critic_node)
    g.add_node("messenger", messenger_node)

    g.set_entry_point("parser")
    g.add_edge("parser", "healer")
    g.add_edge("healer", "critic")
    g.add_conditional_edges("critic", route_after_critic, {"messenger": "messenger"})
    g.add_edge("messenger", END)
    return g.compile()


def build_compliance_report(state: dict) -> str:
    critic_entry = next(
        (t for t in reversed(state["trace"]) if t.get("node") == "critic"), {}
    )
    healer_entry = next(
        (t for t in reversed(state["trace"]) if t.get("node") == "healer"), {}
    )
    latency = state.get("latency_ms", {})
    total_ms = sum(latency.values())

    lines = [
        "=" * 60,
        "  SAFETY & COMPLIANCE REPORT",
        "=" * 60,
        f"  Node latencies:",
        f"    Parser   : {latency.get('parser', '?')}ms  (includes RAG lookup + 500ms think)",
        f"    Healer   : {latency.get('healer', '?')}ms  (includes DB scan + 500ms think)",
        f"    Critic   : {latency.get('critic', '?')}ms  (3-check compliance guard)",
        f"    Messenger: {latency.get('messenger', '?')}ms",
        f"    Total    : {total_ms}ms",
        "",
        f"  DB search depth  : {len(healer_entry.get('search_depth', []))} record(s) scanned",
        f"  Mismatch log     : {healer_entry.get('mismatch_log', 'n/a')}",
        "",
        f"  Compliance checks: {critic_entry.get('checks_passed', '?')}/{critic_entry.get('checks_total', 3)} passed",
    ]
    for entry in critic_entry.get("validation_log", []):
        lines.append(f"    {entry}")
    lines += [
        "",
        f"  KB evidence      : {len(state.get('kb_evidence', ''))} chars from carrier_errors.md",
        f"  Reasoning steps  : {len(state.get('reasoning_path', []))} node(s) logged",
        "=" * 60,
    ]
    return "\n".join(lines)


def main():
    raw = (BASE / "mocks/carrier_logs/sample_error.txt").read_text()

    initial_state: FulfillmentState = {
        "raw_input": raw,
        "employee_id": None,
        "error_code": None,
        "error_description": None,
        "field_affected": None,
        "submitted_value": None,
        "corrected_value": None,
        "confidence_score": 0.0,
        "action_card": None,
        "status": None,
        "trace": [],
        "latency_ms": {},
        "kb_evidence": "",
        "reasoning_path": [],
    }

    graph = build_graph()
    final = graph.invoke(initial_state)

    print("\n" + "=" * 60)
    print(final["action_card"])
    print()
    print(build_compliance_report(final))

    print("\n  REASONING PATH:")
    for step in final.get("reasoning_path", []):
        print(f"  {step}")
    print()

    log_path = BASE / "logs/agent_trace.json"
    log_path.write_text(json.dumps(final["trace"], indent=2))
    print(f"  Trace written → {log_path}\n")


if __name__ == "__main__":
    main()
