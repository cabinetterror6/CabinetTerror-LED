from flask import Flask, render_template, request, redirect
from werkzeug.utils import secure_filename
import subprocess
import json
import os

app = Flask(__name__)
SETTINGS_FILE = '/home/shanpi/settings.json'
UPLOAD_FOLDER = '/home/shanpi/'
ALLOWED_EXTENSIONS = {'png', 'gif'}

def get_ip():
    try:
        return subprocess.check_output(['hostname', '-I']).decode('utf-8').split()[0]
    except:
        return "Unknown"

def load_settings():
    try:
        with open(SETTINGS_FILE, 'r') as f:
            return json.load(f)
    except:
        return {
            "default_message": "Waiting for Chat...",
            "color_hex": "#00FF00",
            "text_size": "large",
            "scroll_speed": "normal",
            "brightness": "40",
            "matrix_rows": "32",
            "matrix_cols": "64",
            "matrix_chain": "2",
            "gpio_slowdown": "1"
        }

def save_settings(data):
    with open(SETTINGS_FILE, 'w') as f:
        json.dump(data, f)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/', methods=['GET', 'POST'])
def dashboard():
    settings = load_settings()
    ip_address = get_ip()

    if request.method == 'POST':
        action = request.form.get('action')

        # 1. Update Display Settings
        if action == 'update_settings':
            settings['default_message'] = request.form.get('message', settings.get('default_message', 'Waiting for Chat...'))
            settings['color_hex'] = request.form.get('color', settings.get('color_hex', '#00FF00'))
            settings['text_size'] = request.form.get('text_size', settings.get('text_size', 'large'))
            settings['scroll_speed'] = request.form.get('scroll_speed', settings.get('scroll_speed', 'normal'))
            settings['brightness'] = request.form.get('brightness', settings.get('brightness', '40'))
            save_settings(settings)

        # 2. Update Hardware Settings
        elif action == 'update_hardware':
            settings['matrix_rows'] = request.form.get('matrix_rows', settings.get('matrix_rows', '32'))
            settings['matrix_cols'] = request.form.get('matrix_cols', settings.get('matrix_cols', '64'))
            settings['matrix_chain'] = request.form.get('matrix_chain', settings.get('matrix_chain', '2'))
            settings['gpio_slowdown'] = request.form.get('gpio_slowdown', settings.get('gpio_slowdown', '1'))
            save_settings(settings)
            os.system('sudo systemctl restart twitch_led.service')

        # 3. Wi-Fi Setup Logic
        elif action == 'connect_wifi':
            ssid = request.form.get('ssid')
            password = request.form.get('password')
            # Kill hotspot, wait, then join home wifi
            connect_command = f'sudo nmcli con down "CabinetTerror-LED" && sleep 2 && sudo nmcli dev wifi connect "{ssid}" password "{password}"'
            subprocess.Popen(connect_command, shell=True)
            return render_template('connecting.html', ssid=ssid)

        # 4. Upload Media
        elif action == 'upload_media':
            if 'file' in request.files:
                file = request.files['file']
                if file.filename != '' and allowed_file(file.filename):
                    filename = secure_filename(file.filename).lower()
                    file.save(os.path.join(UPLOAD_FOLDER, filename))

        return redirect('/')

    return render_template('index.html', settings=settings, ip_address=ip_address)

if __name__ == '__main__':
    # Run on port 80 (requires sudo)
    app.run(host='0.0.0.0', port=80)