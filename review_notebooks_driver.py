#!/usr/bin/env python

import os
import json
from pathlib import Path

this_dir = Path(__file__).parent

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
    for i1, subdir1 in enumerate(passing_subdirs):
        for i2, subdir2 in enumerate(passing_subdirs):
            if i1 >= i2:
                continue
            comparison_fname = f'{review_folder}/{subdir1}/comparisons/{subdir2}/comparison.json'
            if os.path.exists(comparison_fname):
                print(f"Comparison file {comparison_fname} exists")
                continue
            cmd = f'./scripts/comparison.py --dandiset_id {dandiset_id} --version {version} --model {review_model} --subfolder1_name {subdir1} --subfolder2_name {subdir2}'
            print(f"Running command: {cmd}")
            result = os.system(cmd)
            if result != 0:
                raise RuntimeError(f"Failed to run command: {cmd}")
            if not os.path.exists(comparison_fname):
                raise RuntimeError(f"Comparison file {comparison_fname} does not exist even after running the command")

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
