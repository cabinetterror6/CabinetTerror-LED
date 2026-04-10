#!/usr/bin/env python3
import time
import math
import json
import requests
import os
from PIL import Image, ImageSequence
from rgbmatrix import RGBMatrix, RGBMatrixOptions, graphics
import paho.mqtt.client as mqtt

# --- CONFIGURATION ---
MQTT_BROKER = "localhost"
MQTT_TOPIC = "twitch/scroll"
GPIO_MAPPING = 'adafruit-hat'

# Global state variables
current_message = "Waiting for Chat..."
new_message_arrived = False
current_color = graphics.Color(0, 255, 0)
TEXT_HEIGHT = 22

def get_settings():
    try:
        with open('/home/shanpi/settings.json', 'r') as f:
            data = json.load(f)

            h = data.get('color_hex', '#00FF00').lstrip('#')
            r, g, b = tuple(int(h[i:i+2], 16) for i in (0, 2, 4))

            speed = data.get('scroll_speed', 'normal')
            brightness = int(data.get('brightness', 40))
            text_size = data.get('text_size', 'large')

            rows = int(data.get('matrix_rows', 32))
            cols = int(data.get('matrix_cols', 64))
            chain = int(data.get('matrix_chain', 2))
            slowdown = int(data.get('gpio_slowdown', 1))

            return data.get('default_message', 'Waiting...'), graphics.Color(r, g, b), speed, brightness, text_size, rows, cols, chain, slowdown
    except Exception as e:
        return "Waiting...", graphics.Color(0, 255, 0), "normal", 40, "large", 32, 64, 2, 1

def get_sports_score(team_name):
    leagues = {'NFL': 'football/nfl', 'NBA': 'basketball/nba', 'MLB': 'baseball/mlb', 'NHL': 'hockey/nhl'}
    for league, path in leagues.items():
        try:
            url = f"https://site.api.espn.com/apis/site/v2/sports/{path}/scoreboard"
            response = requests.get(url, timeout=3)
            data = response.json()
            for event in data.get('events', []):
                name = event.get('name', '').lower()
                short_name = event.get('shortName', '').lower()
                if team_name.lower() in name or team_name.lower() in short_name:
                    status = event['status']['type']['shortDetail']
                    competitors = event['competitions'][0]['competitors']
                    home = competitors[0]
                    away = competitors[1]
                    return f"[{league}] {away['team']['abbreviation']} {away['score']} @ {home['team']['abbreviation']} {home['score']} ({status})"
        except:
            continue
    return f"No game found for: {team_name}"

def on_connect(client, userdata, flags, rc):
    client.subscribe(MQTT_TOPIC)

def on_message(client, userdata, msg):
    global current_message, new_message_arrived, current_color
    try:
        incoming = msg.payload.decode("utf-8").strip()
        if incoming.lower().startswith("!sports "):
            current_message = get_sports_score(incoming[8:].strip())
        elif incoming.startswith("▶️") or "Playing:" in incoming:
            current_message = incoming
            current_color = graphics.Color(145, 70, 255)
        else:
            current_message = incoming
        new_message_arrived = True
    except:
        pass

def run_matrix():
    global current_message, new_message_arrived, current_color, TEXT_HEIGHT

    # 1. Grab initial settings
    DEFAULT_MSG, SETTINGS_COLOR, current_speed_str, current_brightness, current_font_size, m_rows, m_cols, m_chain, m_slow = get_settings()

    current_message = DEFAULT_MSG
    speed_map = {"fast": 0.015, "normal": 0.03, "slow": 0.05}
    current_speed_val = speed_map.get(current_speed_str, 0.03)

    # 2. Setup Hardware Options
    options = RGBMatrixOptions()
    options.rows = m_rows
    options.cols = m_cols
    options.chain_length = m_chain
    options.gpio_slowdown = m_slow
    options.hardware_mapping = GPIO_MAPPING
    options.drop_privileges = False
    options.brightness = current_brightness

    matrix = RGBMatrix(options = options)
    offscreen_canvas = matrix.CreateFrameCanvas()

    # 3. INITIALIZE FONT PROPERLY
    font = graphics.Font()
    font_path = "/home/shanpi/LEDMatrix/rpi-rgb-led-matrix-master/fonts/"

    if current_font_size == "small":
        font.LoadFont(font_path + "7x13.bdf")
        TEXT_HEIGHT = 18
    elif current_font_size == "medium":
        font.LoadFont(font_path + "9x18.bdf")
        TEXT_HEIGHT = 21
    else:
        font.LoadFont(font_path + "10x20.bdf")
        TEXT_HEIGHT = 22

    # 4. Start MQTT
    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_message = on_message
    try:
        client.connect(MQTT_BROKER, 1883, 60)
        client.loop_start()
    except:
        pass

    pos = offscreen_canvas.width
    is_scrolling_custom = False
    hue = 0

    while True:
        if new_message_arrived:
            if current_message == "!police":
                end_time = time.time() + 10
                while time.time() < end_time:
                    offscreen_canvas.Fill(255, 0, 0)
                    offscreen_canvas = matrix.SwapOnVSync(offscreen_canvas)
                    time.sleep(0.15)
                    offscreen_canvas.Fill(0, 0, 255)
                    offscreen_canvas = matrix.SwapOnVSync(offscreen_canvas)
                    time.sleep(0.15)
                current_message = DEFAULT_MSG
                new_message_arrived = False
                pos = offscreen_canvas.width
                is_scrolling_custom = False
                continue

            elif current_message.startswith("!"):
                cmd = current_message[1:].lower()
                gif_p = f"/home/shanpi/{cmd}.gif"
                png_p = f"/home/shanpi/{cmd}.png"

                if os.path.exists(gif_p):
                    gif_img = Image.open(gif_p)
                    frames = [f.convert('RGB').resize((offscreen_canvas.width, 32), Image.NEAREST) for f in ImageSequence.Iterator(gif_img)]
                    end_t = time.time() + 5
                    while time.time() < end_t:
                        for frame in frames:
                            offscreen_canvas.Clear()
                            offscreen_canvas.SetImage(frame, (offscreen_canvas.width - frame.width) // 2, 0)
                            offscreen_canvas = matrix.SwapOnVSync(offscreen_canvas)
                            time.sleep(0.1)
                elif os.path.exists(png_p):
                    img = Image.open(png_p).convert('RGB')
                    img.thumbnail((offscreen_canvas.width, 32))
                    offscreen_canvas.Clear()
                    offscreen_canvas.SetImage(img, (offscreen_canvas.width - img.width) // 2, 0)
                    offscreen_canvas = matrix.SwapOnVSync(offscreen_canvas)
                    time.sleep(5)

                current_message = DEFAULT_MSG
                new_message_arrived = False
                pos = offscreen_canvas.width
                is_scrolling_custom = False
                continue

        if new_message_arrived and current_message != DEFAULT_MSG:
            pos = offscreen_canvas.width
            is_scrolling_custom = True
            new_message_arrived = False

        offscreen_canvas.Clear()
        if is_scrolling_custom:
            r = int(127 * math.sin(hue) + 128)
            g = int(127 * math.sin(hue + 2) + 128)
            b = int(127 * math.sin(hue + 4) + 128)
            if current_color != graphics.Color(145, 70, 255):
                current_color = graphics.Color(r, g, b)
            hue += 0.1
        else:
            current_color = SETTINGS_COLOR

        length = graphics.DrawText(offscreen_canvas, font, pos, TEXT_HEIGHT, current_color, current_message)
        pos -= 1

        if (pos + length < 0):
            if is_scrolling_custom: is_scrolling_custom = False

            # REFRESH SETTINGS ON LOOP
            DEFAULT_MSG, SETTINGS_COLOR, speed_str, b_val, size_str, m_rows, m_cols, m_chain, m_slow = get_settings()
            matrix.brightness = b_val
            current_speed_val = speed_map.get(speed_str, 0.03)

            # Update Font if changed
            if size_str != current_font_size:
                current_font_size = size_str
                if size_str == "small":
                    font.LoadFont(font_path + "7x13.bdf")
                    TEXT_HEIGHT = 18
                elif size_str == "medium":
                    font.LoadFont(font_path + "9x18.bdf")
                    TEXT_HEIGHT = 21
                else:
                    font.LoadFont(font_path + "10x20.bdf")
                    TEXT_HEIGHT = 22

            if not is_scrolling_custom:
                current_message = DEFAULT_MSG
                current_color = SETTINGS_COLOR
            pos = offscreen_canvas.width

        time.sleep(current_speed_val)
        offscreen_canvas = matrix.SwapOnVSync(offscreen_canvas)

if __name__ == "__main__":
    run_matrix()