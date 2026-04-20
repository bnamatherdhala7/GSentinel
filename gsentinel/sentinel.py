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
    }

    graph = build_graph()
    final = graph.invoke(initial_state)

    print("\n" + "=" * 60)
    print(final["action_card"])
    print("=" * 60 + "\n")

    log_path = BASE / "logs/agent_trace.json"
    log_path.write_text(json.dumps(final["trace"], indent=2))
    print(f"Trace written to {log_path}")


if __name__ == "__main__":
    main()
