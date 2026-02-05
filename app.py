#!/usr/bin/env python3
"""
豆包TTS服务 - 带WebUI管理界面
"""

import os
import json
import base64
import uuid
from datetime import datetime
from flask import Flask, request, Response, render_template_string, jsonify
import requests

app = Flask(__name__)

# 配置文件路径
CONFIG_FILE = '/opt/doubao-tts/config.json'
STATS_FILE = '/opt/doubao-tts/stats.json'

# 默认配置
DEFAULT_CONFIG = {
    'appid': '',
    'access_token': '',
    'default_voice': 'zh_female_cancan_mars_bigtts',
    'cluster': 'volcano_tts'
}

# 可用音色列表
VOICES = [
    {"id": "zh_female_cancan_mars_bigtts", "name": "灿灿 - 活泼女声"},
    {"id": "saturn_zh_female_keainvsheng_tob", "name": "可爱女生"},
    {"id": "saturn_zh_female_tiaopigongzhu_tob", "name": "调皮公主"},
    {"id": "saturn_zh_male_shuanglangshaonian_tob", "name": "爽朗少年"},
    {"id": "saturn_zh_male_tiancaitongzhuo_tob", "name": "天才同桌"},
]

def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    return DEFAULT_CONFIG.copy()

def save_config(config):
    os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=2)

def load_stats():
    if os.path.exists(STATS_FILE):
        with open(STATS_FILE, 'r') as f:
            return json.load(f)
    return {'total_chars': 0, 'total_requests': 0, 'history': []}

def save_stats(stats):
    os.makedirs(os.path.dirname(STATS_FILE), exist_ok=True)
    with open(STATS_FILE, 'w') as f:
        json.dump(stats, f, indent=2)

def update_stats(chars):
    stats = load_stats()
    stats['total_chars'] += chars
    stats['total_requests'] += 1
    today = datetime.now().strftime('%Y-%m-%d')
    found = False
    for day in stats['history']:
        if day['date'] == today:
            day['chars'] += chars
            day['requests'] += 1
            found = True
            break
    if not found:
        stats['history'].append({'date': today, 'chars': chars, 'requests': 1})
    stats['history'] = stats['history'][-30:]
    save_stats(stats)

def synthesize_tts(text, voice, speed_ratio=1.0):
    """调用豆包TTS API"""
    config = load_config()
    
    if not config.get('appid') or not config.get('access_token'):
        return None, "未配置appid或access_token"
    
    url = "https://openspeech.bytedance.com/api/v1/tts"
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer; {config['access_token']}"
    }
    
    payload = {
        "app": {
            "appid": config["appid"],
            "token": "placeholder",
            "cluster": config.get("cluster", "volcano_tts")
        },
        "user": {"uid": "legado_user"},
        "audio": {
            "voice_type": voice,
            "encoding": "mp3",
            "speed_ratio": speed_ratio,
            "rate": 24000
        },
        "request": {
            "reqid": str(uuid.uuid4()),
            "text": text,
            "operation": "query"
        }
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        result = response.json()
        
        if result.get("code") != 3000:
            return None, f"API错误: {result.get('message', 'Unknown')}"
        
        audio_data = base64.b64decode(result.get("data", ""))
        return audio_data, None
    except Exception as e:
        return None, str(e)

# API路由
@app.route('/speech/stream', methods=['POST'])
def speech_stream():
    """TTS接口 - 供开源阅读调用"""
    try:
        data = request.json
        text = data.get('text', '')
        config = load_config()
        voice = data.get('voice', config.get('default_voice'))
        rate = data.get('rate', '0%')
        
        if not text:
            return Response('No text', status=400)
        
        # 解析语速
        speed_ratio = 1.0
        if rate:
            rate_str = rate.replace('%', '').replace('+', '')
            try:
                speed_ratio = 1.0 + float(rate_str) / 100
                speed_ratio = max(0.2, min(3.0, speed_ratio))
            except:
                pass
        
        audio, error = synthesize_tts(text, voice, speed_ratio)
        
        if audio:
            update_stats(len(text))
            return Response(audio, mimetype='audio/mp3')
        else:
            return Response(f'TTS failed: {error}', status=500)
    except Exception as e:
        return Response(f'Error: {e}', status=500)

@app.route('/api/config', methods=['GET', 'POST'])
def api_config():
    if request.method == 'GET':
        config = load_config()
        # 隐藏token
        config['access_token'] = '********' if config.get('access_token') else ''
        # 隐藏appid中间几位
        appid = config.get('appid', '')
        if len(appid) > 6:
            config['appid'] = appid[:3] + '*' * (len(appid)-6) + appid[-3:]
        return jsonify(config)
    else:
        data = request.json
        config = load_config()
        if data.get('appid') and '*' not in data['appid']:
            config['appid'] = data['appid']
        if data.get('access_token') and data['access_token'] != '********':
            config['access_token'] = data['access_token']
        if data.get('default_voice'):
            config['default_voice'] = data['default_voice']
        save_config(config)
        return jsonify({'status': 'ok'})

@app.route('/api/stats', methods=['GET'])
def api_stats():
    return jsonify(load_stats())

@app.route('/api/voices', methods=['GET'])
def api_voices():
    return jsonify(VOICES)

@app.route('/')
def index():
    config = load_config()
    server_ip = request.host.split(':')[0]
    # 隐藏appid中间几位
    appid = config.get('appid', '')
    if len(appid) > 6:
        appid_display = appid[:3] + '*' * (len(appid)-6) + appid[-3:]
    else:
        appid_display = appid
    return render_template_string(HTML_TEMPLATE, 
        server_ip=server_ip,
        has_config=bool(config.get('appid') and config.get('access_token')),
        has_token=bool(config.get('access_token')),
        default_voice=config.get('default_voice', ''),
        appid=appid_display)

HTML_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>豆包TTS服务</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { font-family: -apple-system, BlinkMacSystemFont, sans-serif; background: #f5f5f5; }
        .container { max-width: 900px; margin: 0 auto; padding: 20px; }
        .card { background: white; border-radius: 12px; padding: 24px; margin-bottom: 20px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }
        .card h2 { color: #333; margin-bottom: 16px; font-size: 18px; }
        .stat-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 16px; }
        .stat-item { text-align: center; padding: 16px; background: #f8f9fa; border-radius: 8px; }
        .stat-value { font-size: 28px; font-weight: bold; color: #007bff; }
        .stat-label { color: #666; font-size: 14px; margin-top: 4px; }
        .form-group { margin-bottom: 16px; }
        .form-group label { display: block; margin-bottom: 6px; color: #333; font-weight: 500; }
        .form-group input, .form-group select { width: 100%; padding: 10px 12px; border: 1px solid #ddd; border-radius: 6px; font-size: 14px; }
        .btn { padding: 10px 20px; border: none; border-radius: 6px; cursor: pointer; font-size: 14px; }
        .btn-primary { background: #007bff; color: white; }
        .code-block { background: #2d2d2d; color: #f8f8f2; padding: 16px; border-radius: 8px; font-family: monospace; font-size: 12px; overflow-x: auto; white-space: pre-wrap; word-break: break-all; }
        .status { display: inline-block; padding: 4px 12px; border-radius: 20px; font-size: 12px; }
        .status-ok { background: #d4edda; color: #155724; }
        .status-error { background: #f8d7da; color: #721c24; }
        .toast { position: fixed; top: 20px; right: 20px; padding: 12px 24px; background: #333; color: white; border-radius: 6px; display: none; }
    </style>
</head>
<body>
    <div class="container">
        <h1 style="margin: 20px 0; color: #333;">豆包TTS服务</h1>
        <div class="card">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">
                <h2>服务状态</h2>
                <span class="status {% if has_config %}status-ok{% else %}status-error{% endif %}">
                    {% if has_config %}已配置{% else %}未配置{% endif %}
                </span>
            </div>
            <div class="stat-grid" id="stats">
                <div class="stat-item"><div class="stat-value" id="total-chars">-</div><div class="stat-label">总字符数</div></div>
                <div class="stat-item"><div class="stat-value" id="total-requests">-</div><div class="stat-label">总请求数</div></div>
                <div class="stat-item"><div class="stat-value" id="today-chars">-</div><div class="stat-label">今日字符</div></div>
                <div class="stat-item"><div class="stat-value" id="today-requests">-</div><div class="stat-label">今日请求</div></div>
            </div>
        </div>
        <div class="card">
            <h2>开源阅读配置</h2>
            <p style="color:#666;margin-bottom:12px;">复制以下配置到开源阅读的朗读引擎：</p>
            <div class="code-block" id="legado-config"></div>
        </div>
        <div class="card">
            <h2>API设置</h2>
            <form id="config-form">
                <div class="form-group">
                    <label>App ID</label>
                    <input type="text" id="appid" value="{{ appid }}" placeholder="火山引擎AppID">
                </div>
                <div class="form-group">
                    <label>Access Token</label>
                    <input type="password" id="access-token" placeholder="{% if has_token %}********（已配置，留空保持不变）{% else %}火山引擎Access Token{% endif %}" value="">
                </div>
                <div class="form-group">
                    <label>默认音色</label>
                    <select id="default-voice"></select>
                </div>
                <button type="submit" class="btn btn-primary">保存设置</button>
            </form>
        </div>
        <div class="card">
            <h2>测试</h2>
            <div class="form-group">
                <input type="text" id="test-text" value="你好，这是一段测试语音。" style="margin-bottom:12px;">
            </div>
            <button class="btn btn-primary" onclick="testTTS()">播放测试</button>
            <audio id="audio-player" style="margin-left:12px;"></audio>
        </div>
    </div>
    <div class="toast" id="toast"></div>
<script>
const serverIp = '{{ server_ip }}';
const defaultVoice = '{{ default_voice }}';
async function loadStats() {
    const res = await fetch('/api/stats');
    const data = await res.json();
    document.getElementById('total-chars').textContent = data.total_chars.toLocaleString();
    document.getElementById('total-requests').textContent = data.total_requests.toLocaleString();
    const today = new Date().toISOString().split('T')[0];
    const todayData = data.history.find(d => d.date === today) || {chars: 0, requests: 0};
    document.getElementById('today-chars').textContent = todayData.chars.toLocaleString();
    document.getElementById('today-requests').textContent = todayData.requests.toLocaleString();
}
async function loadVoices() {
    const res = await fetch('/api/voices');
    const voices = await res.json();
    const select = document.getElementById('default-voice');
    voices.forEach(v => {
        const opt = document.createElement('option');
        opt.value = v.id; opt.textContent = v.name;
        if (v.id === defaultVoice) opt.selected = true;
        select.appendChild(opt);
    });
    updateLegadoConfig();
}
function updateLegadoConfig() {
    const voice = document.getElementById('default-voice').value;
    const config = `名称: 豆包TTS\nurl: http://${serverIp}/speech/stream,{"method":"POST","body":{"text":"` + String.fromCharCode(123,123) + `speakText` + String.fromCharCode(125,125) + `","voice":"${voice}","rate":"` + String.fromCharCode(123,123) + `String(speakSpeed)` + String.fromCharCode(125,125) + `%"},"headers":{"Content-Type":"application/json"}}\nContent-Type: audio/mp3\n并发率: 0`;
    document.getElementById('legado-config').textContent = config;
}
document.getElementById('default-voice').addEventListener('change', updateLegadoConfig);
document.getElementById('config-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const appid = document.getElementById('appid').value;
    const token = document.getElementById('access-token').value;
    const voice = document.getElementById('default-voice').value;
    await fetch('/api/config', {
        method: 'POST', headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({appid: appid, access_token: token || '***', default_voice: voice})
    });
    showToast('设置已保存'); location.reload();
});
async function testTTS() {
    const text = document.getElementById('test-text').value;
    const voice = document.getElementById('default-voice').value;
    const res = await fetch('/speech/stream', {
        method: 'POST', headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({text, voice, rate: '0%'})
    });
    if (res.ok) {
        const blob = await res.blob();
        document.getElementById('audio-player').src = URL.createObjectURL(blob);
        document.getElementById('audio-player').play();
    } else { showToast('TTS失败: ' + await res.text()); }
}
function showToast(msg) {
    const t = document.getElementById('toast'); t.textContent = msg; t.style.display = 'block';
    setTimeout(() => t.style.display = 'none', 3000);
}
loadStats(); loadVoices(); setInterval(loadStats, 30000);
</script>
</body>
</html>
'''

if __name__ == '__main__':
    os.makedirs('/opt/doubao-tts', exist_ok=True)
    app.run(host='0.0.0.0', port=80, threaded=True)
