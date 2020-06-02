#!/bin/sh

setup_git() {
  git config --global user.email "travis@travis-ci.org"
  git config --global user.name "Travis CI"
  
  git remote rm origin
  # change this
  git remote add origin https://CHANGETHIS:${GH_TOKEN}@github.com/wiris/santoku.git > /dev/null 2>&1
}

bump_version() {
  git checkout develop
  # this makes a commit and tags it with the version
  bump2version minor --allow-dirty --verbose --tag-name 'v{new_version}' --message "[skip ci] Bump to v{new_version}"
}

merge() {
  git checkout -B master
  git merge --no-ff -m "[skip ci] merging 'develop' into 'master'" develop 
}

push_changes() {
  git push --quiet origin master stable --tags 
}

setup_git
bump_version
merge
push_changes