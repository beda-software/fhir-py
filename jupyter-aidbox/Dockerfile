FROM jupyter/base-notebook:latest

USER root
RUN apt-get update && apt-get install -y git 
USER jovyan

RUN pip install aidbox
ADD examples.ipynb /work
