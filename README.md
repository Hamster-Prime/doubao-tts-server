# 豆包TTS服务

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.8+-blue.svg" alt="Python">
  <img src="https://img.shields.io/badge/License-MIT-green.svg" alt="License">
  <img src="https://img.shields.io/badge/火山引擎-语音合成-orange.svg" alt="Volcengine">
</p>

一个带WebUI管理界面的火山引擎豆包语音合成API中间件，专为**开源阅读(Legado)**等阅读软件设计。

## 功能特性

- **WebUI管理界面** - 可视化配置，无需编辑配置文件
- **用量统计** - 实时查看字符消耗、请求次数
- **多音色支持** - 内置多种音色，可自由切换
- **开源阅读适配** - 一键复制配置，即开即用
- **语速调节** - 支持动态语速控制

## 快速开始

### 1. 安装依赖

```bash
apt install python3 python3-flask python3-pip
pip3 install requests
```

### 2. 部署服务

```bash
# 克隆仓库
git clone https://github.com/Hamster-Prime/doubao-tts-server.git
cd doubao-tts-server

# 直接运行
python3 app.py

# 或使用systemd（推荐）
sudo cp doubao-tts.service /etc/systemd/system/
sudo systemctl enable doubao-tts
sudo systemctl start doubao-tts
```

### 3. 配置API密钥

1. 访问 http://your-server-ip
2. 在"API设置"中填入火山引擎的 App ID 和 Access Token
3. 选择默认音色
4. 点击"保存设置"

## 获取火山引擎API密钥

1. 访问 [火山引擎控制台](https://console.volcengine.com/speech/service/8)
2. 开通语音合成服务
3. 创建应用获取 App ID
4. 生成 Access Token

## 开源阅读配置

在WebUI中复制配置，粘贴到开源阅读的"朗读引擎"设置中即可。

配置格式：
```
名称: 豆包TTS
url: http://your-server-ip/speech/stream,{"method":"POST","body":{"text":"{{speakText}}","voice":"zh_female_cancan_mars_bigtts","rate":"{{String(speakSpeed)}}%"},"headers":{"Content-Type":"application/json"}}
Content-Type: audio/mp3
并发率: 0
```

## API接口

### POST /speech/stream

语音合成接口

**请求体：**
```json
{
  "text": "要合成的文本",
  "voice": "zh_female_cancan_mars_bigtts",
  "rate": "0%"
}
```

**响应：** `audio/mp3` 音频流

## 可用音色

| 音色ID | 名称 |
|--------|------|
| zh_female_cancan_mars_bigtts | 灿灿 - 活泼女声 |
| zh_male_chunhou_mars_bigtts | 淳厚 - 淳厚男声 |
| zh_female_shuangkuai_mars_bigtts | 爽快 - 爽快女声 |
| zh_male_yangguang_mars_bigtts | 阳光 - 阳光男声 |
| zh_female_tianmei_mars_bigtts | 甜美 - 甜美女声 |

更多音色请参考：[火山引擎音色列表](https://www.volcengine.com/docs/6561/1257544)

## 目录结构

```
doubao-tts-server/
├── app.py              # 主程序
├── doubao-tts.service  # systemd服务文件
├── README.md
└── LICENSE
```

## License

MIT License
