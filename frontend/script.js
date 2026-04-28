let mediaRecorder;
let audioChunks = [];
let isRecording = false;

const recordBtn = document.getElementById('recordBtn');
const API_BASE_URL = (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1')
    ? 'http://localhost:8000'
    : '';

const micIcon = document.getElementById('micIcon');
const statusText = document.getElementById('statusText');
const transcriptionBox = document.getElementById('transcriptionBox');
const loadingState = document.getElementById('loadingState');
const resultSection = document.getElementById('resultSection');
const generatedImage = document.getElementById('generatedImage');
const downloadBtn = document.getElementById('downloadBtn');
const shareBtn = document.getElementById('shareBtn');
const newBtn = document.getElementById('newBtn');

recordBtn.addEventListener('click', toggleRecording);

async function toggleRecording() {
    if (!isRecording) {
        startRecording();
    } else {
        stopRecording();
    }
}

async function startRecording() {
    try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        
        // Detect supported mime types
        const types = [
            'audio/webm;codecs=opus',
            'audio/webm',
            'audio/ogg;codecs=opus',
            'audio/wav',
            'audio/mp4'
        ];
        const mimeType = types.find(t => MediaRecorder.isTypeSupported(t)) || '';
        
        console.log("Using MIME type:", mimeType);
        mediaRecorder = new MediaRecorder(stream, { mimeType });
        audioChunks = [];

        mediaRecorder.ondataavailable = (event) => {
            if (event.data.size > 0) {
                audioChunks.push(event.data);
            }
        };

        mediaRecorder.onstop = async () => {
            const finalType = mimeType.split(';')[0] || 'audio/webm';
            const audioBlob = new Blob(audioChunks, { type: finalType });
            console.log(`Sending blob: ${audioBlob.size} bytes, type: ${finalType}`);
            sendToBackend(audioBlob);
        };

        mediaRecorder.start();
        isRecording = true;
        recordBtn.classList.add('recording');
        micIcon.classList.remove('fa-microphone');
        micIcon.classList.add('fa-stop');
        statusText.innerText = "Listening... Click to stop";
        transcriptionBox.innerText = "Recording in progress...";
        resultSection.classList.add('hidden');
    } catch (err) {
        console.error("Error accessing microphone:", err);
        statusText.innerText = "Error: Could not access microphone";
    }
}

function stopRecording() {
    mediaRecorder.stop();
    isRecording = false;
    recordBtn.classList.remove('recording');
    micIcon.classList.add('fa-microphone');
    micIcon.classList.remove('fa-stop');
    statusText.innerText = "Processing audio...";
}

async function sendToBackend(blob) {
    loadingState.classList.remove('hidden');
    statusText.innerText = "Transcribing your voice...";

    const formData = new FormData();
    formData.append('audio', blob, 'audio.webm');

    try {
        const response = await fetch(`${API_BASE_URL}/api/speech-to-image`, {
            method: 'POST',
            body: formData
        });

        if (!response.ok) {
            const errData = await response.json().catch(() => ({}));
            throw new Error(errData.detail || `Server error: ${response.statusText}`);
        }

        const data = await response.json();
        await displayResult(data);
    } catch (err) {
        console.error("Error sending to backend:", err);
        statusText.innerText = `Error: ${err.message}`;
        transcriptionBox.innerText = "Something went wrong. Please try again.";
        loadingState.classList.add('hidden');
    }
}

/**
 * Polls a Pollinations image URL via fetch() with retries.
 * Pollinations generates images lazily — the first request triggers generation
 * and can take 15–30s. We retry until we get a successful image response.
 *
 * @param {string} url        - The Pollinations image URL
 * @param {number} maxRetries - How many times to retry (default 20)
 * @param {number} delay      - Delay between retries in ms (default 2000)
 * @returns {Promise<string>} - Resolves with an object URL for the image blob
 */
/**
 * Waits for an image to load via an Image object.
 * This is more robust against CORS/WAF issues than fetch().
 */
async function displayResult(data) {
    transcriptionBox.innerText = `"${data.transcription}"`;
    statusText.innerText = "Processing your creation...";
    loadingState.classList.remove('hidden');
    resultSection.classList.add('hidden');

    console.log("Backend response:", data);

    try {
        if (!data.image_url) throw new Error("No image URL received");

        // Prepend API_BASE_URL if the URL is a relative path
        const fullImageUrl = data.image_url.startsWith('/') 
            ? `${API_BASE_URL}${data.image_url}` 
            : data.image_url;

        console.log("Loading image from:", fullImageUrl);

        // Since the backend already downloaded it, it should load instantly
        generatedImage.src = fullImageUrl;

        // Reveal result after a tiny delay to ensure the browser paints
        generatedImage.onload = () => {
            loadingState.classList.add('hidden');
            resultSection.classList.remove('hidden');
            statusText.innerText = "Done! Here is your creation.";
            
            setTimeout(() => {
                resultSection.scrollIntoView({ behavior: 'smooth', block: 'center' });
            }, 100);
        };

        generatedImage.onerror = () => {
            throw new Error("Failed to load image from local storage");
        };

        generatedImage.dataset.originalUrl = fullImageUrl;

    } catch (err) {
        console.error("Image load failed:", err);
        loadingState.classList.add('hidden');
        statusText.innerText = "Error: Could not display image.";
        transcriptionBox.innerText = `Transcript: "${data.transcription}" — but the image failed to load. Please try again!`;
    }
}

// Download via blob to bypass CORS on external CDN URLs
downloadBtn.addEventListener('click', async () => {
    const src = generatedImage.src;
    if (!src) return;

    try {
        // If already a blob URL, fetch it directly; otherwise re-fetch
        const response = await fetch(src);
        const blob = await response.blob();
        const blobUrl = URL.createObjectURL(blob);

        const link = document.createElement('a');
        link.href = blobUrl;
        link.download = 'vocalvision-creation.png';
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);

        setTimeout(() => URL.revokeObjectURL(blobUrl), 5000);
    } catch (err) {
        console.error("Download failed:", err);
        window.open(generatedImage.dataset.originalUrl || src, '_blank');
    }
});

shareBtn.addEventListener('click', async () => {
    const shareUrl = generatedImage.dataset.originalUrl || generatedImage.src;
    const text = transcriptionBox.innerText;

    if (navigator.share) {
        try {
            await navigator.share({
                title: 'VocalVision Creation',
                text: `I generated this image using my voice: ${text}`,
                url: shareUrl
            });
        } catch (err) {
            console.log('Share cancelled or failed:', err);
        }
    } else {
        await navigator.clipboard.writeText(shareUrl);
        alert('Image link copied to clipboard!');
    }
});

newBtn.addEventListener('click', () => {
    resultSection.classList.add('hidden');
    transcriptionBox.innerText = '';
    transcriptionBox.innerHTML = '<span class="placeholder-text">Your spoken prompt will appear here...</span>';
    statusText.innerText = "Click to start speaking";
    generatedImage.src = '';
    generatedImage.dataset.originalUrl = '';
});