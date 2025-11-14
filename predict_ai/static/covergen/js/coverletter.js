// -----------------------------------------------------
// DOM REFERENCES
// -----------------------------------------------------
const sessionId =
  'sess-' +
  Math.random().toString(36).slice(2, 10) +
  '-' +
  Date.now().toString(36);
const clientText = document.getElementById('clientText');
const urlInput = document.getElementById('urlInput');
const addUrlBtn = document.getElementById('addUrlBtn');
const urlList = document.getElementById('urlList');
const fileInput = document.getElementById('fileInput');
const generateBtn = document.getElementById('generateBtn');

// Progress UI
const progressArea = document.getElementById('progressArea');
const progressPct = document.getElementById('progressPct');
const progressCircle = document.getElementById('progressCircle');
const progressText = document.getElementById('progressText');
const subText = document.getElementById('subText');

// Output Results Elements
const coverLetterContentEl = document.querySelector('[contenteditable="true"]');
const structuredJsonEl = document.getElementById('structuredJson');

// SERVER STREAM URL
const STREAM_URL = '/api/genrate-cover-letter';
const MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024; // 10MB

// Storage for final results
let finalAnalysisData = null;
let finalCoverLetterText = null;

// -----------------------------------------------------
// INITIAL UI SETUP
// -----------------------------------------------------
function hideProgress() {
  progressArea.classList.add('hidden');
  progressPct.textContent = '0%';
  progressCircle.style.strokeDashoffset = '251.2';
}

function resetUI() {
  hideProgress();
  finalAnalysisData = null;
  finalCoverLetterText = null;
  coverLetterContentEl.innerHTML = '<p>Loading cover letter...</p>';
  // structuredJsonEl.textContent = '';
}

resetUI();

// -----------------------------------------------------
// URL LIST MANAGEMENT
// -----------------------------------------------------
function createUrlCard(url) {
  const card = document.createElement('div');
  card.className =
    'flex items-center justify-between p-3 bg-background-light border border-border-light rounded-lg';

  const left = document.createElement('div');
  left.className = 'flex items-center gap-3 overflow-hidden';

  const icon = document.createElement('span');
  icon.className = 'material-symbols-outlined text-primary';
  icon.textContent = 'link';

  const p = document.createElement('p');
  p.className = 'text-sm font-medium truncate';
  p.textContent = url;

  left.appendChild(icon);
  left.appendChild(p);

  const removeBtn = document.createElement('button');
  removeBtn.className = 'text-text-muted-light hover:text-red-500';
  removeBtn.innerHTML = '<span class="material-symbols-outlined">close</span>';

  removeBtn.addEventListener('click', () => {
    card.remove();
  });

  card.appendChild(left);
  card.appendChild(removeBtn);

  return card;
}

addUrlBtn.addEventListener('click', () => {
  const val = urlInput.value.trim();
  if (!val) return;

  try {
    new URL(val);
  } catch (e) {
    alert('Please enter a valid URL');
    return;
  }

  const card = createUrlCard(val);
  urlList.prepend(card);
  urlInput.value = '';
});

// -----------------------------------------------------
// FILE UPLOAD HANDLING
// -----------------------------------------------------
let selectedFile = null;

fileInput.addEventListener('change', (ev) => {
  const f = ev.target.files[0];
  if (!f) return;

  if (f.size > MAX_FILE_SIZE_BYTES) {
    alert('File too large. Max 10MB allowed.');
    fileInput.value = '';
    return;
  }

  selectedFile = f;

  const fileCard = document.createElement('div');
  fileCard.className =
    'flex items-center justify-between p-3 bg-background-light border border-border-light rounded-lg';

  const left = document.createElement('div');
  left.className = 'flex items-center gap-3 overflow-hidden';

  const icon = document.createElement('span');
  icon.className = 'material-symbols-outlined text-primary';
  icon.textContent = 'attach_file';

  const p = document.createElement('p');
  p.className = 'text-sm font-medium truncate';
  p.textContent = f.name;

  left.appendChild(icon);
  left.appendChild(p);

  const removeBtn = document.createElement('button');
  removeBtn.className = 'text-text-muted-light hover:text-red-500';
  removeBtn.innerHTML = '<span class="material-symbols-outlined">close</span>';

  removeBtn.addEventListener('click', () => {
    fileCard.remove();
    selectedFile = null;
    fileInput.value = '';
  });

  fileCard.appendChild(left);
  fileCard.appendChild(removeBtn);

  urlList.prepend(fileCard);
});

// -----------------------------------------------------
// PROGRESS UI
// -----------------------------------------------------
function setProgress(pct, text = 'Processing...') {
  progressArea.classList.remove('hidden');
  pct = Math.max(0, Math.min(100, pct));

  progressPct.textContent = pct + '%';
  progressText.textContent = text;

  const dashOffset = 251.2 * (1 - pct / 100);
  progressCircle.style.strokeDashoffset = dashOffset;
}

// -----------------------------------------------------
// POPULATE OUTPUT SECTIONS WITH BACKEND DATA
// -----------------------------------------------------
function populateOutput(analysisData, coverLetterText) {
  // 1. Display Cover Letter
  if (coverLetterText) {
    finalCoverLetterText = coverLetterText;
    // Format the cover letter with paragraph tags
    const paragraphs = coverLetterText.split('\n\n').filter(p => p.trim());
    coverLetterContentEl.innerHTML = paragraphs
      .map(para => `<p>${para.trim()}</p>`)
      .join('');
  }

  // 2. Display Structured JSON
  if (analysisData) {
    finalAnalysisData = analysisData;
    structuredJsonEl.textContent = JSON.stringify(analysisData, null, 2);
  }

  // 3. Populate Point-Wise Breakdown Cards
  if (analysisData) {
    populateBreakdownCards(analysisData);
  }
}

// Helper function to populate the breakdown cards
function populateBreakdownCards(data) {
  // Find and update each card based on data keys
  
  // Important Point
  const importantPointCard = document.querySelector('[data-section="important-point"]');
  if (importantPointCard && data.important_point) {
    const textEl = importantPointCard.querySelector('.card-content');
    if (textEl) textEl.textContent = data.important_point;
  }

  // Technical Questions
  const techQuestionsCard = document.querySelector('[data-section="tech-questions"]');
  if (techQuestionsCard && data.technical_questions && data.technical_questions.length > 0) {
    const textEl = techQuestionsCard.querySelector('.card-content');
    if (textEl) {
      textEl.innerHTML = data.technical_questions
        .map(q => `<li class="list-item">${q}</li>`)
        .join('');
    }
  }

  // Non-Technical Questions
  const nonTechQuestionsCard = document.querySelector('[data-section="non-tech-questions"]');
  if (nonTechQuestionsCard && data.non_technical_questions && data.non_technical_questions.length > 0) {
    const textEl = nonTechQuestionsCard.querySelector('.card-content');
    if (textEl) {
      textEl.innerHTML = data.non_technical_questions
        .map(q => `<li class="list-item">${q}</li>`)
        .join('');
    }
  }

  // Required Technologies
  const techCard = document.querySelector('[data-section="required-tech"]');
  if (techCard && data.technologies_needed && Object.keys(data.technologies_needed).length > 0) {
    const textEl = techCard.querySelector('.card-content');
    if (textEl) {
      let techHtml = '';
      for (const [category, techs] of Object.entries(data.technologies_needed)) {
        techHtml += `<div class="mb-3"><strong>${category}:</strong>`;
        techHtml += '<ul class="list-disc list-inside mt-1">';
        techs.forEach(tech => {
          techHtml += `<li>${tech}</li>`;
        });
        techHtml += '</ul></div>';
      }
      textEl.innerHTML = techHtml;
    }
  }

  // Non-Technical Requirements
  const nonTechReqCard = document.querySelector('[data-section="non-tech-req"]');
  if (nonTechReqCard && data.non_tech_requirements && data.non_tech_requirements.length > 0) {
    const textEl = nonTechReqCard.querySelector('.card-content');
    if (textEl) {
      textEl.innerHTML = data.non_tech_requirements
        .map(req => `<li class="list-item">${req}</li>`)
        .join('');
    }
  }

  // Project Scope / Relevant Experience
  const scopeCard = document.querySelector('[data-section="project-scope"]');
  if (scopeCard && data.project_scope) {
    const textEl = scopeCard.querySelector('.card-content');
    if (textEl) textEl.textContent = data.project_scope;
  }

  // Unclear Points
  const unclearCard = document.querySelector('[data-section="unclear-points"]');
  if (unclearCard && data.clarifying_questions && data.clarifying_questions.length > 0) {
    const textEl = unclearCard.querySelector('.card-content');
    if (textEl) {
      textEl.innerHTML = data.clarifying_questions
        .map(q => `<li class="list-item">${q}</li>`)
        .join('');
    }
  }

  // Brief Message (greeting + main objective)
  const briefCard = document.querySelector('[data-section="brief-message"]');
  if (briefCard && data.main_objective) {
    const textEl = briefCard.querySelector('.card-content');
    if (textEl) textEl.textContent = data.main_objective;
  }
}

// -----------------------------------------------------
// STREAMING (SSE-LIKE) FETCH HANDLER
// Buffer and display after completion
// -----------------------------------------------------
async function startStreaming(payload) {
  resetUI();

  let reader;
  try {
    const res = await fetch(STREAM_URL, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });

    if (!res.ok) {
      alert('Server error: ' + res.status);
      hideProgress();
      return;
    }

    reader = res.body.getReader();
  } catch (error) {
    alert('Network error: ' + error);
    hideProgress();
    return;
  }

  const decoder = new TextDecoder();
  let buf = '';
  let bufferedAnalysis = null;
  let bufferedCoverLetter = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buf += decoder.decode(value, { stream: true });

    let idx;
    while ((idx = buf.indexOf('\n\n')) !== -1) {
      let chunk = buf.slice(0, idx).trim();
      buf = buf.slice(idx + 2);

      if (!chunk) continue;

      const dataLines = chunk
        .split(/\r?\n/)
        .filter((l) => l.startsWith('data:'))
        .map((l) => l.replace('data:', '').trim());

      if (dataLines.length === 0) continue;

      let jsonText = dataLines.join('\n');

      let obj = null;
      try {
        obj = JSON.parse(jsonText);
      } catch {
        bufferedCoverLetter += jsonText;
        continue;
      }

      // Handle different event types
      if (obj.type === 'token' || obj.type === 'partial' || obj.type === 'partial_gen') {
        // Buffer tokens - don't display yet
        bufferedCoverLetter += obj.content || obj.token || '';

      } else if (obj.type === 'progress') {
        // Update progress bar
        const pct = Number(obj.percent) || 0;
        const msg = obj.message || 'Processing...';
        setProgress(pct, msg);

      } else if (obj.type === 'analysis_done') {
        // Store analysis data
        try {
          bufferedAnalysis = typeof obj.analysis === 'string' 
            ? JSON.parse(obj.analysis) 
            : obj.analysis;
        } catch (e) {
          console.error('Failed to parse analysis:', e);
        }

      } else if (obj.type === 'cover_letter_done') {
        // Backend explicitly sends the final cover letter
        if (obj.content) {
          bufferedCoverLetter = obj.content;
        }

      } else if (obj.type === 'done' || obj.type === 'finished') {
        // Final completion event - now display everything
        setProgress(100, 'Completed!');
        
        // Wait a moment then show output
        setTimeout(() => {
          populateOutput(bufferedAnalysis, bufferedCoverLetter);
          progressArea.classList.add('hidden')
          showOutput();
        }, 500);

      } else if (obj.type === 'error') {
        alert('Server error: ' + (obj.message || 'Unknown'));
        hideProgress();
        return;

      } else if (obj.type === 'usage') {
        // Optional: log token usage
        console.log('Token usage:', obj);
      }
    }
  }
}

// -----------------------------------------------------
// GENERATE BUTTON CLICK HANDLER
// -----------------------------------------------------
generateBtn.addEventListener('click', async () => {
  const text = clientText.value.trim();
  if (!text) {
    alert('Job description cannot be empty.');
    return;
  }

  // Collect URLs
  const urls = [];
  urlList.querySelectorAll('p').forEach((p) => urls.push(p.textContent));

  // Prepare file (base64)
  let fileBase64 = null;
  let filename = null;

  if (selectedFile) {
    filename = selectedFile.name;
    const arrBuf = await selectedFile.arrayBuffer();
    const chunkSize = 0x8000;
    const bytes = new Uint8Array(arrBuf);
    let binary = '';
    for (let i = 0; i < bytes.length; i += chunkSize) {
      const slice = bytes.subarray(i, i + chunkSize);
      binary += String.fromCharCode.apply(null, slice);
    }
    fileBase64 = btoa(binary);
  }

  const payload = {
    action: 'generate',
    client_text: text,
    context_snippets: urls,
    file_base64: fileBase64,
    file_name: filename,
    session_id: sessionId
  };

  // Show progress and start streaming
  progressArea.classList.remove('hidden');
  setProgress(1, 'Sending to server...');

  startStreaming(payload).catch((err) => {
    console.error('streaming error', err);
    hideProgress();
  });
});

// Optional: Ctrl+Enter to trigger generation
clientText.addEventListener('keydown', (e) => {
  if (e.ctrlKey && e.key === 'Enter') {
    generateBtn.click();
  }
});

// -----------------------------------------------------
// SECTION VISIBILITY/NAVIGATION
// -----------------------------------------------------
function showOutput() {
  const inputSection = document.getElementById('inputSection');
  const outputSection = document.getElementById('outputSection');

  inputSection.classList.add('hidden');
  outputSection.classList.remove('hidden');

  requestAnimationFrame(() => {
    outputSection.classList.add('show');
  });
}

function showInput() {
  const inputSection = document.getElementById('inputSection');
  const outputSection = document.getElementById('outputSection');

  outputSection.classList.remove('show');

  setTimeout(() => {
    outputSection.classList.add('hidden');
    inputSection.classList.remove('hidden');

    requestAnimationFrame(() => {
      inputSection.classList.add('show');
    });
  }, 200);
}

// Make functions globally available
window.showInput = showInput;
window.showOutput = showOutput;