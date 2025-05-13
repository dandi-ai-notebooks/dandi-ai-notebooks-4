import os
import json
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# Create figures directory if it doesn't exist
os.makedirs('figures', exist_ok=True)

# Set publication-quality plot style
plt.style.use('seaborn-v0_8-paper')
plt.rcParams.update({
    'font.size': 12,
    'axes.labelsize': 12,
    'axes.titlesize': 14,
    'xtick.labelsize': 10,
    'ytick.labelsize': 10,
    'legend.fontsize': 10,
    'figure.titlesize': 14,
    'figure.dpi': 300,
    'savefig.dpi': 300,
    'savefig.bbox': 'tight',
    'savefig.pad_inches': 0.1
})

# Load results
with open('results.json') as f:
    X = json.load(f)

# Process qualification test results
qualification_tests = [x for x in X['results'] if x['type'] == 'qualification_test']
pass_fail_counts = {}

for test in qualification_tests:
    model = test['model']
    subfolder = test['subfolder']
    if not subfolder.endswith('-2'):  # Only include -2 prompts
        continue
    key = f"{model}-{subfolder}"

    if key not in pass_fail_counts:
        pass_fail_counts[key] = {'pass': 0, 'fail': 0}

    if test['passing']:
        pass_fail_counts[key]['pass'] = pass_fail_counts[key]['pass'] + 1
    else:
        pass_fail_counts[key]['fail'] = pass_fail_counts[key]['fail'] + 1

def clean_model_name(name):
    # Remove 'dandisets-' prefix if present
    return name.replace('dandisets-', '')

# Convert counts to DataFrame with formatted model/prompt names
prompt_map = {'e-2': 'A', 'f-2': 'B', 'g-2': 'C'}
formatted_counts = {}
for key, counts in pass_fail_counts.items():
    model, prompt = key.rsplit('-prompt-', 1)
    model = clean_model_name(model)
    new_key = f"{model} {prompt_map[prompt]}"
    formatted_counts[new_key] = counts

pass_fail_df = pd.DataFrame.from_dict(formatted_counts, orient='index')
pass_fail_df.sort_index(inplace=True)

# Plot 1: Qualification Test Results
plt.figure(figsize=(12, 8))
ax = pass_fail_df.plot(kind='barh', stacked=True)
plt.title('Qualification Test Results by Model/Prompt', pad=20)
plt.xlabel('Number of Tests')
plt.ylabel('Model-Prompt Combination')

# Add value labels on the bars
for c in pass_fail_df.columns:
    vals = pass_fail_df[c]
    xpos = vals/2 if c == 'pass' else pass_fail_df['pass'] + vals/2
    for i, (v, x) in enumerate(zip(vals, xpos)):
        if v != 0:
            plt.text(x, i, str(int(v)), ha='center', va='center')

plt.tight_layout()
plt.savefig('figures/qualification_test_results.png')
plt.close()

# Process rankings
rankings_list = [x for x in X['results'] if x['type'] == 'rankings']

# Get unique dandisets and notebook subfolders
dandisets = set()
subfolders = set()
for r in rankings_list:
    dandisets.add(r['dandiset_id'])
    for n in r['notebooks']:
        if n['subfolder'].endswith('-2'):
            subfolders.add(n['subfolder'])

# Create rankings DataFrame
df = pd.DataFrame(index=sorted(list(dandisets)), columns=sorted(list(subfolders)))
df.index.name = 'dandiset_id'

# Fill in rankings
for r in rankings_list:
    dandiset = r['dandiset_id']
    filtered_notebooks = [n for n in r['notebooks'] if n['subfolder'].endswith('-2')]
    for i, n in enumerate(filtered_notebooks):
        df.loc[dandiset, n['subfolder']] = i + 1

# Plot 2: Top Rankings by Model/Prompt Pair
num_first_place = (df == 1).sum().sort_values(ascending=True)

plt.figure(figsize=(12, 8))
bars = plt.barh(range(len(num_first_place)), num_first_place.values.astype(float))
# Clean model names in the labels
cleaned_labels = [label.replace('dandisets-', '') for label in num_first_place.index]
plt.yticks(range(len(num_first_place)), cleaned_labels)
plt.xlabel('Number of #1 Rankings')
plt.title('Number of Times Each Model/Prompt Was Ranked #1', pad=20)

# Add value labels
for bar in bars:
    width = int(bar.get_width())
    plt.text(width, bar.get_y() + bar.get_height()/2,
             str(width), ha='left', va='center')

plt.tight_layout()
plt.savefig('figures/top_rankings_by_model_prompt.png')
plt.close()

# Plot 3: Top Rankings by Model
def get_model_name(col):
    parts = col.split('-prompt-')
    return parts[0]

# Get unique models
models = sorted(set(get_model_name(col) for col in df.columns))

# Count number of times each model was ranked #1
num_first_by_model = {
    model: ((df[[col for col in df.columns if col.startswith(model)]]) == 1).sum().sum()
    for model in models
}
num_first_by_model = pd.Series(num_first_by_model).sort_values(ascending=True)

plt.figure(figsize=(12, 6))
bars = plt.barh(range(len(num_first_by_model)), num_first_by_model.values.astype(float))
# Clean model names in the labels
cleaned_labels = [clean_model_name(label) for label in num_first_by_model.index]
plt.yticks(range(len(num_first_by_model)), cleaned_labels)
plt.xlabel('Number of #1 Rankings')
plt.title('Number of Times Each Model Was Ranked #1', pad=20)

# Add value labels
for bar in bars:
    width = int(bar.get_width())
    plt.text(width, bar.get_y() + bar.get_height()/2,
             str(width), ha='left', va='center')

plt.tight_layout()
plt.savefig('figures/top_rankings_by_model.png')
plt.close()

# Plot 4: Top Rankings by Prompt
prompt_mapping = {
    'e-2': 'A',
    'f-2': 'B',
    'g-2': 'C'
}

# Count number of times each prompt was ranked #1
num_first_by_prompt = {
    prompt_mapping[prompt]: ((df[[col for col in df.columns if col.endswith(f'-prompt-{prompt}')]]) == 1).sum().sum()
    for prompt in ['e-2', 'f-2', 'g-2']
}
num_first_by_prompt = pd.Series(num_first_by_prompt).sort_values(ascending=True)

plt.figure(figsize=(12, 4))
bars = plt.barh(range(len(num_first_by_prompt)), num_first_by_prompt.values.astype(float))
plt.yticks(range(len(num_first_by_prompt)), list(num_first_by_prompt.index))
plt.xlabel('Number of #1 Rankings')
plt.title('Number of Times Each Prompt Was Ranked #1', pad=20)

# Add value labels
for bar in bars:
    width = int(bar.get_width())
    plt.text(width, bar.get_y() + bar.get_height()/2,
             str(width), ha='left', va='center')

plt.tight_layout()
plt.savefig('figures/top_rankings_by_prompt.png')
plt.close()
