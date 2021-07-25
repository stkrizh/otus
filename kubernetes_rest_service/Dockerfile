FROM python:3.9-slim

COPY requirements.txt ./
RUN pip install -r requirements.txt

COPY app ./app
COPY run.sh ./

EXPOSE 8000

ENV PYTHONPATH=./:./app

CMD ["./run.sh"]
