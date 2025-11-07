FROM python:3.12-slim

ENV LANG=C.UTF-8 \
    DEBIAN_FRONTEND=noninteractive \
    APT_INSTALL="apt install -y --no-install-recommends"

RUN apt update && \
    $APT_INSTALL texlive-full

RUN apt update && \
    $APT_INSTALL build-essential \
      pkg-config \
      cmake \
      ffmpeg \
      libpango1.0-dev \
      dvisvgm \
      git

RUN apt update && \
    $APT_INSTALL xorg xvfb

WORKDIR /app

RUN git clone https://github.com/3b1b/manim.git

RUN pip install -e manim
