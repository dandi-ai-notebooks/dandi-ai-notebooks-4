#!/usr/bin/env python3

from typing import List, Dict, Any, Tuple
import os
import time
import platform
import json
from pathlib import Path
from helpers.run_completion import run_completion

this_dir = Path(__file__).parent

def get_notebook_path(*, dandiset_id: str, version: str, subfolder_name: str) -> str | None:
    p = f'{this_dir}/../dandiset_repos/{dandiset_id}/v4/{version}/{subfolder_name}/{dandiset_id}.ipynb'
    if not os.path.exists(p):
        return None
    return p

def create_message_content_for_cell(cell: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Create user message content for a given cell."""
    content: List[Dict[str, Any]] = []
    if cell["cell_type"] == "markdown":
        markdown_source = cell["source"]
        content.append(
            {"type": "text", "text": "INPUT-MARKDOWN: " + "".join(markdown_source)}
        )
    elif cell["cell_type"] == "code":
        code_source = cell["source"]
        content.append({"type": "text", "text": "INPUT-CODE: " + "".join(code_source)})
        for x in cell["outputs"]:
            output_type = x["output_type"]
            if output_type == "stream":
                content.append(
                    {"type": "text", "text": "OUTPUT-TEXT: " + "\n".join(x["text"])}
                )
            elif output_type == "display_data" or output_type == "execute_result":
                if "image/png" in x["data"]:
                    png_base64 = x["data"]["image/png"]
                    image_data_url = f"data:image/png;base64,{png_base64}"
                    content.append({"type": "text", "text": "OUTPUT-IMAGE:"})
                    content.append(
                        {"type": "image_url", "image_url": {"url": image_data_url}}
                    )
                elif "text/plain" in x["data"]:
                    content.append(
                        {
                            "type": "text",
                            "text": "OUTPUT-TEXT: " + "".join(x["data"]["text/plain"]),
                        }
                    )
                elif "text/html" in x["data"]:
                    content.append(
                        {
                            "type": "text",
                            "text": "OUTPUT-TEXT: " + "".join(x["data"]["text/html"]),
                        }
                    )
                else:
                    print(
                        f"Warning: got output type {output_type} but no image/png data or text/plain or text/html"
                    )
            else:
                print(f"Warning: unsupported output type {output_type}")
    else:
        print(f'Warning: unsupported cell type {cell["cell_type"]}')
        content.append({"type": "text", "text": "Unsupported cell type"})
    return content

def read_template_prompt(name: str):
    template_path = (
        Path(__file__).parent / "templates" / "comparison" / name
    )
    with open(template_path, "r") as f:
        content = f.read()
    return content

def parse_comparison_response(comparison_response: str) -> Tuple[str, int]:
    i1 = comparison_response.find("<thinking>")
    i2 = comparison_response.find("</thinking>")
    if i1 == -1 or i2 == -1:
        print(comparison_response)
        raise ValueError("Invalid response text: <thinking> tag not found")
    thinking = comparison_response[i1 + len("<thinking>"):i2].strip()
    i1 = comparison_response.find("<selection>")
    i2 = comparison_response.find("</selection>")
    if i1 == -1 or i2 == -1:
        print(comparison_response)
        raise ValueError("Invalid response text: <selection> tag not found")
    selection_str = comparison_response[i1 + len("<selection>"):i2].strip()
    if selection_str == '1':
        selection = 1
    elif selection_str == '2':
        selection = 2
    else:
        print(comparison_response)
        raise ValueError("Invalid selection text")
    return thinking, selection

def run_comparison_test_for_notebooks(*, notebook1_path: str, notebook2_path: str, model: str):
    with open(notebook1_path, 'r') as f:
        notebook1 = json.load(f)
    with open(notebook2_path, 'r') as f:
        notebook2 = json.load(f)
    cells1 = notebook1.get('cells', [])
    cells2 = notebook2.get('cells', [])
    total_prompt_tokens = 0
    total_completion_tokens = 0
    system_prompt = read_template_prompt("comparison_system_message.txt")

    messages: List[Dict[str, Any]] = [
        {
            "role": "system",
            "content": system_prompt,
        }
    ]
    for notebook_num in range(1, 2 + 1):
        messages.append({
            "role": "user",
            "content": f"BEGIN NOTEBOOK {notebook_num} CONTENT",
        })
        cells = cells1 if notebook_num == 1 else cells2
        for cell in cells:
            if cell["cell_type"] not in ["code", "markdown"]:
                continue
            cell_content = create_message_content_for_cell(cell)
            messages.append(
                {
                    "role": "user",
                    "content": cell_content,
                }
            )
        messages.append({
            "role": "user",
            "content": f"END NOTEBOOK {notebook_num} CONTENT",
        })

    user_message = read_template_prompt("comparison_user_message.txt")
    messages.append(
        {
            "role": "user",
            "content": user_message,
        }
    )

    comparison_response, new_messages, prompt_tokens, completion_tokens = (
        run_completion(messages=messages, model=model)
    )
    total_prompt_tokens += prompt_tokens
    total_completion_tokens += completion_tokens
    messages = new_messages # very important to update messages with the new messages from the model

    thinking, selection = parse_comparison_response(comparison_response)

    return {
        "thinking": thinking,
        "selection": selection,
        "total_prompt_tokens": total_prompt_tokens,
        "total_completion_tokens": total_completion_tokens,
        "metadata": {
            "model": model,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "system_info": {"platform": platform.platform(), "hostname": platform.node()}
        }
    }


def run_comparison(*, model: str, dandiset_id: str, version: str, subfolder1_name: str, subfolder2_name: str) -> Dict[str, Any]:
    notebook1_path = get_notebook_path(dandiset_id=dandiset_id, version=version, subfolder_name=subfolder1_name)
    notebook2_path = get_notebook_path(dandiset_id=dandiset_id, version=version, subfolder_name=subfolder2_name)
    if notebook1_path is None:
        raise ValueError(f"Notebook not found at {notebook1_path}")
    if notebook2_path is None:
        raise ValueError(f"Notebook not found at {notebook2_path}")
    return run_comparison_test_for_notebooks(notebook1_path=notebook1_path, notebook2_path=notebook2_path, model=model)

def main():
    # get dandiset_id, version, subfolder_name, model from command line arguments
    import argparse
    parser = argparse.ArgumentParser(description="Run comparison between notebooks.")
    parser.add_argument("--dandiset_id", type=str, required=True, help="Dandiset ID")
    parser.add_argument("--version", type=str, required=True, help="Dandiset Version")
    parser.add_argument("--subfolder1_name", type=str, required=True, help="Subfolder 1 name")
    parser.add_argument("--subfolder2_name", type=str, required=True, help="Subfolder 2 name")
    parser.add_argument("--model", type=str, required=True, help="Model name")
    args = parser.parse_args()
    dandiset_id = args.dandiset_id
    version = args.version
    subfolder1_name = args.subfolder1_name
    subfolder2_name = args.subfolder2_name
    model = args.model
    this_dir = Path(__file__).parent
    model_second_part = model.split("/")[1]
    comparison_result_path = f'{this_dir}/../reviews/{model_second_part}/dandisets/{dandiset_id}/{version}/{subfolder1_name}/comparisons/{subfolder2_name}/comparison.json'
    comparison_result_thinking_path = f'{this_dir}/../reviews/{model_second_part}/dandisets/{dandiset_id}/{version}/{subfolder1_name}/comparisons/{subfolder2_name}/comparison_thinking.md'
    # make sure parent directory exists
    os.makedirs(os.path.dirname(comparison_result_path), exist_ok=True)
    if os.path.exists(comparison_result_path):
        print("Comparison result already exists. Loading from file...")
        with open(comparison_result_path, 'r') as f:
            result = json.load(f)
    else:
        result = run_comparison(model=model, dandiset_id=dandiset_id, version=version, subfolder1_name=subfolder1_name, subfolder2_name=subfolder2_name)
        with open(comparison_result_path, 'w') as f:
            json.dump(result, f, indent=4)
        with open(comparison_result_thinking_path, 'w') as f:
            f.write(result["thinking"])

    print("Thinking:")
    print(result["thinking"])
    print("")
    print(f"Selection: {result['selection']}")
    print("")
    print(f"Total Prompt Tokens: {result['total_prompt_tokens']}")
    print(f"Total Completion Tokens: {result['total_completion_tokens']}")

if __name__ == "__main__":
    main()
