#!/bin/bash

echo source /usr/share/bash-completion/completions/git >> /home/vscode/.bashrc;
poetry config virtualenvs.in-project true;
echo "Installing dependencies..." && poetry install;
