#!/usr/bin/env python3
"""
Speech-to-speech Questionnaire (Flask + Socket.IO)

- Loads questions from questions.json
- Greets the user and asks questions one-by-one
- Captures spoken answers via Whisper
- Speaks each next step via TTS
"""

import os
import json
import tempfile
import base64
import glob
import time
from datetime import datetime

from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, emit
from openai import OpenAI

# ---------- Flask/Socket.IO ----------
app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'
socketio = SocketIO(app, cors_allowed_origins="*")

# ---------- Per-connection state ----------
# sessions[sid] = {
#   "history": [...],
#   "q_idx": int,
#   "answers": [{"id":..., "question":..., "answer":...}, ...],
#   "questions": [...]
# }
sessions = {}

# ---------- Cleanup Functions ----------
def cleanup_old_files():
    """Remove old answer and completed_questions files on startup."""
    print("🧹 Cleaning up old files...")
    
    # Clean up old answer files
    answer_files = glob.glob("responses/answers_*.json")
    for file_path in answer_files:
        try:
            os.remove(file_path)
            print(f"🗑️  Removed: {file_path}")
        except Exception as e:
            print(f"❌ Error removing {file_path}: {e}")
    
    # Clean up old completed_questions files
    completed_files = glob.glob("completed_questions_*.json")
    for file_path in completed_files:
        try:
            os.remove(file_path)
            print(f"🗑️  Removed: {file_path}")
        except Exception as e:
            print(f"❌ Error removing {file_path}: {e}")
    
    print("✅ Cleanup completed!")

# ---------- Initialize cleanup on startup ----------
cleanup_old_files()

# ---------- Config / OpenAI helpers ----------
def save_answers_to_file(answers, session_id):
    """Save answers to a JSON file in the responses folder."""
    try:
        # Create responses folder if it doesn't exist
        responses_dir = "responses"
        os.makedirs(responses_dir, exist_ok=True)
        
        # Create filename with timestamp and session ID
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{responses_dir}/answers_{timestamp}_session_{session_id}.json"
        
        # Prepare data to save
        data_to_save = {
            "session_id": session_id,
            "timestamp": datetime.now().isoformat(),
            "answers": answers
        }
        
        # Save to file
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data_to_save, f, ensure_ascii=False, indent=2)
        
        print(f"✅ Answers saved to: {filename}")
        return filename
    except Exception as e:
        print(f"❌ Error saving answers: {e}")
        return None

def load_api_key():
    try:
        with open('config.env', 'r') as f:
            for line in f:
                line = line.strip()
                if line.startswith('OPENAI_API_KEY='):
                    return line.split('=', 1)[1].strip()
    except FileNotFoundError:
        pass
    print('Load API is good')
    return None

def get_openai_client():
    api_key = load_api_key()
    if not api_key:
        raise ValueError("OpenAI API key not found in config.env")
    print('Load get_openai_client is good')
    return OpenAI(api_key=api_key)

# ---------- Audio I/O ----------
def transcribe_audio(audio_data_base64, language="en"):
    """Speech -> Text (Whisper)"""
    try:
        client = get_openai_client()
        raw = base64.b64decode(audio_data_base64)
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
            tmp.write(raw)
            path = tmp.name
        with open(path, 'rb') as f:
            transcript = client.audio.transcriptions.create(
                model="whisper-1",
                file=f,
                response_format="text",
                language=language
            )
        os.unlink(path)
        return transcript.strip()
    except Exception as e:
        print(f"[transcribe_audio] {e}")
        print('Load transcribe_audio is good')
        return ""

def tts(text):
    """Text -> Speech (TTS) -> base64 wav"""
    try:
        client = get_openai_client()
        # tts-1 returns raw audio bytes
        res = client.audio.speech.create(
            model="tts-1",
            voice="alloy",
            input=text
        )
        audio_bytes = res.content
        return base64.b64encode(audio_bytes).decode("utf-8")
    except Exception as e:
        print(f"[tts] {e}")
        print('Load tts is good')
        return None


# ---------- Questionnaire flow ----------
def load_questions():
    with open("questions.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    print('Load load questions is good')
    return data.get("questions", [])

def current_question(state):
    qs = state["questions"]
    idx = state["q_idx"]
    if 0 <= idx < len(qs):
        return qs[idx]
    print('Load current_question is good')
    return None

def speak_and_emit(text, sid=None):
    """Helper to emit both text and audio to client."""
    if sid is None:
        sid = request.sid
    emit('ai_response', {
        'text': text,
        'timestamp': datetime.now().strftime("%H:%M:%S")
    }, room=sid)
    audio = tts(text)
    if audio:
        emit('audio_response', {'audio': audio}, room=sid)

# ---------- Analysis Functions ----------
def run_analysis_with_latest_responses():
    """Run analysis using the latest response file."""
    print("🔄 Running Analysis with Latest Responses...")
    print("=" * 50)
    
    # Check if we have responses
    responses_dir = "responses"
    if not os.path.exists(responses_dir):
        print("❌ No responses folder found.")
        return False
    
    # Get all response files and sort by modification time
    response_files = [f for f in os.listdir(responses_dir) if f.startswith('answers_') and f.endswith('.json')]
    if len(response_files) == 0:
        print("❌ No response files found.")
        return False
    
    # Sort by modification time to get the latest
    response_files_with_paths = []
    for file in response_files:
        file_path = os.path.join(responses_dir, file)
        mtime = os.path.getmtime(file_path)
        response_files_with_paths.append((file, file_path, mtime))
    
    # Sort by modification time (newest first)
    response_files_with_paths.sort(key=lambda x: x[2], reverse=True)
    
    latest_file = response_files_with_paths[0]
    print(f"📁 Latest response file: {latest_file[0]}")
    print(f"🕒 Modified: {datetime.fromtimestamp(latest_file[2]).strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Load the latest response
    try:
        with open(latest_file[1], 'r', encoding='utf-8') as f:
            latest_response = json.load(f)
        print(f"✅ Loaded latest response with {len(latest_response.get('answers', []))} answers")
    except Exception as e:
        print(f"❌ Error loading latest response: {e}")
        return False
    
    # Load questions template
    try:
        with open('questions.json', 'r', encoding='utf-8') as f:
            questions_template = json.load(f)
        print(f"✅ Loaded questions template with {len(questions_template.get('questions', []))} questions")
    except Exception as e:
        print(f"❌ Error loading questions template: {e}")
        return False
    
    # Run analysis with ChatGPT
    print("\n🤖 Running ChatGPT analysis...")
    try:
        completed_json = analyze_responses_with_chatgpt([latest_response], questions_template)
        
        if not completed_json:
            print("❌ Failed to get analysis from ChatGPT")
            return False
        
        # Save the completed questions
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"completed_questions_{timestamp}.json"
        
        if save_completed_questions(completed_json, output_file):
            print(f"\n🎉 Analysis complete!")
            print(f"📁 Output file: {output_file}")
            print(f"📊 Analyzed latest response session")
            return True
        else:
            print("❌ Failed to save completed questions")
            return False
            
    except Exception as e:
        print(f"❌ Error running analysis: {e}")
        return False

def analyze_responses_with_chatgpt(responses, questions_template):
    """Use ChatGPT to analyze responses and create a complete questions.json."""
    try:
        client = get_openai_client()
        
        # Prepare the prompt for ChatGPT
        prompt = f"""
You are a data analyst. I have collected voice questionnaire responses and need you to analyze them to create a comprehensive questions.json file.

ORIGINAL QUESTIONS TEMPLATE:
{json.dumps(questions_template, ensure_ascii=False, indent=2)}

COLLECTED RESPONSES:
{json.dumps(responses, ensure_ascii=False, indent=2)}

Please analyze these responses and create a complete questions.json file that includes:

1. The original questions structure
2. For each question, add a "responses" field containing all the answers collected
3. Add statistics like response count, common answers, etc.
4. Add a "summary" section with overall insights
5. Keep the original structure but enhance it with the collected data

The output should be a valid JSON file that can be used for further analysis.
"""

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a data analyst specializing in questionnaire analysis. You create comprehensive JSON reports from collected responses."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=4000,
            temperature=0.3
        )
        
        return response.choices[0].message.content.strip()
        
    except Exception as e:
        print(f"❌ Error calling ChatGPT: {e}")
        return None

def extract_json_from_response(response_text):
    """Extract JSON from ChatGPT response that might contain extra text."""
    try:
        # Look for JSON block between ```json and ```
        import re
        json_match = re.search(r'```json\s*(\{.*?\})\s*```', response_text, re.DOTALL)
        if json_match:
            return json_match.group(1)
        
        # If no code block, try to find JSON object
        json_match = re.search(r'(\{.*\})', response_text, re.DOTALL)
        if json_match:
            return json_match.group(1)
        
        # If still nothing, return the whole response
        return response_text
    except Exception as e:
        print(f"❌ Error extracting JSON: {e}")
        return response_text

def save_completed_questions(completed_json, output_file="completed_questions.json"):
    """Save the completed questions JSON to a file."""
    try:
        # Extract JSON from response
        json_text = extract_json_from_response(completed_json)
        
        # Try to parse the JSON first
        parsed_json = json.loads(json_text)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(parsed_json, f, ensure_ascii=False, indent=2)
        
        print(f"✅ Completed questions saved to: {output_file}")
        return True
    except json.JSONDecodeError as e:
        print(f"❌ Error parsing ChatGPT response as JSON: {e}")
        print("Raw response:")
        print(completed_json)
        return False
    except Exception as e:
        print(f"❌ Error saving file: {e}")
        return False

# ---------- Routes ----------
@app.route('/')
def index():
    return render_template('voice_chat.html')

@app.route('/tts', methods=['POST'])
def tts_endpoint():
    """API endpoint for text-to-speech conversion."""
    try:
        data = request.get_json()
        text = data.get('text', '')
        if not text:
            return jsonify({"error": "No text provided"}), 400
        
        audio_base64 = tts(text)
        if audio_base64:
            return jsonify({"audio": audio_base64})
        else:
            return jsonify({"error": "TTS conversion failed"}), 500
    except Exception as e:
        print(f"Error in TTS endpoint: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/analyze', methods=['POST'])
def analyze_responses():
    """API endpoint to trigger analysis of latest responses."""
    try:
        success = run_analysis_with_latest_responses()
        if success:
            return jsonify({
                "status": "success",
                "message": "Analysis completed successfully!",
                "timestamp": datetime.now().isoformat()
            })
        else:
            return jsonify({
                "status": "error",
                "message": "Analysis failed. Check server logs for details."
            }), 500
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"Error during analysis: {str(e)}"
        }), 500

# ---------- Socket.IO Events ----------
@socketio.on('connect')
def on_connect():
    sid = request.sid
    print(f'Client connected: {sid}')

    # Initialize per-session state
    sessions[sid] = {
        "history": [],
        "q_idx": 0,
        "answers": [],
        "questions": load_questions()
    }

    emit('status', {'message': 'Connected to voice questionnaire'})

    # Greeting first
    greeting = "Hi, I have some questions I would like you to answer."
    emit('ai_response', {
        'text': greeting,
        'timestamp': datetime.now().strftime("%H:%M:%S")
    })
    audio = tts(greeting)
    if audio:
        emit('audio_response', {'audio': audio})

    # Send first question after greeting (client will handle the 5-second delay)
    q = current_question(sessions[sid])
    if q:
        emit('first_question', {
            'text': q["text"],
            'timestamp': datetime.now().strftime("%H:%M:%S"),
            'delay': 5000  # 5 second delay in milliseconds
        })
    else:
        emit('ai_response', {
            'text': "I don't have any questions to ask right now.",
            'timestamp': datetime.now().strftime("%H:%M:%S")
        })
        audio = tts("I don't have any questions to ask right now.")
        if audio:
            emit('audio_response', {'audio': audio})

@socketio.on('disconnect')
def on_disconnect():
    sid = request.sid
    print(f'Client disconnected: {sid}')
    sessions.pop(sid, None)

@socketio.on('audio_data')
def on_audio_data(data):
    """Handle incoming audio chunks from the browser."""
    sid = request.sid
    state = sessions.get(sid)
    if not state:
        emit('error', {'message': 'Session not initialized.'})
        return

    try:
        user_text = transcribe_audio(data['audio'])
        if not user_text:
            emit('error', {'message': 'Could not understand audio. Please try again.'})
            return

        # Save user message
        state["history"].append({"speaker": "user", "message": user_text})
        emit('transcription', {
            'text': user_text,
            'timestamp': datetime.now().strftime("%H:%M:%S")
        })

        # Store answer for current question
        q = current_question(state)
        if q:
            state["answers"].append({
                "id": q.get("id"),
                "question": q.get("text"),
                "answer": user_text
            })
            state["q_idx"] += 1  # advance to next question

        # Ask next question or finish
        next_q = current_question(state)
        if next_q:
            response_text = f"Thank you. {next_q['text']}"
            emit('ai_response', {
                'text': response_text,
                'timestamp': datetime.now().strftime("%H:%M:%S")
            })
            audio = tts(response_text)
            if audio:
                emit('audio_response', {'audio': audio})
        else:
            # Questionnaire completed - finish and trigger analysis
            thanks = "Thanks for your answers. We are done."
            emit('ai_response', {
                'text': thanks,
                'timestamp': datetime.now().strftime("%H:%M:%S")
            })
            audio = tts(thanks)
            if audio:
                emit('audio_response', {'audio': audio})

            # Save answers to file
            saved_file = save_answers_to_file(state["answers"], sid)

            # Send structured results back to the client
            emit('questionnaire_complete', {
                'answers': state["answers"],
                'saved_file': saved_file
            })

            # Trigger automatic analysis
            print("🔄 Triggering automatic analysis...")
            try:
                success = run_analysis_with_latest_responses()
                if success:
                    print("✅ Automatic analysis completed successfully")
                else:
                    print("❌ Automatic analysis failed")
            except Exception as e:
                print(f"❌ Error in automatic analysis: {e}")

    except Exception as e:
        print(f"[on_audio_data] {e}")
        emit('error', {'message': f'Error processing audio: {str(e)}'})

@socketio.on('get_history')
def on_get_history():
    sid = request.sid
    state = sessions.get(sid, {"history": []})
    emit('history', {'history': state["history"]})

@socketio.on('clear_history')
def on_clear_history():
    sid = request.sid
    state = sessions.get(sid)
    if state:
        state["history"].clear()
        state["answers"].clear()
        state["q_idx"] = 0
    emit('history_cleared', {'message': 'History cleared'})

if __name__ == '__main__':
    print("🚀 Starting Voice Questionnaire Server...")
    print("🌐 Open: http://localhost:5001")
    print("🎤 Check your microphone & speakers")
    socketio.run(app, debug=True, host='0.0.0.0', port=5001, allow_unsafe_werkzeug=True)
