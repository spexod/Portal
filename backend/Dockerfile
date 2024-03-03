# # Things that can be cached
# Base Configurations
FROM python as build
ENV PYTHONNUNBUFFERED 1
WORKDIR /django
ENV PYTHONPATH "${PYTHONPATH}:/django"
# update pip
RUN pip install --upgrade pip
# get the cron application installed
RUN apt-get update && apt-get install cron rsync -y
# # setup a username and group
RUN addgroup --system --gid 1001 python_group
RUN adduser --system --uid 1001 python_user
# set up the cronlog
RUN mkdir /cronlogs
RUN mkdir /nonexistent
RUN touch /cronlogs/cron.log
RUN chown python_user:python_group /cronlogs
RUN chown python_user:python_group /nonexistent
RUN chown python_user:python_group /var/run
RUN chown python_user:python_group /usr/sbin/cron
RUN chown python_user:python_group /usr/sbin/cron
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
RUN chown -R python_user:python_group /django
# set the user
USER python_user
# what runs when the container is started
CMD ["/start.sh"]
# CMD ["gunicorn", "core.wsgi", "--bind", "0.0.0.0:8000"]