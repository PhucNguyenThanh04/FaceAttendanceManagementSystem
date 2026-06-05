const AI_SERVICE_BASE_URL = 'http://localhost:8001';

const startBtn = document.getElementById('startBtn');
const stopBtn = document.getElementById('stopBtn');
const reloadBtn = document.getElementById('reloadBtn');
const stream = document.getElementById('stream');
const statusBox = document.getElementById('status');
const STREAM_FPS = 10;

function attendanceUrl(path) {
  return `${AI_SERVICE_BASE_URL}/api/v1/attendance${path}`;
}

function loadStream() {
  stream.src = `${attendanceUrl('/stream')}?fps=${STREAM_FPS}&t=${Date.now()}`;
}

async function request(path, method = 'GET') {
  const res = await fetch(attendanceUrl(path), { method });
  const data = await res.json();
  if (statusBox) {
    statusBox.textContent = JSON.stringify(data, null, 2);
  }
  return data;
}


startBtn.onclick = async () => {
  await request('/start', 'POST');
  loadStream();
};

stopBtn.onclick = async () => {
  await request('/stop', 'POST');
};

reloadBtn.onclick = loadStream;

loadStream();
