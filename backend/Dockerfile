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
RUN apt-get install cron rsync -y
# pip install the requirements
COPY requirements.txt .
RUN pip install -r requirements.txt
# # Things that will need to update every time the SpExoDisks code changes
# load data into this container for the API from SpExoDisks science app

# # Things that will need to update every time the SpExWebsite code changes
# copy all the files into the container
COPY . .

# what runs when the container is started
CMD ["/start.sh"]
# CMD ["gunicorn", "core.wsgi", "--bind", "0.0.0.0:8000"]