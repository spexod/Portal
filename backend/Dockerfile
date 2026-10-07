# # Things that can be cached
# Base Configurations
FROM python:3.14-alpine AS build
ENV PYTHONNUNBUFFERED 1
WORKDIR /home/python_user/backend_app
ENV PYTHONPATH "${PYTHONPATH}:/home/python_user/backend_app"
# No database credentials at build time: MYSQL_* are passed only at runtime (compose.yaml
# "environment:"), so they are never stored in the image. IS_DOCKER_BUILD is set inline on
# the RUN steps below that import Django, so it does not leak into the runtime image.
ARG MPLCONFIGDIR
ENV MPLCONFIGDIR $MPLCONFIGDIR
ARG DATA_OUTPUT_DIR
ENV DATA_OUTPUT_DIR $DATA_OUTPUT_DIR
# update pip
RUN pip install --upgrade pip
# install a virtual environment
RUN pip install virtualenv
# create a virtual environment
RUN python -m venv /home/python_user/backend_app/venv
# activate the virtual environment
RUN source /home/python_user/backend_app/venv/bin/activate
# install mysql client and gcc compiler on the alpine image
RUN apk update && apk add --no-cache mariadb-dev build-base
# # setup a username and group
RUN addgroup --system --gid 1001 python_group
RUN adduser --system --uid 1001 python_user --ingroup python_group
## make a cache directory for matplotlib
RUN mkdir -p $MPLCONFIGDIR
RUN chown python_user:python_group $MPLCONFIGDIR
# make and output directory for data processing results
RUN mkdir -p $DATA_OUTPUT_DIR
RUN chown python_user:python_group $DATA_OUTPUT_DIR
# pip install the requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
# # Things that will need to update every time the code changes
# COPY --chown=python_user:python_group . .
COPY . .
# generate the Django migration files (no database needed at build time)
# Database initialization and "migrate" now run at container start, see docker-entrypoint.sh
# (--skip-checks: the model system checks ask MySQL for its server version)
RUN IS_DOCKER_BUILD=true python manage.py makemigrations djangoAPI --skip-checks
# For static files used by the Django app
RUN mkdir /home/python_user/backend_app/static_root
# collect the static files
RUN IS_DOCKER_BUILD=true python manage.py collectstatic --clear --noinput
# allow the user to read the static files
RUN chown -R python_user:python_group /home/python_user/backend_app/static_root
# set the user
USER python_user
# initialize the database and apply migrations, then run CMD (or the "docker compose run" command)
ENTRYPOINT ["/bin/sh", "/home/python_user/backend_app/docker-entrypoint.sh"]
# what runs when the container is started
CMD ["gunicorn", "core.wsgi", "--bind", "0.0.0.0:8000"]