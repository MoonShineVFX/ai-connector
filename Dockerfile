FROM python:3.11
ENV PYTHONUNBUFFERED 1

RUN mkdir /app
WORKDIR /app

ADD requirements.txt /app
RUN pip install -r requirements.txt

COPY ./src /app

ARG NOW
ENV VERSION=$NOW

CMD ["python", "main.py"]
