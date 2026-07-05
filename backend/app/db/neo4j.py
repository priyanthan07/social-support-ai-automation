"""Neo4j client for the applicant / household relationship graph.

Used by the Validation Agent to model household composition and to surface
cross-applicant signals such as shared addresses (possible duplicate / fraud).
"""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from neo4j import Driver, GraphDatabase

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


@lru_cache
def get_driver() -> Driver:
    return GraphDatabase.driver(
        settings.neo4j_uri, auth=(settings.neo4j_user, settings.neo4j_password)
    )


def create_constraints() -> None:
    """Idempotently create uniqueness constraints."""
    stmts = [
        "CREATE CONSTRAINT applicant_id IF NOT EXISTS "
        "FOR (a:Applicant) REQUIRE a.application_id IS UNIQUE",
    ]
    with get_driver().session() as session:
        for stmt in stmts:
            session.run(stmt)


def upsert_household(
    application_id: str,
    applicant_name: str,
    address: str | None,
    family_members: list[dict[str, Any]] | None,
) -> None:
    """Create/merge the applicant, their address, and family-member nodes."""
    family_members = family_members or []
    query = """
    MERGE (a:Applicant {application_id: $application_id})
      SET a.name = $applicant_name
    WITH a
    FOREACH (_ IN CASE WHEN $address IS NULL THEN [] ELSE [1] END |
        MERGE (addr:Address {value: $address})
        MERGE (a)-[:RESIDES_AT]->(addr)
    )
    WITH a
    UNWIND $family_members AS fm
        MERGE (m:Person {name: fm.name})
        SET m.relation = fm.relation
        MERGE (a)-[:HAS_FAMILY_MEMBER]->(m)
    """
    with get_driver().session() as session:
        session.run(
            query,
            application_id=application_id,
            applicant_name=applicant_name,
            address=address,
            family_members=family_members,
        )


def find_shared_address_applicants(application_id: str, address: str | None) -> list[str]:
    """Return other application_ids registered at the same address."""
    if not address:
        return []
    query = """
    MATCH (a:Applicant)-[:RESIDES_AT]->(addr:Address {value: $address})
    WHERE a.application_id <> $application_id
    RETURN a.application_id AS other
    """
    with get_driver().session() as session:
        result = session.run(query, address=address, application_id=application_id)
        return [record["other"] for record in result]


def household_snapshot(application_id: str) -> dict[str, Any]:
    """Return a small snapshot of the applicant's graph for the UI."""
    query = """
    MATCH (a:Applicant {application_id: $application_id})
    OPTIONAL MATCH (a)-[:RESIDES_AT]->(addr:Address)
    OPTIONAL MATCH (a)-[:HAS_FAMILY_MEMBER]->(m:Person)
    RETURN a.name AS name, addr.value AS address, collect(DISTINCT m.name) AS members
    """
    with get_driver().session() as session:
        rec = session.run(query, application_id=application_id).single()
        if not rec:
            return {}
        return {"name": rec["name"], "address": rec["address"], "members": rec["members"]}


def ping() -> bool:
    try:
        with get_driver().session() as session:
            session.run("RETURN 1")
        return True
    except Exception as exc:  # pragma: no cover
        logger.warning("Neo4j ping failed: %s", exc)
        return False
