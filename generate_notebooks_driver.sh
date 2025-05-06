#!/bin/bash

DANDISET_ID=001361
VERSION=0.250406.0045

MODEL=google/gemini-2.0-flash-001

PROMPT=prompt-e-1
./scripts/generate_notebook.py --dandiset_id $DANDISET_ID --version $VERSION --model $MODEL --prompt $PROMPT

PROMPT=prompt-f-1
./scripts/generate_notebook.py --dandiset_id $DANDISET_ID --version $VERSION --model $MODEL --prompt $PROMPT

PROMPT=prompt-g-1
./scripts/generate_notebook.py --dandiset_id $DANDISET_ID --version $VERSION --model $MODEL --prompt $PROMPT


MODEL=google/gemini-2.5-pro-preview-03-25

PROMPT=prompt-e-1
./scripts/generate_notebook.py --dandiset_id $DANDISET_ID --version $VERSION --model $MODEL --prompt $PROMPT

PROMPT=prompt-f-1
./scripts/generate_notebook.py --dandiset_id $DANDISET_ID --version $VERSION --model $MODEL --prompt $PROMPT

PROMPT=prompt-g-1
./scripts/generate_notebook.py --dandiset_id $DANDISET_ID --version $VERSION --model $MODEL --prompt $PROMPT


MODEL=openai/o4-mini-high

PROMPT=prompt-e-1
./scripts/generate_notebook.py --dandiset_id $DANDISET_ID --version $VERSION --model $MODEL --prompt $PROMPT

PROMPT=prompt-f-1
./scripts/generate_notebook.py --dandiset_id $DANDISET_ID --version $VERSION --model $MODEL --prompt $PROMPT

PROMPT=prompt-g-1
./scripts/generate_notebook.py --dandiset_id $DANDISET_ID --version $VERSION --model $MODEL --prompt $PROMPT