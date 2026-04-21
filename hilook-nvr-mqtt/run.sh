#!/bin/sh
NVR_PORT=$(jq -r '.nvr_port' /data/options.json)
MQTT_HOST=$(jq -r '.mqtt_host' /data/options.json)
MQTT_PORT=$(jq -r '.mqtt_port' /data/options.json)
MOTION_TIMEOUT=$(jq -r '.motion_timeout' /data/options.json)

echo "Starting HiLook NVR listener on port ${NVR_PORT}"
echo "MQTT broker: ${MQTT_HOST}:${MQTT_PORT}"
echo "Motion timeout: ${MOTION_TIMEOUT}s"

python3 /nvr_listener.py "${NVR_PORT}" "${MQTT_HOST}" "${MQTT_PORT}" "${MOTION_TIMEOUT}"
