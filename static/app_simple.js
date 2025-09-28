const socket = io();
const logEl = document.getElementById('log');
const answersEl = document.getElementById('answers');
const btn = document.getElementById('recordBtn');
const analyzeBtn = document.getElementById('analyzeBtn');
const analysisStatusEl = document.getElementById('analysisStatus');

let mediaRecorder = null;
let audioChunks = [];
let isRecording = false;
let questionnaireStarted = false;

function logLine(who, text) {
  const row = document.createElement('div');
  row.className = 'msg';
  row.innerHTML = `<span class="who">${who}:</span><span>${text}</span>`;
  logEl.appendChild(row);
  logEl.scrollTop = logEl.scrollHeight;
}

function playBase64Wav(b64) {
  const audio = new Audio("data:audio/wav;base64," + b64);
  audio.play();
}

// Socket events
socket.on('connect', () => {
  logLine('System', 'Connected - Click "Start Recording" to begin');
  btn.style.display = 'block'; // Show button immediately
  btn.disabled = false;
});

socket.on('status', (d) => {
  logLine('System', d.message);
});

socket.on('ai_response', (d) => {
  logLine('Agent', d.text);
});

socket.on('audio_response', (d) => {
  playBase64Wav(d.audio);
});

socket.on('transcription', (d) => {
  logLine('You', d.text);
});

socket.on('question_ready', (d) => {
  btn.style.display = 'block';
  btn.disabled = false;
  btn.textContent = 'Start Recording';
  logLine('System', 'Question ready - click "Start Recording" to answer');
});

socket.on('questionnaire_complete', (d) => {
  btn.style.display = 'none';
  logLine('System', 'Questionnaire complete!');
  logLine('System', `Answers: ${JSON.stringify(d.answers, null, 2)}`);
});

socket.on('error', (d) => {
  logLine('Error', d.message);
});

// Handle first question with delay
socket.on('first_question', (d) => {
  setTimeout(() => {
    // Display the question text
    logLine('Agent', d.text, 'agent');
    
    // Convert text to speech for the first question
    fetch('/tts', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text: d.text })
    })
    .then(response => response.json())
    .then(data => {
      if (data.audio) {
        playBase64Wav(data.audio);
        // Show record button after TTS
        setTimeout(() => {
          btn.style.display = 'block';
          btn.disabled = false;
          btn.textContent = 'Start Recording';
          logLine('System', 'Question ready - click "Start Recording" to answer');
        }, 1000);
      }
    })
    .catch(error => console.error('TTS Error:', error));
  }, d.delay || 2000); // Default to 2 seconds if no delay specified
});

// Recording functions
async function startRecording() {
  if (isRecording) return;
  
  try {
    // First time: start the questionnaire
    if (!questionnaireStarted) {
      socket.emit('start_questionnaire');
      logLine('System', 'Starting questionnaire...');
      questionnaireStarted = true;
      btn.disabled = true;
      btn.textContent = 'Loading...';
      return;
    }
    
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    mediaRecorder = new MediaRecorder(stream, { mimeType: 'audio/webm' });

    mediaRecorder.ondataavailable = (e) => {
      if (e.data.size > 0) audioChunks.push(e.data);
    };

    mediaRecorder.onstop = async () => {
      const blob = new Blob(audioChunks, { type: 'audio/webm' });
      audioChunks = [];

      // Convert to WAV using WebAudio
      const arrayBuf = await blob.arrayBuffer();
      const ctx = new (window.AudioContext || window.webkitAudioContext)();
      const audioBuf = await ctx.decodeAudioData(arrayBuf);

      // Encode PCM 16-bit WAV
      const wavBuf = encodeWAV(audioBuf);
      const b64 = arrayBufferToBase64(wavBuf);

      socket.emit('audio_data', { audio: b64 });
      logLine('System', 'Audio sent');
    };

    mediaRecorder.start();
    isRecording = true;
    btn.textContent = 'Stop Recording';
    btn.disabled = false;
    logLine('System', 'Recording... Click "Stop Recording" when done');
  } catch (error) {
    console.error('Error accessing microphone:', error);
    logLine('Error', 'Microphone access denied. Please allow microphone access and try again.');
  }
}

function stopRecording() {
  if (mediaRecorder && isRecording) {
    mediaRecorder.stop();
    isRecording = false;
    btn.textContent = 'Processing...';
    btn.disabled = true;
    logLine('System', 'Recording stopped, processing...');
  }
}

btn.addEventListener('click', async () => {
  if (!isRecording) {
    await startRecording();
  } else {
    stopRecording();
  }
});

// Analysis button
analyzeBtn.addEventListener('click', async () => {
  analysisStatusEl.textContent = 'Running analysis...';
  analyzeBtn.disabled = true;
  
  try {
    const response = await fetch('/analyze', { method: 'POST' });
    const data = await response.json();
    
    if (data.success) {
      analysisStatusEl.textContent = `Analysis complete! Output: ${data.output_file}`;
      logLine('System', `Analysis complete! Output: ${data.output_file}`);
    } else {
      analysisStatusEl.textContent = `Analysis failed: ${data.error}`;
      logLine('Error', `Analysis failed: ${data.error}`);
    }
  } catch (error) {
    analysisStatusEl.textContent = `Analysis error: ${error.message}`;
    logLine('Error', `Analysis error: ${error.message}`);
  } finally {
    analyzeBtn.disabled = false;
  }
});

// WAV encoding functions
function encodeWAV(audioBuffer) {
  const numChannels = audioBuffer.numberOfChannels;
  const sampleRate = audioBuffer.sampleRate;
  const samples = audioBuffer.length;

  const interleaved = interleave(audioBuffer);
  const dataLen = interleaved.length * 2;
  const buffer = new ArrayBuffer(44 + dataLen);
  const view = new DataView(buffer);

  writeUTFBytes(view, 0, 'RIFF');
  view.setUint32(4, 36 + dataLen, true);
  writeUTFBytes(view, 8, 'WAVE');
  writeUTFBytes(view, 12, 'fmt ');
  view.setUint32(16, 16, true);
  view.setUint16(20, 1, true);
  view.setUint16(22, numChannels, true);
  view.setUint32(24, sampleRate, true);
  view.setUint32(28, sampleRate * numChannels * 2, true);
  view.setUint16(32, numChannels * 2, true);
  view.setUint16(34, 16, true);
  writeUTFBytes(view, 36, 'data');
  view.setUint32(40, dataLen, true);

  let offset = 44;
  for (let i = 0; i < interleaved.length; i++, offset += 2) {
    const s = Math.max(-1, Math.min(1, interleaved[i]));
    view.setInt16(offset, s < 0 ? s * 0x8000 : s * 0x7FFF, true);
  }
  return buffer;
}

function interleave(audioBuffer) {
  const numChannels = audioBuffer.numberOfChannels;
  const length = audioBuffer.length;
  const result = new Float32Array(length * numChannels);
  let offset = 0;
  for (let i = 0; i < length; i++) {
    for (let channel = 0; channel < numChannels; channel++) {
      result[offset++] = audioBuffer.getChannelData(channel)[i];
    }
  }
  return result;
}

function writeUTFBytes(view, offset, string) {
  for (let i = 0; i < string.length; i++) {
    view.setUint8(offset + i, string.charCodeAt(i));
  }
}

function arrayBufferToBase64(buffer) {
  let binary = '';
  const bytes = new Uint8Array(buffer);
  for (let i = 0; i < bytes.byteLength; i++) {
    binary += String.fromCharCode(bytes[i]);
  }
  return btoa(binary);
}
