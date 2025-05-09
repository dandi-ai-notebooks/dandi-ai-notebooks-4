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
