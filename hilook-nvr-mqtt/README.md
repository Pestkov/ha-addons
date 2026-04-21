# HiLook NVR MQTT

Listens for TCP motion events from HiLook/Hikvision NVR
and publishes them to MQTT.

## MQTT Topics

| Topic | Payload |
|-------|---------|
| `nvr/channel/1/event` | `{"channel": 1, "event": "motion"}` |
| `nvr/channel/2/event` | `{"channel": 2, "event": "motion"}` |
| `nvr/status` | `online` |

## Configuration

| Option | Default | Description |
|--------|---------|-------------|
| `mqtt_host` | `core-mosquitto` | MQTT broker host |
| `mqtt_port` | `1883` | MQTT broker port |
| `nvr_port` | `6062` | TCP port for NVR |
