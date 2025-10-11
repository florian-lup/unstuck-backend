/**
 * Example Electron client for voice chat WebSocket connection
 * 
 * This example shows how to connect to the voice chat WebSocket endpoint
 * and handle bidirectional audio streaming.
 */

class VoiceChatClient {
  constructor(serverUrl = 'ws://localhost:8000/api/v1/voice/ws') {
    this.serverUrl = serverUrl;
    this.ws = null;
    this.sessionId = null;
    this.audioChunks = [];
    this.isRecording = false;
  }

  /**
   * Connect to the voice chat WebSocket server
   * Note: System prompt and voice are configured on the backend
   */
  connect() {
    return new Promise((resolve, reject) => {
      this.ws = new WebSocket(this.serverUrl);
      this.sessionId = this.generateSessionId();

      this.ws.onopen = () => {
        console.log('WebSocket connected');
        
        // Send start session message
        this.send({
          type: 'start_session',
          session_id: this.sessionId
        });
      };

      this.ws.onmessage = (event) => {
        const message = JSON.parse(event.data);
        this.handleMessage(message);

        if (message.type === 'session_started') {
          resolve();
        }
      };

      this.ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        reject(error);
      };

      this.ws.onclose = () => {
        console.log('WebSocket disconnected');
      };
    });
  }

  /**
   * Send a message to the server
   */
  send(message) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(message));
    }
  }

  /**
   * Send an audio chunk to the server
   * @param {ArrayBuffer} audioData - wav audio data
   */
  sendAudioChunk(audioData) {
    // Convert ArrayBuffer to base64
    const base64Audio = this.arrayBufferToBase64(audioData);
    
    this.send({
      type: 'audio_chunk',
      session_id: this.sessionId,
      audio_data: base64Audio,
      format: 'wav'
    });
  }

  /**
   * Signal end of audio input
   */
  endAudio() {
    this.send({
      type: 'audio_end',
      session_id: this.sessionId
    });
  }

  /**
   * End the session
   */
  endSession() {
    this.send({
      type: 'end_session',
      session_id: this.sessionId
    });
  }

  /**
   * Close the WebSocket connection
   */
  close() {
    if (this.ws) {
      this.endSession();
      this.ws.close();
    }
  }

  /**
   * Handle incoming messages from the server
   */
  handleMessage(message) {
    switch (message.type) {
      case 'session_started':
        console.log('Session started:', message.session_id);
        this.onSessionStarted && this.onSessionStarted(message);
        break;

      case 'transcription':
        console.log('Transcription:', message.text);
        this.onTranscription && this.onTranscription(message.text);
        break;

      case 'response_text':
        console.log('Response text:', message.text);
        this.onResponseText && this.onResponseText(message.text);
        break;

      case 'audio_stream_start':
        console.log('Audio stream started');
        this.audioChunks = [];
        this.onAudioStreamStart && this.onAudioStreamStart();
        break;

      case 'audio_stream_chunk':
        // Decode base64 audio chunk
        const audioChunk = this.base64ToArrayBuffer(message.audio_data);
        this.audioChunks.push(audioChunk);
        this.onAudioChunk && this.onAudioChunk(audioChunk);
        break;

      case 'audio_stream_end':
        console.log('Audio stream ended');
        this.onAudioStreamEnd && this.onAudioStreamEnd(this.audioChunks);
        break;

      case 'error':
        console.error('Error:', message.error);
        this.onError && this.onError(message.error);
        break;

      case 'session_ended':
        console.log('Session ended');
        this.onSessionEnded && this.onSessionEnded();
        break;

      default:
        console.warn('Unknown message type:', message.type);
    }
  }

  /**
   * Generate a unique session ID
   */
  generateSessionId() {
    return `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }

  /**
   * Convert ArrayBuffer to base64
   */
  arrayBufferToBase64(buffer) {
    const bytes = new Uint8Array(buffer);
    let binary = '';
    for (let i = 0; i < bytes.byteLength; i++) {
      binary += String.fromCharCode(bytes[i]);
    }
    return btoa(binary);
  }

  /**
   * Convert base64 to ArrayBuffer
   */
  base64ToArrayBuffer(base64) {
    const binaryString = atob(base64);
    const bytes = new Uint8Array(binaryString.length);
    for (let i = 0; i < binaryString.length; i++) {
      bytes[i] = binaryString.charCodeAt(i);
    }
    return bytes.buffer;
  }
}

// ============================================================================
// Example usage in Electron renderer process
// ============================================================================

// Initialize the client
const client = new VoiceChatClient('ws://localhost:8000/api/v1/voice/ws');

// Set up event handlers
client.onSessionStarted = () => {
  console.log('Voice chat session started!');
};

client.onTranscription = (text) => {
  console.log('You said:', text);
  // Update UI to show transcription
};

client.onResponseText = (text) => {
  console.log('Assistant says:', text);
  // Update UI to show response
};

client.onAudioStreamStart = () => {
  console.log('Receiving audio response...');
};

client.onAudioChunk = (audioChunk) => {
  // Play audio chunk immediately for low latency
  playAudioChunk(audioChunk);
};

client.onAudioStreamEnd = (allChunks) => {
  console.log('Audio response complete');
};

client.onError = (error) => {
  console.error('Voice chat error:', error);
};

// Connect to the server (system prompt and voice are configured on backend)
await client.connect();

// ============================================================================
// Recording and sending audio
// ============================================================================

let mediaRecorder;
let audioContext;
let audioStream;

async function startRecording() {
  // Get microphone access
  audioStream = await navigator.mediaDevices.getUserMedia({ 
    audio: {
      channelCount: 1,
      sampleRate: 16000,
      echoCancellation: true,
      noiseSuppression: true
    } 
  });

  // Create audio context for processing
  audioContext = new (window.AudioContext || window.webkitAudioContext)({
    sampleRate: 16000
  });

  const source = audioContext.createMediaStreamSource(audioStream);
  const processor = audioContext.createScriptProcessor(4096, 1, 1);

  source.connect(processor);
  processor.connect(audioContext.destination);

  // Send audio chunks as they're captured
  processor.onaudioprocess = (e) => {
    const inputData = e.inputBuffer.getChannelData(0);
    const pcmData = new Int16Array(inputData.length);
    
    // Convert Float32Array to Int16Array (PCM)
    for (let i = 0; i < inputData.length; i++) {
      const s = Math.max(-1, Math.min(1, inputData[i]));
      pcmData[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
    }
    
    // Send chunk to server
    client.sendAudioChunk(pcmData.buffer);
  };

  console.log('Recording started');
}

function stopRecording() {
  if (audioContext) {
    audioContext.close();
  }
  if (audioStream) {
    audioStream.getTracks().forEach(track => track.stop());
  }
  
  // Signal end of audio
  client.endAudio();
  
  console.log('Recording stopped');
}

// ============================================================================
// Playing audio response
// ============================================================================

let audioPlaybackContext;
let audioQueue = [];
let isPlaying = false;

function playAudioChunk(audioChunk) {
  if (!audioPlaybackContext) {
    audioPlaybackContext = new (window.AudioContext || window.webkitAudioContext)();
  }

  // Decode and play the PCM audio
  audioPlaybackContext.decodeAudioData(audioChunk.slice(0), (buffer) => {
    const source = audioPlaybackContext.createBufferSource();
    source.buffer = buffer;
    source.connect(audioPlaybackContext.destination);
    source.start(0);
  }, (error) => {
    console.error('Error decoding audio:', error);
  });
}

// ============================================================================
// Example: Push-to-talk button
// ============================================================================

const talkButton = document.getElementById('talk-button');

talkButton.addEventListener('mousedown', () => {
  startRecording();
});

talkButton.addEventListener('mouseup', () => {
  stopRecording();
});

// ============================================================================
// Cleanup
// ============================================================================

window.addEventListener('beforeunload', () => {
  client.close();
});

