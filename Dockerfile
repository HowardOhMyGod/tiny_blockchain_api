FROM python:3.6

WORKDIR /usr/app

ADD . /usr/app

RUN pip3 install pipenv && \
    pipenv --python 3.6 && \
    pipenv install

EXPOSE 5000

CMD ["pipenv", "run", "python", "websocket.py"]