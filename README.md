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

### **Option 1: Automated Setup**
```bash
# Run the setup script
./setup.sh

# Start the server
python3 start.py
```

### **Option 2: Manual Setup**
1. **Install Dependencies**:
   ```bash
   pip3 install -r requirements.txt
   ```

2. **Configure API Key**:
   ```bash
   # Copy template
   cp .env.example config.env
   
   # Edit config.env and add your OpenAI API key
   OPENAI_API_KEY=your_actual_api_key_here
   ```

3. **Start the Server**:
   ```bash
   python3 start.py
   ```

4. **Open Browser**:
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
