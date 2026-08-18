import pytest

from semantic_atlas.pgvector_provider import PgVectorOracleV1
from semantic_atlas.protocol_v1 import NeighborRequest, ScorePair


class FakeCursor:
    def __init__(self, connection):
        self.connection = connection
        self.rows = []

    def execute(self, sql, params=()):
        self.connection.calls.append((sql, tuple(params)))
        if "= ANY(%s)" in sql:
            requested = set(params[0])
            self.rows = [(value,) for value in ("doc:a", "doc:b") if value in requested]
        elif "SELECT \"embedding\"::text" in sql:
            self.rows = [("[1,0,0]",)] if params[0] == "doc:anchor" else []
        elif " AS score " in sql:
            candidate = params[-1]
            self.rows = [(0.8 if candidate == "doc:a" else 0.2,)]
        elif " ORDER BY " in sql:
            self.rows = [("doc:a",), ("doc:b",), ("doc:c",)]
        else:
            raise AssertionError((sql, params))

    def fetchall(self):
        return list(self.rows)

    def close(self):
        pass


class FakeConnection:
    def __init__(self):
        self.calls = []
        self.closed = False

    def cursor(self):
        return FakeCursor(self)

    def close(self):
        self.closed = True


def test_pgvector_cosine_adapter_normalizes_distance_to_higher_is_better():
    conn = FakeConnection()
    oracle = PgVectorOracleV1(
        conn,
        table="documents",
        query_catalog={"q:1": [1, 0, 0]},
        metric="cosine",
    )
    pair = ScorePair("q:1", "doc:a")

    assert oracle.contains_many(["q:1", "doc:a", "missing"]) == {
        "q:1": True,
        "doc:a": True,
        "missing": False,
    }
    assert oracle.score_many([pair])[pair] == pytest.approx(0.8)

    score_sql, score_params = [call for call in conn.calls if " AS score " in call[0]][0]
    assert "1 - (\"embedding\" <=> %s::vector)" in score_sql
    assert score_params == ("[1,0,0]", "doc:a")


def test_pgvector_row_anchor_loads_vector_and_excludes_itself():
    conn = FakeConnection()
    oracle = PgVectorOracleV1(conn, table="documents", metric="l2")
    request = NeighborRequest("doc:anchor", 2)

    result = oracle.neighbors_many([request])

    assert result[request] == ("doc:a", "doc:b")
    neighbor_sql, params = [call for call in conn.calls if " ORDER BY " in call[0]][0]
    assert "\"id\"::text <> %s" in neighbor_sql
    assert "<-> %s::vector" in neighbor_sql
    # Vector placeholder is selected before the WHERE placeholder.
    assert params == ("[1,0,0]", "doc:anchor", 2)


def test_pgvector_inner_product_is_converted_from_negative_operator_result():
    conn = FakeConnection()
    oracle = PgVectorOracleV1(
        conn,
        table="documents",
        query_catalog={"q:1": "[0.1,0.2]"},
        metric="inner_product",
    )
    oracle.score_many([ScorePair("q:1", "doc:a")])
    sql = [call[0] for call in conn.calls if " AS score " in call[0]][0]
    assert "-1 * (\"embedding\" <#> %s::vector)" in sql


def test_pgvector_rejects_untrusted_identifiers_and_invalid_vectors():
    conn = FakeConnection()
    with pytest.raises(ValueError, match="invalid SQL identifier"):
        PgVectorOracleV1(conn, table="documents; DROP TABLE users")
    with pytest.raises(ValueError, match="finite"):
        PgVectorOracleV1(conn, table="documents", query_catalog={"q": [float("nan")]})
    with pytest.raises(ValueError, match="unsupported pgvector metric"):
        PgVectorOracleV1(conn, table="documents", metric="made-up")


def test_pgvector_close_closes_owned_connection_surface():
    conn = FakeConnection()
    oracle = PgVectorOracleV1(conn, table="documents")
    oracle.close()
    assert conn.closed is True
