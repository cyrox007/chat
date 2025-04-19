FROM python:3.13.3-alpine

COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt

COPY . . 

CMD alembic upgrade head && python3 run_server.py