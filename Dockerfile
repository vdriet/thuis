FROM python:3.13

RUN mkdir -p /usr/src/app
WORKDIR /usr/src/app

COPY requirements.txt /usr/src/app/
RUN pip install --no-cache-dir -r requirements.txt

COPY /*.py /usr/src/app/
COPY /templates/* /usr/src/app/templates/
COPY /static/* /usr/src/app/static/
COPY /cert/* /usr/src/app/cert/

EXPOSE 8088

CMD [ "python", "-u", "thuis.py" ]
