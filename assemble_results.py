#!/usr/bin/env python3

import json
import os
from pathlib import Path
from typing import Dict
import yaml

def process_qualification_test(file_path: str, rel_path: str, view_model: str) -> Dict:
    """Extract pass/fail result from qualification test file"""
    with open(file_path, 'r') as f:
        data = json.load(f)
    paths = rel_path.split('/')
    return {
        "type": "qualification_test",
        "model": paths[0],
        "dandiset_id": paths[1],
        "version": paths[2],
        "subfolder": paths[3],
        "passing": data.get("passing", False)
    }

def process_comparison_test(file_path: str, rel_path: str, review_model: str) -> Dict:
    """Extract selection from comparison test file"""
    with open(file_path, 'r') as f:
        data = json.load(f)
    paths = rel_path.split('/')
    return {
        "type": "comparison",
        "model": review_model,
        "dandiset_id": paths[1],
        "version": paths[2],
        "subfolder1": paths[3],
        "subfolder2": paths[5],
        "selection": data.get("selection")
    }

def process_human_veto(file_path: str, dandiset_id: str, version: str, subfolder: str, config: Dict) -> Dict:
    """Extract human veto records from yaml file"""
    with open(file_path, 'r') as f:
        data = yaml.safe_load(f)
    return {
        "type": "human_veto",
        "dandiset_id": dandiset_id,
        "version": version,
        "model": config["model"],
        "prompt": config["prompt"],
        "subfolder": subfolder,
        "vetoes": data
    }

def process_rankings(file_path: str, rel_path: str, review_model: str) -> Dict:
    """Extract rankings from rankings.json file"""
    with open(file_path, 'r') as f:
        data = json.load(f)
    paths = rel_path.split('/')
    return {
        "type": "rankings",
        "model": review_model,
        "dandiset_id": paths[1],
        "version": paths[2],
        "notebooks": data.get("ranked_notebooks", [])
    }

def main():
    review_model = "gemini-2.5-pro-preview"
    reviews_dir = Path(f"reviews/{review_model}")
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
                result = process_qualification_test(str(file_path), str(relative_path), review_model)
                results.append(result)

            elif file == "comparison.json":
                result = process_comparison_test(str(file_path), str(relative_path), review_model)
                results.append(result)

            elif file == "rankings.json":
                result = process_rankings(str(file_path), str(relative_path), review_model)
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
                if not str(subfolder).endswith("-2"):
                    continue
                config_fname = subfolder / "config.yaml"
                if not config_fname.exists():
                    raise Exception(f"Config file {config_fname} does not exist")
                    continue
                with open(config_fname, 'r') as f:
                    config = yaml.safe_load(f)
                metadata_fname = subfolder / "metadata.json"
                if not metadata_fname.exists():
                    print(f'==== Metadata file {metadata_fname} does not exist. Skipping.')
                    continue
                with open(metadata_fname, 'r') as f:
                    metadata = json.load(f)

                # Check for human veto file
                human_veto_fname = subfolder / "human_veto.yaml"
                if human_veto_fname.exists():
                    result = process_human_veto(
                        str(human_veto_fname),
                        dandiset_id,
                        version,
                        subfolder.name,
                        config
                    )
                    results.append(result)

                results.append({
                    "type": "notebook",
                    "url": f"https://github.com/dandi-ai-notebooks/{dandiset_id}/blob/main/v4/{version}/{subfolder.name}/{dandiset_id}.ipynb",
                    "dandiset_id": dandiset_id,
                    "version": version,
                    "model": config["model"],
                    "prompt": config["prompt"],
                    "subfolder": subfolder.name,
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
    print(f"Total human veto records: {len([r for r in results if r['type'] == 'human_veto'])}")

    print(f"Writing results to results.json...")
    with open('results.json', 'w') as f:
        json.dump(output, f, indent=2)

if __name__ == "__main__":
    main()
