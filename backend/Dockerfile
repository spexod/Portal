# # Things that can be cached
# Base Configurations
FROM python AS build
ENV PYTHONNUNBUFFERED 1
WORKDIR /django
ENV PYTHONPATH "${PYTHONPATH}:/django"
ARG MYSQL_HOST
ENV MYSQL_HOST $MYSQL_HOST
ARG MYSQL_PASSWORD
ENV MYSQL_PASSWORD $MYSQL_PASSWORD
ARG MYSQL_USER
ENV MYSQL_USER $MYSQL_USER
ENV IS_DOCKER_BUILD true
# update pip
RUN pip install --upgrade pip
# get the cron application installed
RUN apt-get update
# # setup a username and group
RUN addgroup --system --gid 1001 python_group
RUN adduser --system --uid 1001 python_user
RUN mkdir /nonexistent
RUN chown python_user:python_group /nonexistent
# Optional
# chmod g+s, u-s /usr/bin/crontab
# set the permissions intialistation script for the container
COPY --chown=python_user:python_group start.sh /
RUN ["chmod", "+x", "/start.sh"]
# pip install the requirements
COPY --chown=python_user:python_group requirements.txt .
RUN pip install -r requirements.txt
# Things that will need to update every time the code changes
COPY --chown=python_user:python_group . .
RUN mkdir /django/static_root
# initialize the databases, if not already initialized
RUN python science/db/init.py
# migrate the Django database and tables
RUN python manage.py makemigrations djangoAPI
RUN python manage.py migrate
# collect the static files
RUN python manage.py collectstatic --clear --noinput
# set the permissions
RUN chown -R python_user:python_group /django
# set the user
USER python_user
# what runs when the container is started
CMD ["/start.sh"]
# CMD ["gunicorn", "core.wsgi", "--bind", "0.0.0.0:8000"]