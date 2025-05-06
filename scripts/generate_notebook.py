#!/usr/bin/env python

import os
import argparse
import subprocess
from pathlib import Path
import shutil
import yaml
import click
from dotenv import load_dotenv

# Load environment variables from .env file if it exists
load_dotenv()

this_dir = Path(__file__).parent

def get_dandiset_repo_dir(dandiset_id: str) -> str:
    repo_url = f'https://github.com/dandi-ai-notebooks/{dandiset_id}'
    if not os.path.exists(this_dir / 'dandiset_repos'):
        os.makedirs(this_dir / 'dandiset_repos')
    dirname = this_dir / '..' / 'dandiset_repos' / dandiset_id
    if not dirname.exists():
        print(f"Cloning {repo_url} into {dirname}")
        cmd = f'git clone {repo_url} {dirname}'
        print(f"Running command: {cmd}")
        result = subprocess.run(cmd, shell=True)
        if result.returncode != 0:
            raise RuntimeError(f"Failed to clone {repo_url}")
    # pull the latest changes
    cmd = f'git -C {dirname} pull'
    print(f"Running command: {cmd}")
    result = subprocess.run(cmd, shell=True)
    if result.returncode != 0:
        raise RuntimeError(f"Failed to pull {repo_url}")
    return str(dirname)

def create_config(output_dir: str, model: str, prompt: str, dandiset_id: str, version: str):
    """Create the config.yaml file in the output directory."""
    config = {
        'model': model,
        'prompt': prompt,
        'dandiset_id': dandiset_id,
        'version': version,
    }
    with open(os.path.join(output_dir, 'config.yaml'), 'w') as f:
        yaml.dump(config, f)

def copy_template_files(output_dir: str, prompt: str):
    """Copy required template files to the output directory."""
    templates_dir = this_dir / 'templates' / 'generate_notebook'
    files_to_copy = [
        'tools.py',
        'tools_cli.py',
        'generate.py',
        f'{prompt}.txt'
    ]
    # read the prompt.txt to see if it mentions critique_dandiset_notebook.py
    with open(os.path.join(templates_dir, f'{prompt}.txt'), 'r') as f:
        prompt_content = f.read()
    if 'critique_dandiset_notebook.py' in prompt_content:
        files_to_copy.append('critique_dandiset_notebook.py')

    for file in files_to_copy:
        src = os.path.join(templates_dir, file)
        dst = os.path.join(output_dir, file)
        shutil.copy2(src, dst)


def generate_notebook_2(dandiset_id: str,
                        version: str,
                        model: str,
                        prompt: str,
                        notebook_dirname: str
):
    # Create the output directory and any necessary parent directories
    Path(notebook_dirname).mkdir(parents=True, exist_ok=True)

    # Create config.yaml
    create_config(notebook_dirname, model, prompt, dandiset_id, version)

    # Copy template files
    copy_template_files(notebook_dirname, prompt)

    # Run generate.py in the new directory
    try:
        subprocess.run(['python', 'generate.py'], cwd=notebook_dirname, check=True)
    except subprocess.CalledProcessError as e:
        click.echo(f"Error running generate.py: {e}", err=True)
        raise click.Abort()

def generate_notebook(*,
                      dandiset_id: str,
                      version: str,
                      model: str,
                      prompt: str
):
    dirname = get_dandiset_repo_dir(dandiset_id)
    model_second_part = model.split("/")[1]
    notebook_dirname = Path(dirname) / "v4" / f"{version}" / f"{model_second_part}-{prompt}"
    if os.path.exists(notebook_dirname):
        print(f"Directory {notebook_dirname} already exists, skipping generation")
        return
    generate_notebook_2(
        dandiset_id=dandiset_id,
        version=version,
        model=model,
        prompt=prompt,
        notebook_dirname=str(notebook_dirname)
    )

def main():
    parser = argparse.ArgumentParser(description="Generate a notebook for a Dandiset")
    parser.add_argument("--dandiset_id", type=str, required=True, help="Dandiset ID")
    parser.add_argument("--version", type=str, required=True, help="Dandiset Version")
    parser.add_argument("--model", type=str, required=True, help="LLM model name")
    parser.add_argument("--prompt", type=str, required=True, help="Prompt")
    args = parser.parse_args()
    generate_notebook(
        dandiset_id=args.dandiset_id,
        version=args.version,
        model=args.model,
        prompt=args.prompt
    )

if __name__ == "__main__":
    main()
