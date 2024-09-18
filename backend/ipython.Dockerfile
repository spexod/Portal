FROM jupyter/scipy-notebook:latest
WORKDIR /backend
COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt
ENV PYTHONPATH="/backend"