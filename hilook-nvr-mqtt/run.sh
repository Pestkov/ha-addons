#!/usr/bin/with-contenv bashio

MQTT_HOST=$(bashio::config 'mqtt_host')
MQTT_PORT=$(bashio::config 'mqtt_port')
NVR_PORT=$(bashio::config 'nvr_port')

bashio::log.info "Starting HiLook NVR listener on port ${NVR_PORT}"
bashio::log.info "MQTT broker: ${MQTT_HOST}:${MQTT_PORT}"

python3 /nvr_listener.py "${NVR_PORT}" "${MQTT_HOST}" "${MQTT_PORT}"
