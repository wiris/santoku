FROM python:3.8-buster

# install AWS CLI
RUN curl -s "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip" && \
	unzip -qq awscliv2.zip && \
	./aws/install && \
	rm -rf aws*

RUN apt update && apt install -y vim zip ruby-dev rubygems

# Install poetry
RUN curl -sSL https://raw.githubusercontent.com/python-poetry/poetry/master/get-poetry.py | python - 
ENV PATH "/root/.poetry/bin:$PATH"

# Install dependencies via poetry
ENV POETRY_LOCATION=/workspaces/santoku \
	POETRY_VIRTUALENVS_IN_PROJECT=true
WORKDIR $POETRY_LOCATION
COPY pyproject.toml $POETRY_LOCATION
