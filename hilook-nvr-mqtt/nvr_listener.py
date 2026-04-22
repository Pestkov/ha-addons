import asyncio
import sys
import json
import time
import paho.mqtt.client as mqtt

sys.stdout.reconfigure(line_buffering=True)

VERSION = "1.0.10"

NVR_PORT       = int(sys.argv[1])
MQTT_HOST      = sys.argv[2]
MQTT_PORT      = int(sys.argv[3])
MQTT_USER      = sys.argv[4]
MQTT_PASSWORD  = sys.argv[5]
MOTION_TIMEOUT = int(sys.argv[6])

LOG_FILE = "/share/nvr_packets.log"

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

def log_packet(data: bytes, channel: int, ev_name: str, ts: str):
    try:
        with open(LOG_FILE, "a") as f:
            f.write(f"\n=== {ts} channel={channel} event={ev_name} size={len(data)} ===\n")
            # Все ненулевые байты
            for i in range(len(data)):
                if data[i] != 0:
                    asc = chr(data[i]) if 32 <= data[i] < 127 else '.'
                    f.write(f"  [0x{i:04X}] = 0x{data[i]:02X} ({data[i]:3d}) '{asc}'\n")
    except Exception as e:
        print(f"[LOG] Write error: {e}")

def on_connect(client, userdata, flags, rc):
    print(f"[MQTT] Connected rc={rc}")
    client.publish(TOPIC_STATUS, "online", retain=True)
    for ch in range(1, 5):
        topic = f"homeassistant/binary_sensor/nvr_channel_{ch}/config"
        payload = json.dumps({
            "name": f"NVR Camera {ch}",
            "unique_id": f"nvr_camera_{ch}",
            "state_topic": f"nvr/channel/{ch}/state",
            "value_template": "{{ value_json.state }}",
            "payload_on": "motion",
            "payload_off": "clear",
            "device_class": "motion",
            "device": {
                "identifiers": ["hilook_nvr"],
                "name": "HiLook NVR",
                "model": "NVR-104MH-D04",
                "manufacturer": "HiLook"
            }
        })
        result = client.publish(topic, payload, retain=True)
        print(f"[DISC] channel {ch} rc={result.rc}")

def mqtt_connect():
    mqtt_client.on_connect = on_connect
    if MQTT_USER:
        mqtt_client.username_pw_set(MQTT_USER, MQTT_PASSWORD)
    mqtt_client.connect(MQTT_HOST, MQTT_PORT, keepalive=60)
    mqtt_client.loop_start()

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
    size = len(data)
    
    if size < 20:
        return

    # Heartbeat — пишем в лог и пропускаем
    if size in (799, 803, 11):
        try:
            with open(LOG_FILE, "a") as f:
                hex4 = ' '.join(f'{data[i]:02X}' for i in range(min(8, size)))
                f.write(f"[HB] size={size} | {hex4}\n")
        except:
            pass
        return

    print(f"[PKT] size={size}")

    try:
        # Большой пакет (1323, 1331+)
        if size >= 0x021B:
            year   = (data[0x020F] << 8) | data[0x0210]
            month  = data[0x0211]
            day    = data[0x0212]
            hour   = data[0x0213]
            minute = data[0x0214]
            second = data[0x0215]
            channel = data[0x021A]
            ev_type = data[0x0298]

        # Маленький пакет (~807)
        elif size >= 0x01A0:
            year   = (data[0x0192] << 8) | data[0x0193] if data[0x0192] == 0x07 else 0
            year   = (data[0x0193] << 8) | data[0x0194]
            month  = data[0x0195]
            day    = data[0x0196]
            hour   = data[0x0197]
            minute = data[0x0198]
            second = data[0x0199]
            channel = data[0x019E]
            ev_type = data[0x021C]

        else:
            print(f"[PKT] unknown size {size}, skip")
            log_packet(data, -1, "unknown", f"size={size}")
            return

        ts = f"{year}-{month:02d}-{day:02d} {hour:02d}:{minute:02d}:{second:02d}"
        ev_name = EVENT_TYPES.get(ev_type, f"unknown_0x{ev_type:02X}")

        print(f"[ALARM] {ts} channel={channel} event={ev_name}")
        log_packet(data, channel, ev_name, ts)

        if ev_type in EVENT_TYPES and channel > 0:
            handle_motion(channel)
        else:
            print(f"[PKT] skip channel={channel} ev_type=0x{ev_type:02X}")

    except Exception as e:
        print(f"[PARSE] Error: {e}")
        log_packet(data, -1, "parse_error", str(e))

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
    print(f"=== HiLook NVR Listener v{VERSION} ===")
    mqtt_connect()
    server = await asyncio.start_server(
        handle_connection, "0.0.0.0", NVR_PORT
    )
    print(f"[TCP] Listening on 0.0.0.0:{NVR_PORT}")
    async with server:
        await server.serve_forever()

if __name__ == "__main__":
    asyncio.run(main())
