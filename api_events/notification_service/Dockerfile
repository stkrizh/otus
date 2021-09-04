FROM python:3.9-slim

COPY requirements.txt ./
RUN pip install -r requirements.txt

COPY notification_service ./notification_service

EXPOSE 8080

CMD ["python", "-m", "notification_service.app"]
