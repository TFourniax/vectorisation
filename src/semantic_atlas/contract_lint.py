from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .contracts import MutualNeighborClause, NeighborClause, SemanticContract, TripletClause


@dataclass(slots=True, frozen=True)
class ContractIssue:
    code: str
    severity: str
    message: str
    clause_indices: tuple[int, ...]
    objects: tuple[str, ...] = ()


@dataclass(slots=True)
class ContractLintReport:
    contract_digest: str
    issues: list[ContractIssue]

    @property
    def errors(self) -> list[ContractIssue]:
        return [issue for issue in self.issues if issue.severity == "error"]

    @property
    def warnings(self) -> list[ContractIssue]:
        return [issue for issue in self.issues if issue.severity == "warning"]

    @property
    def valid(self) -> bool:
        return not self.errors

    def by_code(self, code: str) -> list[ContractIssue]:
        return [issue for issue in self.issues if issue.code == code]


def _preference_cycles(edges: dict[str, list[tuple[str, int, float]]]) -> list[tuple[list[str], list[int], float]]:
    """Return simple DFS-discovered cycles and their summed required margin."""
    cycles: list[tuple[list[str], list[int], float]] = []
    state: dict[str, int] = {}
    node_stack: list[str] = []
    edge_stack: list[tuple[int, float]] = []
    seen_signatures: set[tuple[str, ...]] = set()

    def canonical(nodes: list[str]) -> tuple[str, ...]:
        # nodes excludes repeated final node.
        if not nodes:
            return ()
        rotations = [tuple(nodes[i:] + nodes[:i]) for i in range(len(nodes))]
        return min(rotations)

    def visit(node: str) -> None:
        state[node] = 1
        node_stack.append(node)
        for nxt, clause_index, margin in edges.get(node, []):
            if state.get(nxt, 0) == 0:
                edge_stack.append((clause_index, margin))
                visit(nxt)
                edge_stack.pop()
            elif state.get(nxt) == 1 and nxt in node_stack:
                start = node_stack.index(nxt)
                cycle_nodes = node_stack[start:].copy()
                signature = canonical(cycle_nodes)
                if signature in seen_signatures:
                    continue
                seen_signatures.add(signature)
                cycle_edges = edge_stack[start:] + [(clause_index, margin)]
                cycles.append(
                    (
                        cycle_nodes,
                        [idx for idx, _ in cycle_edges],
                        float(sum(required for _, required in cycle_edges)),
                    )
                )
        node_stack.pop()
        state[node] = 2

    for node in sorted(edges):
        if state.get(node, 0) == 0:
            visit(node)
    return cycles


def lint_contract(contract: SemanticContract) -> ContractLintReport:
    """Check a Semantic Contract for static contradictions and impossible clauses.

    This does not prove the contract is semantically *correct*. It verifies that
    obvious schema-level pathologies are caught before implementations are
    evaluated or repaired against an impossible target.
    """
    issues: list[ContractIssue] = []
    exact_triplets: dict[tuple[str, str, str], int] = {}
    per_anchor_edges: dict[str, dict[str, list[tuple[str, int, float]]]] = {}

    for index, clause in enumerate(contract.clauses):
        weight = float(clause.weight)
        if weight < 0.0:
            issues.append(ContractIssue("negative_weight", "error", "Clause weight must be non-negative.", (index,), clause.objects))
        elif weight == 0.0:
            issues.append(ContractIssue("zero_weight", "warning", "Zero-weight clause cannot affect the contract score.", (index,), clause.objects))

        if isinstance(clause, TripletClause):
            if clause.anchor in {clause.positive, clause.negative} or clause.positive == clause.negative:
                issues.append(ContractIssue("degenerate_triplet", "error", "Triplet anchor/positive/negative must identify distinct logical objects.", (index,), clause.objects))
            key = (clause.anchor, clause.positive, clause.negative)
            reverse = (clause.anchor, clause.negative, clause.positive)
            if key in exact_triplets:
                issues.append(ContractIssue("duplicate_triplet", "warning", "Duplicate ordinal assertion.", (exact_triplets[key], index), clause.objects))
            if reverse in exact_triplets:
                other = exact_triplets[reverse]
                severity = "error" if (clause.hard or contract.clauses[other].hard or clause.margin > 0 or contract.clauses[other].margin > 0) else "warning"
                issues.append(ContractIssue("reversed_triplet", severity, "Opposite ordinal assertions exist for the same anchor and pair.", (other, index), clause.objects))
            exact_triplets[key] = index
            if clause.margin < 0:
                issues.append(ContractIssue("negative_triplet_margin", "warning", "Negative triplet margin weakens the declared preference and may be unintended.", (index,), clause.objects))
            graph = per_anchor_edges.setdefault(clause.anchor, {})
            graph.setdefault(clause.positive, []).append((clause.negative, index, max(0.0, float(clause.margin))))
            graph.setdefault(clause.negative, [])
            continue

        if isinstance(clause, NeighborClause):
            if not 0.0 <= clause.min_recall <= 1.0:
                issues.append(ContractIssue("invalid_min_recall", "error", "min_recall must be in [0, 1].", (index,), clause.objects))
            if len(set(clause.expected)) != len(clause.expected):
                issues.append(ContractIssue("duplicate_expected_neighbor", "warning", "Expected neighborhood contains duplicate logical IDs.", (index,), clause.objects))
            if clause.anchor in set(clause.expected):
                issues.append(ContractIssue("self_neighbor", "error", "Anchor cannot be an expected external neighbor of itself.", (index,), clause.objects))
            if clause.candidate_k is not None:
                if int(clause.candidate_k) <= 0:
                    issues.append(ContractIssue("invalid_candidate_k", "error", "candidate_k must be positive.", (index,), clause.objects))
                elif clause.expected:
                    max_recall = min(int(clause.candidate_k), len(set(clause.expected))) / len(set(clause.expected))
                    if clause.min_recall > max_recall + 1e-12:
                        issues.append(ContractIssue("impossible_neighbor_recall", "error", f"Requested recall {clause.min_recall:.3f} exceeds maximum {max_recall:.3f} possible with candidate_k={clause.candidate_k}.", (index,), clause.objects))
            continue

        if isinstance(clause, MutualNeighborClause):
            if clause.left == clause.right:
                issues.append(ContractIssue("degenerate_mutual_neighbor", "error", "Mutual-neighbor relation requires two distinct objects.", (index,), clause.objects))
            if int(clause.k) <= 0:
                issues.append(ContractIssue("invalid_mutual_k", "error", "Mutual-neighbor k must be positive.", (index,), clause.objects))
            continue

    for anchor, edges in per_anchor_edges.items():
        for nodes, indices, margin_sum in _preference_cycles(edges):
            # A cycle with positive total required margin is mathematically
            # impossible. A zero-margin cycle can only be satisfied by ties and
            # is therefore flagged as a semantic warning rather than an error.
            severity = "error" if margin_sum > 1e-12 else "warning"
            code = "impossible_preference_cycle" if severity == "error" else "degenerate_preference_cycle"
            issues.append(
                ContractIssue(
                    code,
                    severity,
                    f"Ordinal preference cycle for anchor {anchor!r} has total required margin {margin_sum:.6f}.",
                    tuple(indices),
                    (anchor, *tuple(nodes)),
                )
            )

    # Stable ordering makes lint evidence deterministic and release-friendly.
    issues.sort(key=lambda issue: (0 if issue.severity == "error" else 1, issue.code, issue.clause_indices, issue.objects))
    return ContractLintReport(contract.digest, issues)
