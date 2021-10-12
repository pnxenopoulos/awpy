# Use Ubuntu image.
FROM ubuntu:20.04

# Allow statements and log messages to immediately appear in the Knative logs
ENV PYTHONUNBUFFERED True
ENV DEBIAN_FRONTEND=noninteractive

# Update, install git, wget, pip
RUN apt-get -q update && apt-get install -y git && apt-get install -y wget && apt-get install -y python3-pip 

# Install testing stuff
RUN pip install pytest
RUN pip install codecov
RUN pip install pytest-cov

# Install Golang>=1.14
RUN wget -nv https://golang.org/dl/go1.16.linux-amd64.tar.gz
RUN tar -C /usr/local -xzf go1.16.linux-amd64.tar.gz
ENV PATH="${PATH}:/usr/local/go/bin"

# Copy local code to the container image.
ENV LIB_HOME /csgo-testing
WORKDIR $LIB_HOME
COPY . ./
RUN pip3 install -r requirements.txt

# Run tests
ENTRYPOINT ["./run_tests.sh"]