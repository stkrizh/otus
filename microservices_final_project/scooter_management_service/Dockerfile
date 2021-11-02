FROM python:3.9-slim

COPY requirements.txt ./
RUN pip install -r requirements.txt

COPY scooter_management_service ./scooter_management_service

EXPOSE 8083

CMD ["python", "-m", "scooter_management_service.app"]
