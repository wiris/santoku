#!/bin/bash

set -o errexit
set -o pipefail

# based on: https://gist.github.com/willprice/e07efd73fb7f13f917ea
setup_git() {
  git config --global user.email "cicd@wiris.com"
  git config --global user.name "wiris-ci-bot"
  
  git remote rm origin
  git remote add origin https://${GH_TOKEN}@github.com/wiris/santoku.git > /dev/null 2>&1
}

bump_version() {
  git checkout master

  CURRENT_BUILD_NUM="$(awk -F"." '/version=/{print gsub($2, "\",")}' setup.py)"
  # set version using calver YYMMDD.buildno
  NEW_VERSION="$(date +%y%m%d).$((CURRENT_BUILD_NUM+1))"

  sed -i "s/version=.*/version=\"${NEW_VERSION}\",/g" setup.py

  git commit -am "[skip ci] Bump to ${NEW_VERSION}"
  git tag -a "${NEW_VERSION}" -m "version ${NEW_VERSION}"
}

push_changes() {
  git push --quiet origin master --tags 
}

setup_git
bump_version
push_changes