#!/usr/bin/env python

from typing import List, Dict, Any, Tuple
import os
import json
from pathlib import Path
import math
import itertools

this_dir = Path(__file__).parent

# --------------------------------------------------------------------------- #
# Internal helper: one‐shot Bradley–Terry fit                                 #
# --------------------------------------------------------------------------- #

def _fit_bradley_terry(
    nodes1: List[str],
    nodes2: List[str],
    selections: List[int],
    all_nodes: List[str],
    *,
    alpha: float = 0.5,
    max_iter: int = 1000,
    tol: float = 1e-8,
) -> Dict[str, float]:
    """
    Return a mapping {notebook: ability θ} using MM updates with
    Laplace smoothing (α pseudo‑wins) to avoid zero abilities.
    """
    if not (len(nodes1) == len(nodes2) == len(selections)):
        raise ValueError("nodes1, nodes2 and selections must have equal length")

    items = set(all_nodes)
    theta: Dict[str, float] = {i: 1.0 for i in items}            # initial skill

    for _ in range(max_iter):
        wins  = {i: alpha for i in items}                        # Laplace prior
        denom = {i: 0.0   for i in items}

        for a, b, s in zip(nodes1, nodes2, selections):
            if s == 1:
                wins[a] += 1
            elif s == 2:
                wins[b] += 1
            else:
                raise ValueError("selections must contain only 1 or 2")

            inv = 1.0 / (theta[a] + theta[b])
            denom[a] += inv
            denom[b] += inv

        new_theta = {
            i: (wins[i] / denom[i] if denom[i] else theta[i])
            for i in items
        }

        # Normalise:  mean θ = 1 to remove scale indeterminacy
        mean_th = sum(new_theta.values()) / len(new_theta)
        for i in items:
            new_theta[i] /= mean_th or 1.0

        # Convergence check
        if max(abs(new_theta[i] - theta[i]) for i in items) < tol:
            theta = new_theta
            break
        theta = new_theta

    return theta


# --------------------------------------------------------------------------- #
# Public: rank notebooks                                                      #
# --------------------------------------------------------------------------- #

def rank_notebooks(
    nodes1: List[str],
    nodes2: List[str],
    selections: List[int],
    all_nodes: List[str],
    *,
    alpha: float = 0.5,
    max_iter: int = 1000,
    tol: float = 1e-8,
) -> List[str]:
    """
    Return notebook identifiers sorted from *best* to *worst* estimated
    ability.

    See _fit_bradley_terry for the meaning of alpha / max_iter / tol.
    """
    if len(nodes1) == 0:
        return []

    theta = _fit_bradley_terry(nodes1, nodes2, selections, all_nodes=all_nodes,
                               alpha=alpha, max_iter=max_iter, tol=tol)
    return sorted(theta, key=theta.get, reverse=True)  # type: ignore[return-value]


# --------------------------------------------------------------------------- #
# Public: suggest the next comparison                                         #
# --------------------------------------------------------------------------- #

def suggest_next_comparison(
    nodes1: List[str],
    nodes2: List[str],
    selections: List[int],
    all_nodes: List[str],
    *,
    alpha: float = 0.5,
    max_iter: int = 1000,
    tol: float = 1e-8,
) -> Tuple[str, str]:
    """
    Choose the pair (i, j) that maximises expected information gain,
    measured by Shannon entropy of the Bradley–Terry win probability and
    down‑weighted by how often the pair has already been compared.
    """
    if len(nodes1) == 0:          # nothing compared yet → any pair is fine
        raise ValueError("At least one past comparison is required")

    theta = _fit_bradley_terry(nodes1, nodes2, selections, all_nodes=all_nodes,
                               alpha=alpha, max_iter=max_iter, tol=tol)

    items = set(theta)
    # Count how many times each unordered pair has been judged
    pair_counts: Dict[frozenset, int] = {
        frozenset({a, b}): 0 for a, b in itertools.combinations(items, 2)
    }
    for a, b in zip(nodes1, nodes2):
        pair_counts[frozenset({a, b})] += 1

    # Scan all possible new pairs
    EPS = 1e-12
    best_pair, best_score = None, -1.0
    for i, j in itertools.combinations(items, 2):
        denom = theta[i] + theta[j]
        if denom < EPS:                 # both abilities ~0 → no information
            continue

        p_ij = theta[i] / denom
        # Ignore pairs that are (almost) deterministic
        if p_ij < EPS or (1 - p_ij) < EPS:
            continue

        entropy = -p_ij * math.log2(p_ij) - (1 - p_ij) * math.log2(1 - p_ij)
        score   = entropy / (1 + pair_counts[frozenset({i, j})])

        if score > best_score:
            best_score, best_pair = score, (i, j)

    if best_pair is None:
        raise RuntimeError("All remaining pairs give zero expected gain; "
                           "further comparisons will not improve the ranking.")
    return best_pair

def process_dandiset(*, dandiset_id: str, version: str, review_model: str):
    dandiset_folder = f'{this_dir}/dandiset_repos/{dandiset_id}/v4/{version}'
    if not os.path.exists(dandiset_folder):
        raise RuntimeError(f"Dandiset folder {dandiset_folder} does not exist")
    review_model_second_part = review_model.split('/')[1]
    review_folder = f'{this_dir}/reviews/{review_model_second_part}/dandisets/{dandiset_id}/{version}'
    # get the subdirectories in review_folder
    subdirs = [f for f in os.listdir(dandiset_folder) if os.path.isdir(os.path.join(dandiset_folder, f))]
    passing_subdirs = []
    for subdir in subdirs:
        notebook_fname = f'{dandiset_folder}/{subdir}/{dandiset_id}.ipynb'
        if not os.path.exists(notebook_fname):
            print(f"Notebook file {notebook_fname} does not exist. Skipping.")
            continue
        qualification_test_fname = f'{review_folder}/{subdir}/qualification_test.json'
        if os.path.exists(qualification_test_fname):
            print(f"Qualification test file {qualification_test_fname} exists")
        else:
            cmd = f'./scripts/qualification_test.py  --dandiset_id {dandiset_id} --version {version} --model {review_model} --subfolder_name {subdir}'
            print(f"Running command: {cmd}")
            result = os.system(cmd)
            if result != 0:
                raise RuntimeError(f"Failed to run command: {cmd}")
        if not os.path.exists(qualification_test_fname):
            raise RuntimeError(f"Qualification test file {qualification_test_fname} does not exist even after running the command")
        with open(qualification_test_fname, 'r') as f:
            qualification_test = json.load(f)
            grades = qualification_test['grades']
            all_passing = True
            for grade in grades:
                if grade['grade'] != 'PASS':
                    all_passing = False
                    break
            if all_passing:
                passing_subdirs.append(subdir)
    print(f"Passing subdirs for {dandiset_id} {version}: {passing_subdirs}")
    # be sure they are sorted
    passing_subdirs.sort()
    # now run the comparison for each pair of passing subdirs
    comparison_results = []
    for i1, subdir1 in enumerate(passing_subdirs):
        for i2, subdir2 in enumerate(passing_subdirs):
            if i1 >= i2:
                continue
            comparison_fname = f'{review_folder}/{subdir1}/comparisons/{subdir2}/comparison.json'
            if os.path.exists(comparison_fname):
                with open(comparison_fname, 'r') as f:
                    comparison = json.load(f)
                selection = comparison['selection']
                comparison_results.append((
                    subdir1, subdir2, selection
                ))

    # do 3 more comparisons (how do we know when to stop?)
    for aa in range(3):
        next_pair = suggest_next_comparison(
            nodes1=[i[0] for i in comparison_results],
            nodes2=[i[1] for i in comparison_results],
            selections=[i[2] for i in comparison_results],
            all_nodes=passing_subdirs
        )
        print(f"Next pair to compare: {next_pair}")
        subdir1, subdir2 = next_pair
        comparison_fname = f'{review_folder}/{subdir1}/comparisons/{subdir2}/comparison.json'
        if not os.path.exists(comparison_fname):
            cmd = f'./scripts/comparison.py --dandiset_id {dandiset_id} --version {version} --model {review_model} --subfolder1_name {subdir1} --subfolder2_name {subdir2}'
            print(f"Running command: {cmd}")
            result = os.system(cmd)
            if result != 0:
                raise RuntimeError(f"Failed to run command: {cmd}")
            if not os.path.exists(comparison_fname):
                raise RuntimeError(f"Comparison file {comparison_fname} does not exist even after running the command")
        with open(comparison_fname, 'r') as f:
            comparison = json.load(f)
            selection = comparison['selection']
            comparison_results.append((
                subdir1, subdir2, selection
            ))

    nodes1 = []
    nodes2 = []
    selections = []
    num_wins = {
        k: 0 for k in passing_subdirs
    }
    num_losses = {
        k: 0 for k in passing_subdirs
    }
    for subfolder1, subfolder2, selection in comparison_results:
        nodes1.append(subfolder1)
        nodes2.append(subfolder2)
        selections.append(selection)
        if selection == 1:
            num_wins[subfolder1] += 1
            num_losses[subfolder2] += 1
        elif selection == 2:
            num_wins[subfolder2] += 1
            num_losses[subfolder1] += 1
    ranked_notebooks = rank_notebooks(nodes1=nodes1, nodes2=nodes2, selections=selections, all_nodes=passing_subdirs)
    print(f"\nRanked notebooks for model dandiset {dandiset_id}:")
    for i, notebook in enumerate(ranked_notebooks):
        print(f"{i + 1}: {notebook} (wins: {num_wins[notebook]}, losses: {num_losses[notebook]})")
    ranking_json_fname = f'{review_folder}/rankings.json'
    with open(ranking_json_fname, 'w') as f:
        json.dump({
            'ranked_notebooks': [
                {
                    'subfolder': notebook,
                    'wins': num_wins[notebook],
                    'losses': num_losses[notebook]
                }
                for notebook in ranked_notebooks
            ]
        }, f, indent=4)


def main():
    review_model = "anthropic/claude-3.7-sonnet"
    dandiset_repos_dir = f'{this_dir}/dandiset_repos'
    if not os.path.exists(dandiset_repos_dir):
        raise RuntimeError(f"Dandiset repos folder {dandiset_repos_dir} does not exist")
    for dandiset_id in os.listdir(dandiset_repos_dir):
        if not os.path.isdir(os.path.join(dandiset_repos_dir, dandiset_id)):
            continue
        dandiset_dir = os.path.join(dandiset_repos_dir, dandiset_id, 'v4')
        if not os.path.exists(dandiset_dir):
            continue
        for version in os.listdir(dandiset_dir):
            if not os.path.isdir(os.path.join(dandiset_dir, version)):
                continue
            print(f"Processing dandiset {dandiset_id} version {version}")
            process_dandiset(dandiset_id=dandiset_id, version=version, review_model=review_model)

if __name__ == '__main__':
    main()
