FROM python:3.8.1-buster

# Adding requirements file to current directory
# just this file first to cache the pip install step when code changes
COPY env_requirements.txt .

RUN pip --no-cache-dir install -r env_requirements.txt
#boto3 moto pandas black mypy pytest bump2version

# copy code itself from context to image
COPY . .

# install AWS CLI
RUN curl -s "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip" && \
	unzip -qq awscliv2.zip && \
	./aws/install && \
	rm -rf aws*

RUN apt update && apt install -y vim zip