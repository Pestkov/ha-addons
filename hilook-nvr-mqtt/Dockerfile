FROM python:3.11-alpine

RUN pip3 install paho-mqtt

COPY run.sh /
COPY nvr_listener.py /
RUN chmod a+x /run.sh

CMD [ "/run.sh" ]
