# Use Ubuntu image.
FROM ubuntu:20.04

# Allow statements and log messages to immediately appear in the Knative logs
ENV PYTHONUNBUFFERED True
ENV DEBIAN_FRONTEND=noninteractive

# Update
RUN apt-get -y update

# Install git
RUN apt-get install -y git

# Install wget
RUN apt-get install -y wget

# Install pip
RUN apt-get install -y python3-pip

# Install testing stuff
RUN pip install pytest
RUN pip install codecov
RUN pip install pytest-cov

# Install Golang>=1.14
RUN wget https://golang.org/dl/go1.16.linux-amd64.tar.gz
RUN tar -C /usr/local -xzf go1.16.linux-amd64.tar.gz
ENV PATH="${PATH}:/usr/local/go/bin"

# Copy local code to the container image.
ENV LIB_HOME /csgo-testing
WORKDIR $LIB_HOME
COPY . ./
RUN pip3 install -r requirements.txt

# Get associated files
WORKDIR  $LIB_HOME/tests

# Go back to LIB_HOME
WORKDIR $LIB_HOME

# Run tests
RUN /run_tests.sh

# Run tests
ENTRYPOINT ["/run_tests.sh"]