# 🎤 Voice Questionnaire System

A clean, professional voice questionnaire system with OpenAI integration.

## 📁 Project Structure

```
refont/
├── app.py                 # Main Flask application
├── config.env            # API configuration
├── questions.json        # Questionnaire questions
├── start.py             # Quick start script
├── static/
│   └── app.js           # Frontend JavaScript
├── templates/
│   └── voice_chat.html  # Frontend HTML
└── responses/           # Generated answer files
```

## 🚀 Quick Start

1. **Configure API Key**:
   ```bash
   # Edit config.env
   OPENAI_API_KEY=your_api_key_here
   ```

2. **Start the Server**:
   ```bash
   python3 start.py
   ```

3. **Open Browser**:
   - Go to http://localhost:5001
   - Allow microphone access
   - Start the questionnaire

## ✨ Features

- **Voice-to-Voice**: Speech recognition and text-to-speech
- **5-Second Delay**: Natural pause between greeting and first question
- **Auto Analysis**: Automatic ChatGPT analysis after completion
- **Clean Interface**: No duplicate messages
- **File Management**: Automatic cleanup of old files

## 🎯 How It Works

1. **Greeting**: Agent says "Hi, I have some questions I would like you to answer."
2. **5-Second Pause**: Natural delay for user processing
3. **Questions**: Agent asks questions one by one
4. **Analysis**: Automatic ChatGPT analysis when complete
5. **Save**: Answers saved to timestamped JSON files

## 🔧 Technical Details

- **Backend**: Flask + Socket.IO
- **AI**: OpenAI Whisper (STT) + GPT-4o (analysis) + TTS
- **Frontend**: HTML5 + JavaScript + Web Audio API
- **Port**: 5001

## 📝 Usage

The system automatically:
- Cleans up old files on startup
- Saves responses to `responses/` directory
- Generates analysis files
- Provides clean, professional user experience

Ready to use! 🎉
