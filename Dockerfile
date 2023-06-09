FROM python:3.11.3-alpine

WORKDIR /emarket

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

RUN apk update \
    && apk add postgresql-dev gcc python3-dev musl-dev

RUN pip install --upgrade pip
COPY ./requirements.txt .
RUN pip install -r requirements.txt

EXPOSE 8000
EXPOSE 5432/tcp

COPY . .
