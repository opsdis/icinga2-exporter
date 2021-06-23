FROM python:3 as builder
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY icinga2_exporter ./icinga2_exporter/
COPY setup.cfg .
COPY setup.py .
COPY manage_version.py .
COPY MANIFEST.in .
COPY README.md .

ENV TAG=1.0.0
RUN python setup.py sdist
RUN ls -l dist

FROM python:3
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY --from=builder dist/icinga2-exporter-dirty-dev.tar.gz /dist/
RUN pip install dist/icinga2-exporter-dirty-dev.tar.gz
RUN rm -rf dist
COPY wsgi.py .
#CMD python -m icinga2_exporter -f config.yml
CMD gunicorn --access-logfile /dev/null -w 4 -k uvicorn.workers.UvicornWorker "wsgi:create_app('/etc/icinga2-exporter/config.yml')"