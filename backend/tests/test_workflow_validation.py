import pytest

from app.workflow.definition import WorkflowDefinition
from app.workflow.validation import validate_workflow_definition


def test_validate_default_minimal_workflow_ok():
    definition = WorkflowDefinition(
        schemaVersion=1,
        nodes=[
            {"id": "start", "type": "start"},
            {"id": "context", "type": "context"},
            {"id": "llm", "type": "llm"},
            {"id": "end", "type": "end"},
        ],
        edges=[
            {"source": "start", "target": "context"},
            {"source": "context", "target": "llm"},
            {"source": "llm", "target": "end"},
        ],
    )

    validated = validate_workflow_definition(definition)
    assert validated.start_node_id == "start"
    assert validated.end_node_id == "end"
    assert validated.llm_node_id == "llm"


def test_validate_reject_cycle():
    definition = WorkflowDefinition(
        schemaVersion=1,
        nodes=[
            {"id": "start", "type": "start"},
            {"id": "llm", "type": "llm"},
            {"id": "end", "type": "end"},
        ],
        edges=[
            {"source": "start", "target": "llm"},
            {"source": "llm", "target": "start"},  # cycle
            {"source": "llm", "target": "end"},
        ],
    )

    with pytest.raises(ValueError, match="DAG"):
        validate_workflow_definition(definition)


def test_validate_reject_non_router_multi_outgoing():
    definition = WorkflowDefinition(
        schemaVersion=1,
        nodes=[
            {"id": "start", "type": "start"},
            {"id": "llm", "type": "llm"},
            {"id": "end", "type": "end"},
        ],
        edges=[
            {"source": "start", "target": "llm"},
            {"source": "start", "target": "end"},  # invalid: start is not router
            {"source": "llm", "target": "end"},
        ],
    )

    with pytest.raises(ValueError, match="必须恰好 1 条出边"):
        validate_workflow_definition(definition)


def test_validate_router_requires_cases_and_uniqueness():
    definition = WorkflowDefinition(
        schemaVersion=1,
        nodes=[
            {"id": "start", "type": "start"},
            {"id": "router", "type": "router", "config": {"strategy": "field", "field": "mode"}},
            {"id": "context", "type": "context"},
            {"id": "llm", "type": "llm"},
            {"id": "end", "type": "end"},
        ],
        edges=[
            {"source": "start", "target": "router"},
            {"source": "router", "target": "context", "case": "with_context"},
            {"source": "router", "target": "llm", "case": "direct"},
            {"source": "context", "target": "llm"},
            {"source": "llm", "target": "end"},
        ],
    )

    validated = validate_workflow_definition(definition)
    assert validated.start_node_id == "start"

    bad = definition.model_copy(deep=True)
    # duplicate case
    bad.edges[1].case = "dup"
    bad.edges[2].case = "dup"
    with pytest.raises(ValueError, match="case 必须唯一"):
        validate_workflow_definition(bad)

