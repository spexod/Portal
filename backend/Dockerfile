# # Things that can be cached
# Base Configurations
FROM python as build
ENV PYTHONNUNBUFFERED 1
WORKDIR /django
ENV PYTHONPATH "${PYTHONPATH}:/django"
# set up the cronlog
RUN mkdir /cronlogs
RUN touch /cronlogs/cron.log
# set the permissions intialistation script for the container
ADD start.sh /
RUN ["chmod", "+x", "/start.sh"]
# update pip
RUN pip install --upgrade pip
# get the cron application installed
RUN apt update
RUN apt-get install cron -y
# pip install the requirements
COPY requirements.txt .
RUN pip install -r requirements.txt
# # Things that will need to update every time the SpExoDisks code changes
# load data into this container for the API from SpExoDisks science app
ARG DATA_RESET_UPLOAD=false
ENV DATA_RESET_UPLOAD=${DATA_RESET_UPLOAD}
ARG MYSQL_HOST
ENV MYSQL_HOST=${MYSQL_HOST}
ARG MYSQL_USER
ENV MYSQL_USER=${MYSQL_USER}
ARG MYSQL_PASSWORD
ENV MYSQL_PASSWORD=${MYSQL_PASSWORD}
COPY ./science science
COPY ./ref ref
COPY ./data data
RUN python science/db/process.py
# # Things that will need to update every time the SpExWebsite code changes
# copy all the files into the container
COPY . .
# collect the static files
RUN python manage.py collectstatic --clear --noinput
# add the cron jobs to the Django management, but only after the data is upload to mysql
RUN python manage.py crontab add

# what runs when the container is started
CMD ["/start.sh"]
# CMD ["gunicorn", "core.wsgi", "--bind", "0.0.0.0:8000"]