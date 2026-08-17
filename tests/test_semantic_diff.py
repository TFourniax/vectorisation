import numpy as np

from semantic_atlas.semantic_diff import propose_contract_questions, semantic_diff


def unit(x):
    x = np.asarray(x, dtype=np.float32)
    return x / np.linalg.norm(x)


def test_semantic_diff_detects_local_topology_change():
    old = {
        "a": unit([1.0, 0.0, 0.0]),
        "b": unit([0.95, 0.2, 0.0]),
        "c": unit([0.7, 0.7, 0.0]),
        "d": unit([0.0, 1.0, 0.0]),
    }
    new = dict(old)
    new["b"] = unit([0.0, 0.95, 0.2])

    diff = semantic_diff(old, new, k=2)
    by_id = {row.object_id: row for row in diff.objects}
    assert diff.shared_objects == 4
    assert diff.mean_neighbor_churn > 0.0
    assert by_id["a"].severity > 0.0


def test_question_miner_surfaces_reversed_top_neighbor_preference():
    old = {
        "a": unit([1.0, 0.0]),
        "b": unit([0.99, 0.10]),
        "c": unit([0.70, 0.71]),
        "d": unit([-1.0, 0.0]),
    }
    new = {
        "a": unit([1.0, 0.0]),
        "b": unit([0.60, 0.80]),
        "c": unit([0.99, 0.05]),
        "d": unit([-1.0, 0.0]),
    }
    questions = propose_contract_questions(old, new, limit=10, k=2, min_disagreement=0.01)
    anchor_a = [question for question in questions if question.anchor_id == "a"]
    assert anchor_a
    question = anchor_a[0]
    assert question.old_preference == "b"
    assert question.new_preference == "c"
    assert question.priority > 0
    assert "which is genuinely closer" in question.as_prompt()
