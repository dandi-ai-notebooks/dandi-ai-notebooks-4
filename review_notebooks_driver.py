#!/usr/bin/env python

from typing import List, Dict
import os
import json
from pathlib import Path

this_dir = Path(__file__).parent

def rank_notebooks(nodes1: List[str],
                   nodes2: List[str],
                   selections: List[int],
                   *,
                   max_iter: int = 1000,
                   tol: float = 1e-8) -> List[str]:
    """
    Rank notebooks given pair‑wise outcomes using the Bradley‑Terry model.

    Parameters
    ----------
    nodes1, nodes2 : List[str]
        Paired notebook identifiers.  nodes1[i] competed against nodes2[i].
    selections : List[int]
        For each pair, 1 means nodes1[i] won, 2 means nodes2[i] won.
    max_iter : int, optional
        Maximum MM iterations (default 1000).
    tol : float, optional
        Convergence threshold on max parameter change (default 1e‑8).

    Returns
    -------
    List[str]
        Notebook names sorted from highest to lowest estimated ability.
    """
    if not (len(nodes1) == len(nodes2) == len(selections)):
        raise ValueError("nodes1, nodes2 and selections must be the same length")

    if len(nodes1) == 0:
        return []

    # All unique notebooks start with the same ability
    items = set(nodes1) | set(nodes2)
    theta: Dict[str, float] = {item: 1.0 for item in items}

    for _ in range(max_iter):
        wins  = {item: 0.0 for item in items}   # w_i
        denom = {item: 0.0 for item in items}   # d_i

        # accumulate wins and denominators
        for a, b, s in zip(nodes1, nodes2, selections):
            if s == 1:
                wins[a] += 1
            elif s == 2:
                wins[b] += 1
            else:
                raise ValueError("selections must contain only 1 or 2")

            inv_sum = 1.0 / (theta[a] + theta[b])
            denom[a] += inv_sum
            denom[b] += inv_sum

        # MM‑update: θ_i ← w_i / d_i   (leave θ_i unchanged if d_i == 0)
        new_theta = {i: (wins[i] / denom[i] if denom[i] else theta[i])
                     for i in items}

        # normalise for identifiability (mean θ = 1)
        mean_theta = sum(new_theta.values()) / len(new_theta)
        for i in items:
            new_theta[i] /= mean_theta or 1.0  # avoid division by 0

        # check convergence
        if max(abs(new_theta[i] - theta[i]) for i in items) < tol:
            theta = new_theta
            break
        theta = new_theta

    # sort by estimated ability (descending)
    return sorted(theta.keys(), key=lambda k: theta[k], reverse=True)

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
            if not os.path.exists(comparison_fname):
                cmd = f'./scripts/comparison.py --dandiset_id {dandiset_id} --version {version} --model {review_model} --subfolder1_name {subdir1} --subfolder2_name {subdir2}'
                print(f"Running command: {cmd}")
                result = os.system(cmd)
                if result != 0:
                    raise RuntimeError(f"Failed to run command: {cmd}")
                if not os.path.exists(comparison_fname):
                    raise RuntimeError(f"Comparison file {comparison_fname} does not exist even after running the command")
            else:
                print(f"Comparison file {comparison_fname} exists")
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
    ranked_notebooks = rank_notebooks(nodes1=nodes1, nodes2=nodes2, selections=selections)
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
