FROM python:3.9-slim

COPY requirements.txt ./
RUN pip install -r requirements.txt

COPY auth_service ./auth_service

EXPOSE 8080

CMD ["python", "-m", "auth_service.app"]
