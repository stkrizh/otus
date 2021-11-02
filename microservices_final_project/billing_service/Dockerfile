FROM python:3.9-slim

COPY requirements.txt ./
RUN pip install -r requirements.txt

COPY billing_service ./billing_service

EXPOSE 8081

CMD ["python", "-m", "billing_service.app"]
