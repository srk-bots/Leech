FROM ubuntu:24.10
ENV DEBIAN_FRONTEND=noninteractive

COPY . .
RUN bash Aeon