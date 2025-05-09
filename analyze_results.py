# %%

import json

# %%
with open('results.json') as f:
    X = json.load(f)
# %%
rankings_list = [x for x in X['results'] if x['type'] == 'rankings']
# %%

import pandas as pd
import numpy as np

# Get unique dandisets and notebook subfolders (only those ending in '-2')
dandisets = set()
subfolders = set()
for r in rankings_list:
    dandisets.add(r['dandiset_id'])
    for n in r['notebooks']:
        if n['subfolder'].endswith('-2'):
            subfolders.add(n['subfolder'])

# Create empty DataFrame with NaN values
df = pd.DataFrame(index=sorted(list(dandisets)), columns=sorted(list(subfolders)))
df.index.name = 'dandiset_id'

# Fill in rankings
for r in rankings_list:
    dandiset = r['dandiset_id']
    # Filter notebooks to only those ending in '-2' and get their relative rankings
    filtered_notebooks = [n for n in r['notebooks'] if n['subfolder'].endswith('-2')]
    # For each notebook, fill in its rank (1-based index in filtered list)
    for i, n in enumerate(filtered_notebooks):
        df.loc[dandiset, n['subfolder']] = i + 1

# %%
print("\nRankings table:")
print(df)

print("\nMean rankings:")
print(df.mean().sort_values())

print("\nNumber of times each notebook was ranked:")
print(df.count().sort_values(ascending=False))

# %%
import matplotlib.pyplot as plt

# Calculate mean rankings and sort
mean_rankings = df.mean().sort_values()

# Create horizontal bar plot
plt.figure(figsize=(10, 8))
bars = plt.barh(range(len(mean_rankings)), mean_rankings.values.astype(float))
plt.yticks(range(len(mean_rankings)), list(mean_rankings.index), ha='right')
plt.xlabel('Average Ranking (lower is better)')
plt.title('Average Rankings by Notebook Type')

# Add value labels to the right of each bar
for bar in bars:
    width = float(bar.get_width())
    plt.text(width, bar.get_y() + bar.get_height()/2.,
             f'{width:.2f}',
             ha='left', va='center')

plt.tight_layout()
plt.show()

# %%
# Count number of times each notebook was ranked #1
num_first_place = (df == 1).sum()
num_first_place = num_first_place.sort_values(ascending=False)

plt.figure(figsize=(10, 8))
bars = plt.barh(range(len(num_first_place)), num_first_place.values.astype(float))
plt.yticks(range(len(num_first_place)), list(num_first_place.index), ha='right')
plt.xlabel('Number of #1 Rankings')
plt.title('Number of Times Each Notebook Was Ranked #1')

# Add value labels to the right of each bar
for bar in bars:
    width = int(float(bar.get_width()))
    plt.text(width, bar.get_y() + bar.get_height()/2.,
             str(width),
             ha='left', va='center')

plt.tight_layout()
plt.show()

# %%
# Count number of times each notebook was ranked in top 3
num_top_3 = ((df <= 3) & (df > 0)).sum()  # df > 0 excludes NaN values
num_top_3 = num_top_3.sort_values(ascending=False)

plt.figure(figsize=(10, 8))
bars = plt.barh(range(len(num_top_3)), num_top_3.values.astype(float))
plt.yticks(range(len(num_top_3)), list(num_top_3.index), ha='right')
plt.xlabel('Number of Top 3 Rankings')
plt.title('Number of Times Each Notebook Was Ranked in Top 3')

# Add value labels to the right of each bar
for bar in bars:
    width = int(float(bar.get_width()))
    plt.text(width, bar.get_y() + bar.get_height()/2.,
             str(width),
             ha='left', va='center')

plt.tight_layout()
plt.show()

# %%
# Aggregate by prompt (e-2, f-2, g-2)
df_by_prompt = pd.DataFrame()

# Get mean rankings aggregated by prompt
for prompt in ['e-2', 'f-2', 'g-2']:
    prompt_cols = [col for col in df.columns if col.endswith(f'-prompt-{prompt}')]
    if prompt_cols:
        df_by_prompt[prompt] = df[prompt_cols].mean(axis=1)

# Calculate and plot mean rankings by prompt
mean_rankings_by_prompt = df_by_prompt.mean().sort_values()

plt.figure(figsize=(10, 4))
bars = plt.barh(range(len(mean_rankings_by_prompt)), mean_rankings_by_prompt.values.astype(float))
plt.yticks(range(len(mean_rankings_by_prompt)), list(mean_rankings_by_prompt.index), ha='right')
plt.xlabel('Average Ranking (lower is better)')
plt.title('Average Rankings by Prompt Type')

# Add value labels to the right of each bar
for bar in bars:
    width = float(bar.get_width())
    plt.text(width, bar.get_y() + bar.get_height()/2.,
             f'{width:.2f}',
             ha='left', va='center')

plt.tight_layout()
plt.show()

# Count number of times each prompt was ranked #1
num_first_by_prompt = {
    prompt: ((df[[col for col in df.columns if col.endswith(f'-prompt-{prompt}')]]) == 1).sum().sum()
    for prompt in ['e-2', 'f-2', 'g-2']
}
num_first_by_prompt = pd.Series(num_first_by_prompt).sort_values(ascending=False)

plt.figure(figsize=(10, 4))
bars = plt.barh(range(len(num_first_by_prompt)), num_first_by_prompt.values.astype(float))
plt.yticks(range(len(num_first_by_prompt)), list(num_first_by_prompt.index), ha='right')
plt.xlabel('Number of #1 Rankings')
plt.title('Number of Times Each Prompt Was Ranked #1')

# Add value labels to the right of each bar
for bar in bars:
    width = int(float(bar.get_width()))
    plt.text(width, bar.get_y() + bar.get_height()/2.,
             str(width),
             ha='left', va='center')

plt.tight_layout()
plt.show()

# Count number of times each prompt was ranked in top 3
num_top_3_by_prompt = {
    prompt: ((df[[col for col in df.columns if col.endswith(f'-prompt-{prompt}')]] <= 3) &
            (df[[col for col in df.columns if col.endswith(f'-prompt-{prompt}')]] > 0)).sum().sum()
    for prompt in ['e-2', 'f-2', 'g-2']
}
num_top_3_by_prompt = pd.Series(num_top_3_by_prompt).sort_values(ascending=False)

plt.figure(figsize=(10, 4))
bars = plt.barh(range(len(num_top_3_by_prompt)), num_top_3_by_prompt.values.astype(float))
plt.yticks(range(len(num_top_3_by_prompt)), list(num_top_3_by_prompt.index), ha='right')
plt.xlabel('Number of Top 3 Rankings')
plt.title('Number of Times Each Prompt Was Ranked in Top 3')

# Add value labels to the right of each bar
for bar in bars:
    width = int(float(bar.get_width()))
    plt.text(width, bar.get_y() + bar.get_height()/2.,
             str(width),
             ha='left', va='center')

plt.tight_layout()
plt.show()

# %%
# Aggregate by model (gpt-4.1, gemini-2.5-flash-preview, etc.)
df_by_model = pd.DataFrame()

# Function to extract model name from column
def get_model_name(col):
    parts = col.split('-prompt-')
    return parts[0]

# Get unique models
models = sorted(set(get_model_name(col) for col in df.columns))

# Get mean rankings aggregated by model
for model in models:
    model_cols = [col for col in df.columns if col.startswith(model)]
    if model_cols:
        df_by_model[model] = df[model_cols].mean(axis=1)

# Calculate and plot mean rankings by model
mean_rankings_by_model = df_by_model.mean().sort_values()

plt.figure(figsize=(10, 4))
bars = plt.barh(range(len(mean_rankings_by_model)), mean_rankings_by_model.values.astype(float))
plt.yticks(range(len(mean_rankings_by_model)), list(mean_rankings_by_model.index), ha='right')
plt.xlabel('Average Ranking (lower is better)')
plt.title('Average Rankings by Model')

# Add value labels to the right of each bar
for bar in bars:
    width = float(bar.get_width())
    plt.text(width, bar.get_y() + bar.get_height()/2.,
             f'{width:.2f}',
             ha='left', va='center')

plt.tight_layout()
plt.show()

# Count number of times each model was ranked #1
num_first_by_model = {
    model: ((df[[col for col in df.columns if col.startswith(model)]]) == 1).sum().sum()
    for model in models
}
num_first_by_model = pd.Series(num_first_by_model).sort_values(ascending=False)

plt.figure(figsize=(10, 4))
bars = plt.barh(range(len(num_first_by_model)), num_first_by_model.values.astype(float))
plt.yticks(range(len(num_first_by_model)), list(num_first_by_model.index), ha='right')
plt.xlabel('Number of #1 Rankings')
plt.title('Number of Times Each Model Was Ranked #1')

# Add value labels to the right of each bar
for bar in bars:
    width = int(float(bar.get_width()))
    plt.text(width, bar.get_y() + bar.get_height()/2.,
             str(width),
             ha='left', va='center')

plt.tight_layout()
plt.show()

# Count number of times each model was ranked in top 3
num_top_3_by_model = {
    model: ((df[[col for col in df.columns if col.startswith(model)]] <= 3) &
           (df[[col for col in df.columns if col.startswith(model)]] > 0)).sum().sum()
    for model in models
}
num_top_3_by_model = pd.Series(num_top_3_by_model).sort_values(ascending=False)

plt.figure(figsize=(10, 4))
bars = plt.barh(range(len(num_top_3_by_model)), num_top_3_by_model.values.astype(float))
plt.yticks(range(len(num_top_3_by_model)), list(num_top_3_by_model.index), ha='right')
plt.xlabel('Number of Top 3 Rankings')
plt.title('Number of Times Each Model Was Ranked in Top 3')

# Add value labels to the right of each bar
for bar in bars:
    width = int(float(bar.get_width()))
    plt.text(width, bar.get_y() + bar.get_height()/2.,
             str(width),
             ha='left', va='center')

plt.tight_layout()
plt.show()

# %%
