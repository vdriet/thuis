FROM python:3.13

RUN mkdir -p /usr/src/app
WORKDIR /usr/src/app

COPY requirements.txt /usr/src/app/
RUN pip install --no-cache-dir -r requirements.txt

COPY /*.py /usr/src/app/
COPY /templates/* /usr/src/app/templates/

EXPOSE 8088

CMD [ "python", "-u", "thuis.py" ]
