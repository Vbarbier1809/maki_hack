const socket = io();
const logEl = document.getElementById('log');
const answersEl = document.getElementById('answers');
const btn = document.getElementById('recordBtn');
const analyzeBtn = document.getElementById('analyzeBtn');
const analysisStatusEl = document.getElementById('analysisStatus');

let mediaRecorder = null;
let audioChunks = [];

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

socket.on('connect', () => {
  logLine('System', 'Connected');
});
socket.on('status', (d) => logLine('System', d.message));
socket.on('error', (d) => logLine('Error', d.message));

socket.on('transcription', (d) => logLine('You', d.text));
socket.on('ai_response', (d) => logLine('Agent', d.text));
socket.on('audio_response', (d) => playBase64Wav(d.audio));

// Handle first question with delay
socket.on('first_question', (d) => {
  setTimeout(() => {
    // Don't log the text again since greeting was already displayed
    // Just convert text to speech for the first question
    fetch('/tts', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text: d.text })
    })
    .then(response => response.json())
    .then(data => {
      if (data.audio) {
        playBase64Wav(data.audio);
      }
    })
    .catch(error => console.error('TTS Error:', error));
  }, d.delay || 5000); // Default to 5 seconds if no delay specified
});

socket.on('questionnaire_complete', ({answers, saved_file}) => {
  answersEl.style.display = 'block';
  let content = `<strong>Answers:</strong><pre>${JSON.stringify(answers, null, 2)}</pre>`;
  if (saved_file) {
    content += `<br><strong>✅ Saved to file:</strong> ${saved_file}`;
  }
  answersEl.innerHTML = content;
});

btn.addEventListener('click', async () => {
  if (!mediaRecorder || mediaRecorder.state === 'inactive') {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      mediaRecorder = new MediaRecorder(stream, { mimeType: 'audio/webm' });

      mediaRecorder.ondataavailable = (e) => {
        if (e.data.size > 0) audioChunks.push(e.data);
      };

      mediaRecorder.onstop = async () => {
        const blob = new Blob(audioChunks, { type: 'audio/webm' });
        audioChunks = [];

        // Convert to WAV using WebAudio (simple approach: decode+re-encode PCM in browser)
        // For simplicity here, we send the webm and rely on server to accept wav only.
        // So we'll transcode to WAV here via offline AudioContext.

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
      btn.textContent = 'Stop Recording';
      logLine('System', 'Recording...');
    } catch (error) {
      console.error('Error accessing microphone:', error);
      logLine('Error', 'Microphone access denied. Please allow microphone access and try again.');
    }
  } else {
    mediaRecorder.stop();
    btn.textContent = 'Start Recording';
  }
});

// --- Helpers: WAV encoding ---
function encodeWAV(audioBuffer) {
  const numChannels = audioBuffer.numberOfChannels;
  const sampleRate = audioBuffer.sampleRate;
  const samples = audioBuffer.length;

  // Interleave & convert to 16-bit PCM
  const interleaved = interleave(audioBuffer);
  const dataLen = interleaved.length * 2; // 16-bit
  const buffer = new ArrayBuffer(44 + dataLen);
  const view = new DataView(buffer);

  writeUTFBytes(view, 0, 'RIFF');
  view.setUint32(4, 36 + dataLen, true);
  writeUTFBytes(view, 8, 'WAVE');
  writeUTFBytes(view, 12, 'fmt ');
  view.setUint32(16, 16, true); // PCM
  view.setUint16(20, 1, true);  // PCM
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
  const length = audioBuffer.length * numChannels;
  const result = new Float32Array(length);
  const channels = [];
  for (let c = 0; c < numChannels; c++) channels.push(audioBuffer.getChannelData(c));
  let index = 0;
  for (let i = 0; i < audioBuffer.length; i++) {
    for (let c = 0; c < numChannels; c++) result[index++] = channels[c][i];
  }
  return result;
}

function writeUTFBytes(view, offset, str) {
  for (let i = 0; i < str.length; i++) {
    view.setUint8(offset + i, str.charCodeAt(i));
  }
}

function arrayBufferToBase64(buffer) {
  const bytes = new Uint8Array(buffer);
  let binary = '';
  for (let i = 0; i < bytes.byteLength; i++) binary += String.fromCharCode(bytes[i]);
  return btoa(binary);
}

// Analysis functionality
analyzeBtn.addEventListener('click', async () => {
  try {
    analyzeBtn.disabled = true;
    analyzeBtn.textContent = '🔄 Analyzing...';
    analysisStatusEl.style.display = 'block';
    analysisStatusEl.style.backgroundColor = '#fff3cd';
    analysisStatusEl.style.border = '1px solid #ffeaa7';
    analysisStatusEl.innerHTML = '🔄 Running analysis with ChatGPT...';
    
    const response = await fetch('/analyze', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      }
    });
    
    const result = await response.json();
    
    if (result.status === 'success') {
      analysisStatusEl.style.backgroundColor = '#d4edda';
      analysisStatusEl.style.border = '1px solid #c3e6cb';
      analysisStatusEl.innerHTML = `✅ ${result.message}<br>📁 Analysis saved to completed_questions_*.json<br>🕒 ${new Date(result.timestamp).toLocaleString()}`;
      logLine('System', 'Analysis completed successfully!');
    } else {
      analysisStatusEl.style.backgroundColor = '#f8d7da';
      analysisStatusEl.style.border = '1px solid #f5c6cb';
      analysisStatusEl.innerHTML = `❌ ${result.message}`;
      logLine('Error', result.message);
    }
  } catch (error) {
    console.error('Analysis error:', error);
    analysisStatusEl.style.backgroundColor = '#f8d7da';
    analysisStatusEl.style.border = '1px solid #f5c6cb';
    analysisStatusEl.innerHTML = `❌ Error: ${error.message}`;
    logLine('Error', `Analysis failed: ${error.message}`);
  } finally {
    analyzeBtn.disabled = false;
    analyzeBtn.textContent = '📊 Analyze Responses';
  }
});
