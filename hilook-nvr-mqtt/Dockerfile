FROM ghcr.io/home-assistant/aarch64-base-python:3.11

RUN pip3 install paho-mqtt --break-system-packages

COPY run.sh /
COPY nvr_listener.py /
RUN chmod a+x /run.sh

CMD [ "/run.sh" ]
