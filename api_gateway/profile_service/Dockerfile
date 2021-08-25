FROM python:3.9-slim

COPY requirements.txt ./
RUN pip install -r requirements.txt

COPY profile_service ./profile_service

EXPOSE 8080

CMD ["python", "-m", "profile_service.app"]
