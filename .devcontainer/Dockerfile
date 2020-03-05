FROM python:3.8.1-buster

RUN pip --no-cache-dir install -U boto3 moto pandas black mypy pytest

# install AWS CLI
RUN curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip" && \
	unzip awscliv2.zip && \
	./aws/install &&
	rm -rf aws*