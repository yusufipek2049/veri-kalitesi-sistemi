FROM python:3.12.11-alpine3.22

WORKDIR /opt/enterprise-lab
COPY mock_service.py /opt/enterprise-lab/mock_service.py

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

ENTRYPOINT ["python", "/opt/enterprise-lab/mock_service.py"]
