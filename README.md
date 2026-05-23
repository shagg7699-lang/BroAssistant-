# 🧠 ব্রো (Bro) — সুপারচার্জড AI অ্যাসিস্ট্যান্ট v3.0

**ভয়েস-অ্যাক্টিভেটেড হাইব্রিড AI অ্যাসিস্ট্যান্ট** — বাংলা ও ইংরেজি ভাষায় কম্পিউটার নিয়ন্ত্রণ, কোডিং, ভিডিও এডিটিং, এবং আরও অনেক কিছু।

## ✨ বৈশিষ্ট্য

- 🎤 **ভয়েস কমান্ড** — "ব্রো" বলে অ্যাক্টিভেট, faster-whisper দিয়ে বাংলা/ইংরেজি স্পিচ রিকগনিশন
- 🌐 **মাল্টি-ক্লাউড LLM** — Gemini 3.5 Flash, DeepSeek, GPT-4o, Llama 3.3, স্বয়ংক্রিয় ফেইলওভার
- 🖥️ **কম্পিউটার কন্ট্রোল** — মাউস, কিবোর্ড, স্ক্রিন ক্যাপচার (pyautogui)
- 💻 **VS Code অটোমেশন** — সরাসরি VS Code-এ কোডিং, ডিবাগিং, রিফ্যাক্টরিং
- 🎬 **ভিডিও এডিটিং** — Shotcut/FFmpeg, AI-ভিত্তিক ভিডিও জেনারেশন
- 🎵 **অডিও ফিঙ্গারপ্রিন্টিং** — Chromaprint দিয়ে গান শনাক্তকরণ
- 📱 **রিমোট কমান্ড** — টেলিগ্রাম বট ও অ্যান্ড্রয়েড ফোন থেকে নিয়ন্ত্রণ
- 🔮 **প্রেডিক্টিভ সাজেশন** — পরবর্তী কাজ অনুমান
- 🧩 **প্লাগইন সিস্টেম** — নতুন স্কিল যোগ করার সুবিধা
- 🤖 **রিইনফোর্সমেন্ট লার্নিং** — ব্যবহারকারীর পছন্দ শেখা
- 🔒 **ধাপে ধাপে অনুমতি** — গুরুত্বপূর্ণ কাজে ইউজার কনফার্মেশন

## 📁 প্রজেক্ট স্ট্রাকচার

```
BroAssistant/
├── bro_listener.py          # ওয়েক-ওয়ার্ড ডিটেক্টর
├── bro_assistant.py         # মূল অ্যাসিস্ট্যান্ট
├── bro_tray.py              # সিস্টেম ট্রে অ্যাপ
├── cloud/                   # ক্লাউড API ক্লায়েন্ট
├── local/                   # লোকাল STT/TTS/LLM
├── agents/                  # ১৬+ এজেন্ট
├── optimization/            # ক্যাশ, কনটেক্সট, শিডিউলার
├── utils/                   # লগিং, মেমোরি, স্ক্রিন
├── gui/                     # চ্যাট UI
├── config/                  # সেটিংস
└── data/                    # ডাটা ও লগ
```

## 🚀 সেটআপ

### Windows
```batch
Setup_Bro.bat
```

### Linux / macOS
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# .env ফাইলে API কী যোগ করুন
```

## ⚙️ কনফিগারেশন

`.env` ফাইলে API কী যোগ করুন:
- **GOOGLE_API_KEY** — Gemini 3.5 Flash (প্রাইমারি)
- **GROQ_API_KEY** — Groq (দ্রুত ইনফারেন্স)
- **GITHUB_TOKEN** — GitHub Models
- **SILICONFLOW_*** — SiliconFlow (DeepSeek, Qwen)

## ▶️ চালানো

### ইন্টারেক্টিভ মোড (টেক্সট চ্যাট)
```bash
python bro_assistant.py
```

### ভয়েস মোড (ওয়েক ওয়ার্ড)
```bash
python bro_listener.py
```

### সিস্টেম ট্রে (Windows)
```bash
python bro_tray.py
```

### Windows (ব্যাচ ফাইল)
```batch
Run_Bro.bat
```

## 🧩 এজেন্ট তালিকা

| এজেন্ট | কাজ |
|---------|------|
| `computer_use` | মাউস-কিবোর্ড-স্ক্রিন নিয়ন্ত্রণ |
| `shotcut_agent` | ভিডিও ট্রিম/কাট/রেন্ডার |
| `vscode_cua_agent` | VS Code রোবটিক অটোমেশন |
| `vscode_agents_hub` | বহু-এজেন্ট VS Code প্লাগইন |
| `opencode_autopilot` | স্বয়ংক্রিয় কোডিং |
| `video_agent` | ভিডিও বিশ্লেষণ ও এডিট |
| `autovideo_generator` | টেক্সট থেকে ভিডিও তৈরি |
| `chromaprint_listener` | অডিও ফিঙ্গারপ্রিন্টিং |
| `alex_core_plugin` | ডাইনামিক প্লাগইন সিস্টেম |
| `keysersoze_framework` | মেমোরি ও ফাইল সিস্টেম |
| `joshu_predictor` | প্রেডিক্টিভ অ্যাকশন |
| `human_bot_remote` | অ্যান্ড্রয়েড রিমোট |
| `nova_telegram_bot` | টেলিগ্রাম বট |
| `bantz_behavior_learner` | রিইনফোর্সমেন্ট লার্নিং |
| `miniomni2_brain` | ওমনি-মডেল |
| `just_agents_runner` | লোকাল LLM রানার |

## 🌐 ক্লাউড প্রোভাইডার

| প্রোভাইডার | মডেল | ব্যবহার |
|-----------|-------|---------|
| Google AI | Gemini 3.5 Flash | প্রাইমারি LLM + Vision |
| SiliconFlow | DeepSeek-V3/R1, Qwen3-VL | ব্যাকআপ LLM + Vision |
| GitHub Models | GPT-4o, Claude | ব্যাকআপ LLM |
| Groq | Llama 3.3 70B | দ্রুত ইনফারেন্স |
| Ollama (লোকাল) | deepseek-r1:8b, qwen3:8b | অফলাইন ব্যাকআপ |

## 📜 লাইসেন্স

MIT License
