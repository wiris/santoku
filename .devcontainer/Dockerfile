FROM python:3.8.1-buster

# Adding requirements file of the environment to the image
COPY requirements.txt /tmp/build/

RUN pip --no-cache-dir install -r /tmp/build/requirements.txt

# install AWS CLI
RUN curl -s "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip" && \
	unzip -qq awscliv2.zip && \
	./aws/install && \
	rm -rf aws*

RUN apt update && apt install -y vim zip