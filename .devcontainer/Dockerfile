FROM python:3.9-buster

# Adding requirements file of the environment to the image
COPY .devcontainer/requirements.txt /tmp/build/requirements-dev.txt
COPY requirements-test.txt /tmp/build/requirements-test.txt
COPY requirements.txt /tmp/build/requirements-santoku.txt

RUN pip install --upgrade pip

RUN pip --no-cache-dir install -r /tmp/build/requirements-dev.txt
RUN pip --no-cache-dir install -r /tmp/build/requirements-test.txt
RUN pip --no-cache-dir install -r /tmp/build/requirements-santoku.txt

# install AWS CLI
RUN curl -s "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip" && \
	unzip -qq awscliv2.zip && \
	./aws/install && \
	rm -rf aws*

RUN apt update && apt install -y vim zip ruby-dev rubygems