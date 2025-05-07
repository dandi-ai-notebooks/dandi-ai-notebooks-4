#!/usr/bin/env python3

from typing import List, Dict, Any
import os
import time
import platform
import json
from pathlib import Path
from helpers.run_completion import run_completion
from html import escape as html_escape
import re

class XMLParsingError(Exception):
    """Custom exception for XML parsing errors."""
    pass


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
        Path(__file__).parent / "templates" / "qualification_test" / name
    )
    with open(template_path, "r") as f:
        content = f.read()
    return content

def escape_xml_chars(xml_text: str) -> str:
    """
    Escape '<' and '>' everywhere *except* inside our whitelisted tags.
    """
    _ALLOWED_TAGS = [
        '<grade>', '</grade>',
        '<review>', '</review>',
        '<thinking>', '</thinking>',
    ]
    _PLACEHOLDER = '__TAG_{:02d}__'
    _PLACEHOLDER_RE = re.compile(r'__TAG_(\d{2})__')
    # 1 . swap each allowed tag for a unique placeholder
    for i, tag in enumerate(_ALLOWED_TAGS):
        xml_text = xml_text.replace(tag, _PLACEHOLDER.format(i))

    # 2 . escape everything that remains
    xml_text = html_escape(xml_text, quote=False)   # keeps & and quotes unchanged

    # 3 . put the real tags back
    def _restore(match: re.Match) -> str:
        return _ALLOWED_TAGS[int(match.group(1))]

    return _PLACEHOLDER_RE.sub(_restore, xml_text)

def parse_review_xml(xml_text: str):
    # Escape < and > characters not part of our tags before wrapping
    escaped_xml = escape_xml_chars(xml_text)
    i1 = escaped_xml.find("<review>")
    i2 = escaped_xml.find("</review>")
    if i1 == -1 or i2 == -1:
        raise XMLParsingError("Invalid response text: <review> tag not found")
    review_text = escaped_xml[i1 + len("<review>"):i2].strip()
    i1 = review_text.find("<thinking>")
    i2 = review_text.find("</thinking>")
    if i1 == -1 or i2 == -1:
        raise XMLParsingError("Invalid response text: <thinking> tag not found")
    thinking = review_text[i1 + len("<thinking>"):i2].strip()
    i1 = review_text.find("<grade>")
    i2 = review_text.find("</grade>")
    if i1 == -1 or i2 == -1:
        raise XMLParsingError("Invalid response text: <grade> tag not found")
    grade_text = review_text[i1 + len("<grade>"):i2].strip().upper()
    if grade_text not in ["PASS", "FAIL"]:
        raise XMLParsingError(f"Invalid grade text: {grade_text}")
    if grade_text == "PASS":
        passing = True
    else:
        passing = False
    return passing, thinking

def run_qualification_test_for_notebook(*, notebook_path: str, model: str):
    with open(notebook_path, 'r') as f:
        notebook = json.load(f)
    cells = notebook.get('cells', [])
    total_prompt_tokens = 0
    total_completion_tokens = 0
    system_prompt = read_template_prompt("qualification_test_system_message.txt")

    messages: List[Dict[str, Any]] = [
        {
            "role": "system",
            "content": system_prompt,
        }
    ]
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

    user_message_1 = read_template_prompt("qualification_test_user_message_1.txt")
    messages.append(
        {
            "role": "user",
            "content": user_message_1,
        }
    )

    image_descriptions, new_messages, prompt_tokens, completion_tokens = (
        run_completion(messages=messages, model=model)
    )
    total_prompt_tokens += prompt_tokens
    total_completion_tokens += completion_tokens
    messages = new_messages # very important to update messages with the new messages from the model

    user_message_2 = read_template_prompt("qualification_test_user_message_2.txt")
    messages.append(
        {
            "role": "user",
            "content": user_message_2,
        }
    )
    qualification_test_response, new_messages, prompt_tokens, completion_tokens = (
        run_completion(messages=messages, model=model)
    )
    total_prompt_tokens += prompt_tokens
    total_completion_tokens += completion_tokens
    messages = new_messages

    # Parse rankings text into structured format
    try:
        passing, thinking = parse_review_xml(qualification_test_response)
    except XMLParsingError as e:
        print(f"Error parsing grades: {str(e)}")
        print(qualification_test_response)
        raise Exception(f"Failed to parse grades: {str(e)}")

    return {
        "image_descriptions": image_descriptions,
        "total_prompt_tokens": total_prompt_tokens,
        "total_completion_tokens": total_completion_tokens,
        "thinking": thinking,
        "passing": passing,
        "metadata": {
            "model": model,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "system_info": {"platform": platform.platform(), "hostname": platform.node()}
        }
    }


def run_qualification_test(*, model: str, dandiset_id: str, version: str, subfolder_name: str):
    notebook_path = get_notebook_path(dandiset_id=dandiset_id, version=version, subfolder_name=subfolder_name)
    if notebook_path is None:
        raise ValueError(f"Notebook not found at {notebook_path}")
    return run_qualification_test_for_notebook(notebook_path=notebook_path, model=model)

def main():
    # get dandiset_id, subfolder_name, model from command line arguments
    import argparse
    parser = argparse.ArgumentParser(description="Run qualification test for a notebook.")
    parser.add_argument("--dandiset_id", type=str, required=True, help="Dandiset ID")
    parser.add_argument("--version", type=str, required=True, help="Version")
    parser.add_argument("--subfolder_name", type=str, required=True, help="Subfolder name")
    parser.add_argument("--model", type=str, required=True, help="Model name")
    args = parser.parse_args()
    dandiset_id = args.dandiset_id
    version = args.version
    subfolder_name = args.subfolder_name
    model = args.model
    this_dir = Path(__file__).parent
    model_second_part = model.split("/")[1]
    test_result_path = f'{this_dir}/../reviews/{model_second_part}/dandisets/{dandiset_id}/{version}/{subfolder_name}/qualification_test.json'
    # make sure parent directory exists
    os.makedirs(os.path.dirname(test_result_path), exist_ok=True)
    if os.path.exists(test_result_path):
        print("Qualification test result already exists. Loading from file...")
        with open(test_result_path, 'r') as f:
            result = json.load(f)
    else:
        result = run_qualification_test(model=model, dandiset_id=dandiset_id, version=version, subfolder_name=subfolder_name)
        with open(test_result_path, 'w') as f:
            json.dump(result, f, indent=4)
        thinking_output_path = f'{this_dir}/../reviews/{model_second_part}/dandisets/{dandiset_id}/{version}/{subfolder_name}/qualification_test_thinking.md'
        with open(thinking_output_path, 'w') as f:
            f.write(result["thinking"])
    print("Image Descriptions:")
    print(result["image_descriptions"])
    print("")
    print("Thinking:")
    print(result["thinking"])
    print("")
    print("Passing:", result["passing"])
    print("")
    print(f"Total Prompt Tokens: {result['total_prompt_tokens']}")
    print(f"Total Completion Tokens: {result['total_completion_tokens']}")

if __name__ == "__main__":
    main()
