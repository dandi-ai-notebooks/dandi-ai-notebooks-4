#!/usr/bin/env python3

import json
import os
from pathlib import Path
from typing import Dict
import yaml

def process_qualification_test(file_path: str, rel_path: str) -> Dict:
    """Extract pass/fail result from qualification test file"""
    with open(file_path, 'r') as f:
        data = json.load(f)
    paths = rel_path.split('/')
    return {
        "type": "qualification_test",
        "model": paths[0],
        "dandiset_id": paths[2],
        "version": paths[3],
        "subfolder": paths[4],
        "passing": data.get("passing", False)
    }

def process_comparison_test(file_path: str, rel_path: str) -> Dict:
    """Extract selection from comparison test file"""
    with open(file_path, 'r') as f:
        data = json.load(f)
    paths = rel_path.split('/')
    return {
        "type": "comparison",
        "model": paths[0],
        "dandiset_id": paths[2],
        "version": paths[3],
        "subfolder1": paths[4],
        "subfolder2": paths[6],
        "selection": data.get("selection")
    }

def process_rankings(file_path: str, rel_path: str) -> Dict:
    """Extract rankings from rankings.json file"""
    with open(file_path, 'r') as f:
        data = json.load(f)
    paths = rel_path.split('/')
    return {
        "type": "rankings",
        "model": paths[0],
        "dandiset_id": paths[2],
        "version": paths[3],
        "notebooks": data.get("ranked_notebooks", [])
    }

def main():
    reviews_dir = Path("reviews")
    results = []

    # Recursively walk through reviews directory
    for root, _, files in os.walk(reviews_dir):
        root_path = Path(root)

        for file in files:
            if not file.endswith('.json'):
                continue

            file_path = root_path / file
            relative_path = file_path.relative_to(reviews_dir)

            if file == "qualification_test.json":
                result = process_qualification_test(str(file_path), str(relative_path))
                results.append(result)

            elif file == "comparison.json":
                result = process_comparison_test(str(file_path), str(relative_path))
                results.append(result)

            elif file == "rankings.json":
                result = process_rankings(str(file_path), str(relative_path))
                results.append(result)

    dandiset_repos_dir = Path("dandiset_repos")
    for dandiset_repo_dir in dandiset_repos_dir.iterdir():
        if not dandiset_repo_dir.is_dir():
            continue
        dandiset_id = dandiset_repo_dir.name
        ds_dir = dandiset_repo_dir / "v4"
        if not ds_dir.exists():
            continue
        for version_dir in ds_dir.iterdir():
            if not version_dir.is_dir():
                continue
            version = version_dir.name
            for subfolder in version_dir.iterdir():
                if not subfolder.is_dir():
                    continue
                config_fname = subfolder / "config.yaml"
                if not config_fname.exists():
                    continue
                with open(config_fname, 'r') as f:
                    config = yaml.safe_load(f)
                metadata_fname = subfolder / "metadata.json"
                if not metadata_fname.exists():
                    continue
                with open(metadata_fname, 'r') as f:
                    metadata = json.load(f)
                results.append({
                    "type": "notebook",
                    "url": f"https://github.com/dandi-ai-notebooks/{dandiset_id}/blob/main/v4/{version}/{subfolder.name}/{dandiset_id}.ipynb",
                    "dandiset_id": dandiset_id,
                    "version": version,
                    "model": config["model"],
                    "prompt": config["prompt"],
                    "metadata": metadata
                })

    # Write aggregated results
    output = {
        "results": results
    }

    print(f"Total qualification tests: {len([r for r in results if r['type'] == 'qualification_test'])}")
    print(f"Total passing qualification tests: {len([r for r in results if r['type'] == 'qualification_test' and r['passing']])}")
    print(f"Total comparison tests: {len([r for r in results if r['type'] == 'comparison'])}")
    print(f"Total rankings: {len([r for r in results if r['type'] == 'rankings'])}")

    print(f"Writing results to results.json...")
    with open('results.json', 'w') as f:
        json.dump(output, f, indent=2)

if __name__ == "__main__":
    main()
