#!/bin/bash

# Bootstrap script for the maximum_security_dist repository
# Clones or updates the dist repo in ./.dist_repo

set -e  # Exit on any error

DIST_REPO_REMOTE="git@github.com:arikdcode/maximum_security_dist.git"

DIST_REPO_DIR=".dist_repo"

if [ ! -d "$DIST_REPO_DIR" ]; then
    echo "Cloning dist repo from $DIST_REPO_REMOTE..."
    git clone "$DIST_REPO_REMOTE" "$DIST_REPO_DIR"
    echo "Dist repo cloned successfully."
else
    echo "Dist repo already exists. Updating..."
    cd "$DIST_REPO_DIR"

    # Fetch latest changes
    git fetch origin

    # Try to checkout main branch, fall back to master if it doesn't exist
    if git show-ref --verify --quiet refs/remotes/origin/main; then
        git checkout main
        echo "Checked out main branch."
    elif git show-ref --verify --quiet refs/remotes/origin/master; then
        git checkout master
        echo "Checked out master branch."
    else
        echo "Error: Neither 'main' nor 'master' branch found in remote."
        exit 1
    fi

    # Pull latest changes
    git pull origin
    echo "Dist repo updated successfully."

    # Return to original directory
    cd ..
fi

echo "Dist repo is ready at $DIST_REPO_DIR"
