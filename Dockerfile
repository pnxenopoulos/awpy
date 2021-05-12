# Use Ubuntu image.
FROM ubuntu:20.04

# Allow statements and log messages to immediately appear in the Knative logs
ENV PYTHONUNBUFFERED True
ENV DEBIAN_FRONTEND=noninteractive

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
RUN wget -nv https://golang.org/dl/go1.16.linux-amd64.tar.gz
RUN tar -C /usr/local -xzf go1.16.linux-amd64.tar.gz
ENV PATH="${PATH}:/usr/local/go/bin"

# Copy local code to the container image.
ENV LIB_HOME /csgo-testing
WORKDIR $LIB_HOME
COPY . ./
RUN pip3 install -r requirements.txt

# Get file for local tests
RUN wget -O -nv tests/og-vs-natus-vincere-m1-dust2.dem https://storage.googleapis.com/csgo-tests/og-vs-natus-vincere-m1-dust2.dem

# Run tests
ENTRYPOINT ["/run_tests.sh"]