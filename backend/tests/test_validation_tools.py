"""Validation tool unit tests."""

import json

from app.agents.tools.validation_tools import ValidationToolContext, build_validation_tools


def test_find_shared_address_applicants_returns_neo4j_ids():
    ctx = ValidationToolContext(
        flags=[
            {
                "field": "duplicate",
                "severity": "high",
                "message": "2 other application(s) share this address.",
            }
        ],
        form_data={},
        extractions_by_type={},
        application_id="app-current",
        household={},
        address="Villa 12, Al Wathba, Abu Dhabi",
        shared_address_applicants=["app-other-1", "app-other-2"],
    )
    tools = build_validation_tools(ctx)
    tool = next(t for t in tools if t.name == "find_shared_address_applicants")
    payload = json.loads(tool.invoke({}))
    assert payload["application_ids"] == ["app-other-1", "app-other-2"]
    assert payload["address"] == "Villa 12, Al Wathba, Abu Dhabi"
