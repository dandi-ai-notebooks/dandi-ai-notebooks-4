import numpy as np
from typing import List, Tuple

import math
from typing import List, Dict, Set

def rank_notebooks(*,
                   nodes1: List[str],
                   nodes2: List[str],
                   selections: List[int],
                   all_nodes: List[str],
                   max_iter: int = 10_000,
                   lr: float = 0.05,
                   tol: float = 1e-6) -> List[str]:
    """
    Rank notebooks from best to worst using the Bradley‑Terry model.

    Parameters
    ----------
    nodes1, nodes2 : Lists of node names (same length).
        The i‑th entry of `nodes1` was compared against the i‑th entry of `nodes2`.
    selections : List[int]
        Outcome of each comparison: 1 if `nodes1[i]` won, 2 if `nodes2[i]` won.
    all_nodes : List[str]
        Master list of every notebook; some may never appear in the comparisons.
    max_iter : int, default 10_000
        Soft cap on optimisation iterations.
    lr : float, default 0.05
        Learning‑rate for plain gradient ascent.
    tol : float, default 1e‑6
        Stop when the largest absolute gradient component drops below this value.

    Returns
    -------
    List[str]
        `all_nodes` reordered from best to worst.  Nodes that never took part in
        any duel are appended—preserving their original order—after all active
        nodes.
    """
    if not (len(nodes1) == len(nodes2) == len(selections)):
        raise ValueError("nodes1, nodes2 and selections must have identical length")

    # —­­ bookkeeping ----------------------------------------------------------
    index: Dict[str, int] = {n: i for i, n in enumerate(all_nodes)}
    n = len(all_nodes)

    active: Set[str] = set(nodes1) | set(nodes2)          # took part in ≥1 duel
    inactive: List[str] = [n for n in all_nodes           # never appeared
                           if n not in active]

    a = [0.0] * n                                         # abilities initialised to 0

    # —­­ optimisation loop -----------------------------------------------------
    for _ in range(max_iter):
        grad = [0.0] * n

        # accumulate gradient over every comparison
        for p, q, outcome in zip(nodes1, nodes2, selections):
            i, j = index[p], index[q]
            ai, aj = a[i], a[j]
            exp_ai, exp_aj = math.exp(ai), math.exp(aj)
            denom = exp_ai + exp_aj
            p_i_win = exp_ai / denom                      # model prob that i wins
            y_i = 1.0 if outcome == 1 else 0.0            # observed result

            # ∂ℓ/∂a_i = y_i − p_i_win      ,  ∂ℓ/∂a_j = (1−y_i) − (1−p_i_win)
            grad_i = y_i - p_i_win
            grad_j = -grad_i
            grad[i] += grad_i
            grad[j] += grad_j

        # stopping criterion
        if max(abs(g) for g in grad) < tol:
            break

        # update step
        for k in range(n):
            a[k] += lr * grad[k]

        # remove identifiability: centre abilities so their mean over *active* is 0
        mean_active = sum(a[index[n]] for n in active) / len(active)
        for k in range(n):
            a[k] -= mean_active

    # —­­ build final ranking ---------------------------------------------------
    ranked_active = sorted(active, key=lambda name: a[index[name]], reverse=True)
    return ranked_active + inactive


def suggest_next_comparison(*,
                            nodes1: List[str],
                            nodes2: List[str],
                            selections: List[int],
                            all_nodes: List[str]) -> Tuple[str, str] | None:
    """
    Return the pair for next comparison or None if all comparisons are done.
    We continue until every node has been compared with its ranked neighbors
    """
    ranked_nodes = rank_notebooks(
        nodes1=nodes1,
        nodes2=nodes2,
        selections=selections,
        all_nodes=all_nodes
    )
    num_comparisons_by_node = {}
    for node in all_nodes:
        num_comparisons_by_node[node] = 0
    for i in range(len(nodes1)):
        num_comparisons_by_node[nodes1[i]] += 1
        num_comparisons_by_node[nodes2[i]] += 1
    candidate_comparisons = []
    for i in range(len(ranked_nodes) - 1):
        node1 = ranked_nodes[i]
        node2 = ranked_nodes[i + 1]
        comparison_has_been_made = False
        for a in range(len(nodes1)):
            if nodes1[a] == node1 and nodes2[a] == node2:
                comparison_has_been_made = True
                break
            if nodes1[a] == node2 and nodes2[a] == node1:
                comparison_has_been_made = True
                break
        if not comparison_has_been_made:
            candidate_comparisons.append((node1, node2))
    if len(candidate_comparisons) == 0:
        return None
    least_num_comparisons = None
    best_candidate = None
    for candidate in candidate_comparisons:
        node1, node2 = candidate
        num_comparisons = num_comparisons_by_node[node1] + num_comparisons_by_node[node2]
        if least_num_comparisons is None or num_comparisons < least_num_comparisons:
            least_num_comparisons = num_comparisons
            best_candidate = candidate
    if best_candidate is None:
        return None
    node1, node2 = best_candidate
    return node1, node2


