# SANDBOX IMAGE
FROM python:3.11-slim

WORKDIR /sandbox
# create the new user instead directly using the ROOT becuase the agent code can be malicious and the root have all acccess

RUN useradd -m -s /bin/bash sandbox

# Copy the list of libraries and install them
COPY requirements.sandbox.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt \
    && rm /tmp/requirements.txt

RUN pip uninstall -y pip setuptools wheel
USER sandbox


CMD ["python"]