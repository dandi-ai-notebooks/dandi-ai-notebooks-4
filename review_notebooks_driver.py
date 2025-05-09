#!/usr/bin/env python

import os
import json
from pathlib import Path
from scripts.helpers.rank_notebooks import rank_notebooks, suggest_next_comparison

this_dir = Path(__file__).parent

def process_dandiset(*, dandiset_id: str, version: str, review_model: str):
    dandiset_folder = f'{this_dir}/dandiset_repos/{dandiset_id}/v4/{version}'
    if not os.path.exists(dandiset_folder):
        raise RuntimeError(f"Dandiset folder {dandiset_folder} does not exist")
    review_model_second_part = review_model.split('/')[1]
    review_folder = f'{this_dir}/reviews/{review_model_second_part}/dandisets/{dandiset_id}/{version}'
    # get the subdirectories in review_folder
    subdirs = [f for f in os.listdir(dandiset_folder) if os.path.isdir(os.path.join(dandiset_folder, f))]
    # exclude those that contain "-non-". Those are the non-agentic notebooks
    subdirs = [f for f in subdirs if '-non-' not in f]
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
                print(f'Failed to run qualification test for {dandiset_id} {version} {subdir}')
                raise RuntimeError(f"Failed to run command: {cmd}")
        if not os.path.exists(qualification_test_fname):
            raise RuntimeError(f"Qualification test file {qualification_test_fname} does not exist even after running the command")
        with open(qualification_test_fname, 'r') as f:
            qualification_test = json.load(f)
            passing = qualification_test['passing']
            if passing:
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
            comparison_fname_A = f'{review_folder}/{subdir1}/comparisons/{subdir2}/comparison.json'
            comparison_fname_B = f'{review_folder}/{subdir2}/comparisons/{subdir1}/comparison.json'
            if os.path.exists(comparison_fname_A):
                with open(comparison_fname_A, 'r') as f:
                    comparison = json.load(f)
                selection = comparison['selection']
                comparison_results.append((
                    subdir1, subdir2, selection
                ))
            elif os.path.exists(comparison_fname_B):
                with open(comparison_fname_B, 'r') as f:
                    comparison = json.load(f)
                selection = comparison['selection']
                comparison_results.append((
                    subdir1, subdir2, 3 - selection
                ))

    while True:
        next_pair = suggest_next_comparison(
            nodes1=[i[0] for i in comparison_results],
            nodes2=[i[1] for i in comparison_results],
            selections=[i[2] for i in comparison_results],
            all_nodes=passing_subdirs
        )
        if next_pair is None:
            print("No more pairs to compare")
            break
        print(f"Next pair to compare: {next_pair}")
        subdir1, subdir2 = next_pair
        # randomly swap the two to avoid systematic bias
        if os.urandom(1)[0] % 2 == 0:
            subdir1, subdir2 = subdir2, subdir1
        # check to see if we already have this in the results
        for i1, i2, selection in comparison_results:
            if (i1 == subdir1 and i2 == subdir2) or (i1 == subdir2 and i2 == subdir1):
                raise RuntimeError(f"Comparison already exists for {subdir1} and {subdir2}")
        comparison_fname = f'{review_folder}/{subdir1}/comparisons/{subdir2}/comparison.json'
        if os.path.exists(comparison_fname):
            raise RuntimeError(f"Comparison file {comparison_fname} already exists")
        comparison_fname_other_way_around = f'{review_folder}/{subdir2}/comparisons/{subdir1}/comparison.json'
        if os.path.exists(comparison_fname_other_way_around):
            raise RuntimeError(f"Comparison file {comparison_fname_other_way_around} already exists (other way around)")
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
            if selection == 1:
                print(f"Selected {subdir1} over {subdir2}")
            elif selection == 2:
                print(f"Selected {subdir2} over {subdir1}")
            else:
                raise RuntimeError(f"Invalid selection {selection} for comparison between {subdir1} and {subdir2}")
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

    comparisons_md_fname = f'{review_folder}/comparisons.md'
    # Create comparisons.md
    print(f"\nWriting comparisons to markdown file...")
    with open(comparisons_md_fname, 'w') as f:
        f.write(f'# Comparisons for DANDI:{dandiset_id} {version}\n\n')
        f.write(f'Review model: {review_model}\n\n')
        f.write('| Notebook 1 | Notebook 2 | Selection |\n')
        f.write('|------------|------------|----------|\n')
        for subfolder1, subfolder2, selection in comparison_results:
            json_path = f'{subfolder1}/comparisons/{subfolder2}/comparison_thinking.md'
            f.write(f'| {subfolder1} | {subfolder2} | [{selection}]({json_path}) |\n')

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
