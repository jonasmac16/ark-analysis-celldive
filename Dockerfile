ARG UBUNTU_VERSION=20.04

ARG ARCH=
ARG CUDA=11.2
FROM nvidia/cuda${ARCH:+-$ARCH}:${CUDA}.1-base-ubuntu${UBUNTU_VERSION} as base
# ARCH and CUDA are specified again because the FROM directive resets ARGs
# (but their default value is retained if set previously)
ARG ARCH
ARG CUDA
ARG CUDNN=8.1.0.77-1
ARG CUDNN_MAJOR_VERSION=8
ARG LIB_DIR_PREFIX=x86_64
ARG LIBNVINFER=7.2.2-1
ARG LIBNVINFER_MAJOR_VERSION=7

# Let us install tzdata painlessly
ENV DEBIAN_FRONTEND=noninteractive

# Needed for string substitution
SHELL ["/bin/bash", "-c"]
# Pick up some TF dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        cuda-command-line-tools-${CUDA/./-} \
        libcublas-${CUDA/./-} \
        cuda-nvrtc-${CUDA/./-} \
        libcufft-${CUDA/./-} \
        libcurand-${CUDA/./-} \
        libcusolver-${CUDA/./-} \
        libcusparse-${CUDA/./-} \
        curl \
        libcudnn8=${CUDNN}+cuda${CUDA} \
        libfreetype6-dev \
        libhdf5-serial-dev \
        libzmq3-dev \
        pkg-config \
        software-properties-common \
        unzip

# Install TensorRT if not building for PowerPC
# NOTE: libnvinfer uses cuda11.1 versions
RUN [[ "${ARCH}" = "ppc64le" ]] || { apt-get update && \
        apt-key adv --fetch-keys https://developer.download.nvidia.com/compute/machine-learning/repos/ubuntu1804/x86_64/7fa2af80.pub && \
        echo "deb https://developer.download.nvidia.com/compute/machine-learning/repos/ubuntu1804/x86_64 /"  > /etc/apt/sources.list.d/tensorRT.list && \
        apt-get update && \
        apt-get install -y --no-install-recommends libnvinfer${LIBNVINFER_MAJOR_VERSION}=${LIBNVINFER}+cuda11.0 \
        libnvinfer-plugin${LIBNVINFER_MAJOR_VERSION}=${LIBNVINFER}+cuda11.0 \
        && apt-get clean \
        && rm -rf /var/lib/apt/lists/*; }

# For CUDA profiling, TensorFlow requires CUPTI.
ENV LD_LIBRARY_PATH /usr/local/cuda-11.0/targets/x86_64-linux/lib:/usr/local/cuda/extras/CUPTI/lib64:/usr/local/cuda/lib64:$LD_LIBRARY_PATH

# Link the libcuda stub to the location where tensorflow is searching for it and reconfigure
# dynamic linker run-time bindings
RUN ln -s /usr/local/cuda/lib64/stubs/libcuda.so /usr/local/cuda/lib64/stubs/libcuda.so.1 \
    && echo "/usr/local/cuda/lib64/stubs" > /etc/ld.so.conf.d/z-cuda-stubs.conf \
    && ldconfig

# See http://bugs.python.org/issue19846
ENV LANG C.UTF-8

RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip

RUN python3 -m pip --no-cache-dir install --upgrade \
    "pip<20.3" \
    setuptools

# Some TF tools expect a "python" binary
RUN ln -s $(which python3) /usr/local/bin/python

# Set environment variable 
ENV RUNNING_IN_DOCKER true

# system maintenance
RUN apt-get update

# install gcc
RUN apt-get install -y gcc

# install java, git, curl, wget
RUN apt-get install -y default-jre git curl wget python3-pip


# Install zsh shell
#RUN sh -c "$(wget -O- https://github.com/deluan/zsh-in-docker/releases/download/v1.1.5/zsh-in-docker.sh)" --\
 #   -t robbyrussell \
 #   -p git \
 #   -p https://github.com/zsh-users/zsh-autosuggestions \
 #   -p https://github.com/zsh-users/zsh-completions

# Stage 2: Installing Ark Analysis
FROM base AS move_ark

# copy over: setup.py, pyproject.toml, README and start_jupyter.sh script
COPY setup.py pyproject.toml README.md start_jupyter.sh /opt/ark-analysis/

# Copy over .git for commit history (dynamic versioning requires this in order to build ark)
COPY .git /opt/ark-analysis/.git

# Stage 3: Copy templates/ to scripts/
FROM move_ark AS move_templates

# copy the scripts over
# this should catch changes to the scripts from updates
COPY src /opt/ark-analysis/src

# Stage 4: Install Ark Analysis
FROM move_templates AS install_ark

# Install the package via setup.py
RUN cd /opt/ark-analysis && pip3 install .
RUN python -m pip install requests -U

# download deepcell models
RUN mkdir -p /.keras/models \
    && cd /.keras/models \
    && wget https://deepcell-data.s3-us-west-1.amazonaws.com/saved-models/MultiplexSegmentation-9.tar.gz \
    && tar -xvzf MultiplexSegmentation-9.tar.gz \
    && rm MultiplexSegmentation-9.tar.gz \
    && ln -s /.keras /root

# download bftools
RUN cd /opt \
    && wget https://downloads.openmicroscopy.org/bio-formats/6.13.0/artifacts/bftools.zip \
    && unzip bftools.zip \
    && rm bftools.zip

# Stage 5: Set the working directory, and open Jupyter Lab
FROM install_ark AS open_for_user
WORKDIR /opt/ark-analysis

# jupyter lab
CMD bash -c start_jupyter.sh
