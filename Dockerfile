FROM python:latest

WORKDIR /opt/sgs-housing-bot

RUN apt-get update && \
    apt-get install -y wget tar

RUN apt-get install -y firefox-esr

RUN wget -q -O /tmp/geckodriver.tar.gz https://github.com/mozilla/geckodriver/releases/download/v0.34.0/geckodriver-v0.34.0-linux64.tar.gz && \
    tar -zxf /tmp/geckodriver.tar.gz -C /usr/bin && \
    chmod 755 /usr/bin/geckodriver && \
    rm /tmp/geckodriver.tar.gz

RUN apt-get -y install cron
COPY sgs_cron /etc/cron.d/sgs_cron
RUN chmod 0644 /etc/cron.d/sgs_cron
RUN crontab /etc/cron.d/sgs_cron
RUN touch /var/log/cron.log

COPY ./requirements.txt requirements.txt
RUN pip install -r requirements.txt

COPY ./src .

COPY ./entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT [ "/entrypoint.sh" ]
CMD [ "cron", "-f", "-L", "2" ]