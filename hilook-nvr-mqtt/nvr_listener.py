import asyncio
import sys
import json
import paho.mqtt.client as mqtt

# Аргументы из run.sh
NVR_PORT = int(sys.argv[1])
MQTT_HOST = sys.argv[2]
MQTT_PORT = int(sys.argv[3])

# Типы событий HiLook/Hikvision
EVENT_TYPES = {
    0x01: "io_alarm",
    0x02: "video_loss",
    0x03: "motion",
    0x05: "motion",
    0x06: "tamper",
}

# MQTT топики
TOPIC_EVENT   = "nvr/channel/{channel}/event"
TOPIC_STATUS  = "nvr/status"

mqtt_client = mqtt.Client()

def mqtt_connect():
    try:
        mqtt_client.connect(MQTT_HOST, MQTT_PORT, keepalive=60)
        mqtt_client.loop_start()
        print(f"[MQTT] Connected to {MQTT_HOST}:{MQTT_PORT}")
        mqtt_client.publish(TOPIC_STATUS, "online", retain=True)
    except Exception as e:
        print(f"[MQTT] Connection failed: {e}")

def publish_event(channel, event_type):
    event_name = EVENT_TYPES.get(event_type, f"unknown_{event_type:#04x}")
    topic = TOPIC_EVENT.format(channel=channel)
    payload = json.dumps({
        "channel": channel,
        "event": event_name,
    })
    mqtt_client.publish(topic, payload, retain=False)
    print(f"[EVENT] channel={channel} event={event_name} → {topic}")

def parse_packet(data: bytes):
    print(f"[PKT] Received {len(data)} bytes")

    # Пакет регистрации устройства (~387 байт)
    if len(data) >= 0x8D:
        try:
            model = data[0x67:0x8D].decode('ascii', errors='ignore').rstrip('\x00')
            if model:
                print(f"[REG] Device: {model}")
        except Exception:
            pass

    # Пакет тревоги
    if len(data) >= 0x0299:
        try:
            year   = (data[0x020F] << 8) | data[0x0210]
            month  = data[0x0211]
            day    = data[0x0212]
            hour   = data[0x0213]
            minute = data[0x0214]
            second = data[0x0215]
            ts = f"{year}-{month:02d}-{day:02d} {hour:02d}:{minute:02d}:{second:02d}"

            channel   = data[0x0297]
            ev_type   = data[0x0298]

            print(f"[ALARM] {ts} channel={channel} type=0x{ev_type:02X}")
            publish_event(channel, ev_type)
        except Exception as e:
            print(f"[PARSE] Error: {e}")

async def handle_connection(reader, writer):
    addr = writer.get_extra_info("peername")
    print(f"[TCP] Connect from {addr}")
    try:
        data = await asyncio.wait_for(reader.read(4096), timeout=10.0)
        if data:
            parse_packet(data)
    except asyncio.TimeoutError:
        print(f"[TCP] Timeout {addr}")
    except Exception as e:
        print(f"[TCP] Error: {e}")
    finally:
        writer.close()
        print(f"[TCP] Disconnect {addr}")

async def main():
    mqtt_connect()
    server = await asyncio.start_server(
        handle_connection, "0.0.0.0", NVR_PORT
    )
    print(f"[TCP] Listening on 0.0.0.0:{NVR_PORT}")
    async with server:
        await server.serve_forever()

if __name__ == "__main__":
    asyncio.run(main())
