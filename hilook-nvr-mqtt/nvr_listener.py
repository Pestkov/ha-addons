import asyncio
import sys
import json
import paho.mqtt.client as mqtt

NVR_PORT       = int(sys.argv[1])
MQTT_HOST      = sys.argv[2]
MQTT_PORT      = int(sys.argv[3])
MOTION_TIMEOUT = int(sys.argv[4])

EVENT_TYPES = {
    0x01: "io_alarm",
    0x02: "video_loss",
    0x03: "motion",
    0x05: "motion",
    0x06: "tamper",
}

TOPIC_EVENT  = "nvr/channel/{channel}/state"
TOPIC_STATUS = "nvr/status"

mqtt_client = mqtt.Client()
motion_timers = {}

def mqtt_connect():
    try:
        mqtt_client.connect(MQTT_HOST, MQTT_PORT, keepalive=60)
        mqtt_client.loop_start()
        print(f"[MQTT] Connected to {MQTT_HOST}:{MQTT_PORT}")
        mqtt_client.publish(TOPIC_STATUS, "online", retain=True)
    except Exception as e:
        print(f"[MQTT] Connection failed: {e}")

def publish_state(channel, state):
    topic = TOPIC_EVENT.format(channel=channel)
    payload = json.dumps({"channel": channel, "state": state})
    mqtt_client.publish(topic, payload, retain=True)
    print(f"[STATE] channel={channel} → {state}")

def motion_clear(channel):
    publish_state(channel, "clear")
    motion_timers.pop(channel, None)

def handle_motion(channel):
    if channel in motion_timers:
        motion_timers[channel].cancel()
    publish_state(channel, "motion")
    loop = asyncio.get_event_loop()
    timer = loop.call_later(MOTION_TIMEOUT, motion_clear, channel)
    motion_timers[channel] = timer

def parse_packet(data: bytes):
    if len(data) < 20:
        return

    if len(data) in (799, 803, 11):
        return

    print(f"[PKT] Alarm {len(data)} bytes")

    try:
        model = data[0x67:0x8D].decode('ascii', errors='ignore').rstrip('\x00')
        if model:
            print(f"[REG] Device: {model}")
    except Exception:
        pass

    try:
        year   = (data[0x020F] << 8) | data[0x0210]
        month  = data[0x0211]
        day    = data[0x0212]
        hour   = data[0x0213]
        minute = data[0x0214]
        second = data[0x0215]
        ts = f"{year}-{month:02d}-{day:02d} {hour:02d}:{minute:02d}:{second:02d}"

        channel  = data[0x021A]
        ev_type  = data[0x0298]
        ev_name  = EVENT_TYPES.get(ev_type, f"unknown_0x{ev_type:02X}")

        print(f"[ALARM] {ts} channel={channel} event={ev_name}")
        handle_motion(channel)
    except Exception as e:
        print(f"[PARSE] Error: {e}")

async def handle_connection(reader, writer):
    try:
        data = await asyncio.wait_for(reader.read(4096), timeout=10.0)
        if data:
            parse_packet(data)
    except asyncio.TimeoutError:
        pass
    except Exception as e:
        print(f"[TCP] Error: {e}")
    finally:
        writer.close()

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
