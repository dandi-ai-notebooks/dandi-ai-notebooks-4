#!/bin/bash

cd dandiset_repos || exit

for dir in */; do
  if [ -d "$dir" ]; then
    echo "Pulling $dir..."
    cd "$dir" || continue
    git pull
    cd ..
  fi
done
