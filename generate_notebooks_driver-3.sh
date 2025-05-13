#!/bin/bash

DANDISET_IDS_AND_VERSIONS=(
    "001433 0.250507.2356"
    "001195 0.250408.1733"
    "001375 0.250406.1855"
    "001361 0.250406.0045"
    "001359 0.250401.1603"
    "001174 0.250331.2218"
    "001333 0.250327.2220"
    "000690 0.250326.0015"
    "001366 0.250324.1603"
    "000617 0.250312.0130"
    "001354 0.250312.0036"
    "000563 0.250311.2145"
)

for entry in "${DANDISET_IDS_AND_VERSIONS[@]}"; do
    IFS=' ' read -r DANDISET_ID VERSION <<< "$entry"

    # MODEL=google/gemini-2.5-flash-preview
    # MODEL=google/gemini-2.5-pro-preview
    # MODEL=openai/o4-mini-high
    MODEL=openai/gpt-4.1
    # MODEL=anthropic/claude-3.7-sonnet

    # non-agentic
    PROMPT=prompt-non-2
    ./scripts/generate_notebook.py --dandiset_id $DANDISET_ID --version $VERSION --model $MODEL --prompt $PROMPT

    # no exploration
    PROMPT=prompt-e-2
    ./scripts/generate_notebook.py --dandiset_id $DANDISET_ID --version $VERSION --model $MODEL --prompt $PROMPT

    # exploration
    PROMPT=prompt-f-2
    ./scripts/generate_notebook.py --dandiset_id $DANDISET_ID --version $VERSION --model $MODEL --prompt $PROMPT

    # exploration + critique
    PROMPT=prompt-g-2
    ./scripts/generate_notebook.py --dandiset_id $DANDISET_ID --version $VERSION --model $MODEL --prompt $PROMPT
done
