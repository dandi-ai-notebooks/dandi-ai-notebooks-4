import numpy as np
from typing import List, Tuple

def _fit_bt(nodes1: List[str],
            nodes2: List[str],
            selections: List[int],
            all_nodes: List[str],
            max_iter: int = 1000,
            tol: float = 1e-6) -> np.ndarray:
    """
    Fit a Bradley‑Terry model and return the ability (“skill”) vector r.

    r[i] > 1 ⇒ node i is better than average, r[i] < 1 ⇒ worse than average.
    """
    index = {node: i for i, node in enumerate(all_nodes)}
    n = len(all_nodes)

    # match & win matrices ----------------------------------------------------
    matches = np.zeros((n, n), dtype=int)
    wins    = np.zeros((n, n), dtype=int)

    for a, b, sel in zip(nodes1, nodes2, selections):
        i, j = index[a], index[b]
        matches[i, j] += 1
        matches[j, i] += 1
        if sel == 1:       # first node chosen
            wins[i, j] += 1
        else:              # second node chosen
            wins[j, i] += 1

    w_i = wins.sum(axis=1)          # total wins per node
    r   = np.ones(n, dtype=float)   # initialise abilities

    # MM iterations -----------------------------------------------------------
    for _ in range(max_iter):
        r_old = r.copy()

        denom = np.zeros(n, dtype=float)
        for i in range(n):
            for j in range(n):
                if i == j or matches[i, j] == 0:
                    continue
                denom[i] += matches[i, j] / (r[i] + r[j])

        # update step
        update_mask = denom > 0
        r[update_mask] = w_i[update_mask] / denom[update_mask]

        r /= r.mean()                              # identifiability
        if np.max(np.abs(r - r_old)) < tol:        # convergence
            break

    return r


# --------------------------------------------------------------------------- #
#  Public helpers                                                             #
# --------------------------------------------------------------------------- #

def rank_notebooks(*,
                   nodes1: List[str],
                   nodes2: List[str],
                   selections: List[int],
                   all_nodes: List[str]) -> List[str]:
    """
    Rank notebooks from best to worst using the Bradley‑Terry model.
    """
    r = _fit_bt(nodes1, nodes2, selections, all_nodes)
    order = np.argsort(-r)            # descending by ability
    return [all_nodes[i] for i in order]


def suggest_next_comparison(*,
                            nodes1: List[str],
                            nodes2: List[str],
                            selections: List[int],
                            all_nodes: List[str]) -> Tuple[str, str]:
    """
    Heuristic for the next most‑informative pair to compare.

    – If an untried pair exists, return the first one encountered.
    – Otherwise, return the pair whose current BT skill estimates are
      closest (|rank difference| minimal), i.e. where our knowledge is
      most uncertain.
    """
    index = {node: i for i, node in enumerate(all_nodes)}
    n = len(all_nodes)

    compared = set()
    for a, b in zip(nodes1, nodes2):
        i, j = index[a], index[b]
        compared.add((min(i, j), max(i, j)))

    # 1) Any still‑unseen pair? ----------------------------------------------
    for i in range(n):
        for j in range(i + 1, n):
            if (i, j) not in compared:
                return all_nodes[i], all_nodes[j]

    # 2) Otherwise pick pair with abilities closest to each other ------------
    abilities = _fit_bt(nodes1, nodes2, selections, all_nodes)
    best_pair = None
    best_gap  = float("inf")

    for i in range(n):
        for j in range(i + 1, n):
            gap = abs(abilities[i] - abilities[j])
            if gap < best_gap:
                best_gap, best_pair = gap, (all_nodes[i], all_nodes[j])

    if best_pair is None:
        raise RuntimeError("No best pair found, this should not happen")

    return best_pair
