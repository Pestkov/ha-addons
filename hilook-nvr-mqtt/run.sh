#!/bin/sh

NVR_PORT=$(jq -r '.nvr_port' /data/options.json)
MQTT_HOST=$(jq -r '.mqtt_host' /data/options.json)
MQTT_PORT=$(jq -r '.mqtt_port' /data/options.json)

echo "Starting HiLook NVR listener on port ${NVR_PORT}"
echo "MQTT broker: ${MQTT_HOST}:${MQTT_PORT}"

python3 /nvr_listener.py "${NVR_PORT}" "${MQTT_HOST}" "${MQTT_PORT}"
