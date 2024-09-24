# # Things that can be cached
# Base Configurations
FROM python:3.12-alpine AS build
ENV PYTHONNUNBUFFERED 1
WORKDIR /home/python_user/backend_app
ENV PYTHONPATH "${PYTHONPATH}:/home/python_user/backend_app"
ARG MYSQL_HOST
ENV MYSQL_HOST $MYSQL_HOST
ARG MYSQL_PASSWORD
ENV MYSQL_PASSWORD $MYSQL_PASSWORD
ARG MYSQL_USER
ENV MYSQL_USER $MYSQL_USER
ENV IS_DOCKER_BUILD true
ARG MPLCONFIGDIR
ENV MPLCONFIGDIR $MPLCONFIGDIR
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
# pip install the requirements
COPY requirements.txt .
RUN pip install -r requirements.txt
# # Things that will need to update every time the code changes
# COPY --chown=python_user:python_group . .
COPY . .
# initialize the databases, if not already initialized
RUN python science/db/init.py
# migrate the Django database and tables
RUN python manage.py makemigrations djangoAPI
RUN python manage.py migrate
# For static files used by the Django app
RUN mkdir /home/python_user/backend_app/static_root
# collect the static files
RUN python manage.py collectstatic --clear --noinput
# allow the user to read the static files
RUN chown -R python_user:python_group /home/python_user/backend_app/static_root
# set the user
USER python_user
# what runs when the container is started
CMD ["gunicorn", "core.wsgi", "--bind", "0.0.0.0:8000"]