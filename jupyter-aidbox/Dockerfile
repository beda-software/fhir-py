FROM jupyter/datascience-notebook:latest

RUN pip install aidbox
COPY examples.ipynb /home/jovyan/work/examples.ipynb
USER root
RUN chown jovyan /home/jovyan/work/examples.ipynb
USER jovyan
