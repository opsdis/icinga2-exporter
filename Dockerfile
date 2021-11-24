FROM docker-hub-remote.bahnhub.tech.rz.db.de/alpine:3.15 as builder
RUN apk update && apk add python3 py3-pip python3-dev gcc libc-dev alpine-sdk
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY icinga2_exporter ./icinga2_exporter/
COPY setup.cfg .
COPY setup.py .
COPY MANIFEST.in .
COPY README.md .
RUN python3 setup.py sdist

FROM docker-hub-remote.bahnhub.tech.rz.db.de/alpine:3.15
RUN apk update && apk add python3 py3-pip python3-dev gcc libc-dev alpine-sdk
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY --from=builder dist/*.tar.gz /dist/
RUN pip install dist/*.tar.gz
RUN rm -rf dist
COPY wsgi.py .
RUN pip install gunicorn uvicorn
CMD gunicorn --access-logfile /dev/null -w 4 -k uvicorn.workers.UvicornWorker "wsgi:create_app('/etc/icinga2-exporter/config.yml')"