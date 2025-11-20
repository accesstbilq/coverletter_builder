// -----------------------------------------------------
// DOM REFERENCES
// -----------------------------------------------------
const sessionId =
  'sess-' +
  Math.random().toString(36).slice(2, 10) +
  '-' +
  Date.now().toString(36);
const clientText = document.getElementById('clientText'),
urlInput = document.getElementById('urlInput'),
addUrlBtn = document.getElementById('addUrlBtn'),
urlList = document.getElementById('urlList'),
fileInput = document.getElementById('fileInput'),
generateBtn = document.getElementById('generateBtn'),
regenerateBtn = document.getElementById('regenerate'),
errors = document.getElementById('errors'),
copyBtn = document.getElementById('copyCoverBtn'),
copyFeedback = document.getElementById('copyCoverFeedback');
let loaderInterval;
let loaderSeconds = 0;

// Progress UI
const progressPct = document.getElementById('progressPct'),
progressCircle = document.getElementById('progressCircle'),
progressText = document.getElementById('progressText'),
subText = document.getElementById('subText'),
progressOverlay = document.getElementById('progressOverlay');

// Output Results Elements
const coverLetterContentEl = document.querySelector('#coverLetterContentEl'),
structuredJsonEl = document.getElementById('structuredJson');

// SERVER STREAM URL
const STREAM_URL = '/api/genrate-cover-letter';
const MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024; // 10MB

// Storage for final results
let finalAnalysisData = null;
let finalCoverLetterText = null;

// Category selection tracking
let selectedCategories = [];

//JSON data element
const briefCard = document.querySelector('[data-section="brief-message"]'),
  scopeCard = document.querySelector('[data-section="project-scope"]'),
  techCard = document.querySelector('[data-section="required-tech"]'),
  nonTechReqCard = document.querySelector('[data-section="non-tech-req"]'),
  unclearCard = document.querySelector('[data-section="unclear-points"]'),
  techQuestionsCard = document.querySelector('[data-section="tech-questions"]'),
  nonTechQuestionsCard = document.querySelector(
    '[data-section="non-tech-questions"]'
  ),
  importantPointCard = document.querySelector(
    '[data-section="important-point"]'
  ),
  Recommendations = document.querySelector('[data-section="recommendations"]'),
  refrenceWeb = document.querySelector('[data-section="reference-websites"]');
// -----------------------------------------------------
// INITIAL UI SETUP
// -----------------------------------------------------
function hideProgress() {
  generateBtn.disabled = false;
  progressOverlay.classList.add('hidden');
  document.body.classList.remove('overflow-hidden');
  clearInterval(loaderInterval);
}

function clearCard(card) {
  if (!card) return;
  const content = card.querySelector('.card-content');
  if (content) content.textContent = '';
}

function resetUI() {
  hideProgress();
  finalAnalysisData = null;
  finalCoverLetterText = null;

  if (coverLetterContentEl) {
    coverLetterContentEl.innerHTML = '<p>Loading cover letter...</p>';
  }

  clearCard(briefCard);
  clearCard(scopeCard);
  clearCard(techCard);
  clearCard(nonTechReqCard);
  clearCard(unclearCard);
  clearCard(techQuestionsCard);
  clearCard(nonTechQuestionsCard);
  clearCard(importantPointCard);
  clearCard(Recommendations);
  clearCard(refrenceWeb);

  if (errors && !errors.classList.contains('hidden')) {
    errors.classList.add('hidden');
  }
}


resetUI();

function cleanModelDividers(text) {
  return text
    .replace(/\r/g, '') // normalize CRLF
    .replace(/(^|\n)\s*={3,}\s*($|\n)/g, '\n') // remove ===== lines
    .replace(/(^|\n)\s*-{3,}\s*($|\n)/g, '\n') // remove --- lines
    .replace(/(^|\n)\s*#{1,6}\s*OUTPUT\s*\d+.*($|\n)/gi, '') // remove "OUTPUT" headings
    .replace('human_proposal_text', '')
    .replace('structured_data', '')
    .trim();
}

// If the model accidentally appended JSON at the end, strip it off.
// Heuristic: take substring from first "{" to last "}" and attempt JSON.parse;
// if valid, remove that substring from the main text.
function stripTrailingJsonBlock(text) {
  const firstBrace = text.indexOf('{');
  if (firstBrace === -1) return text;
  const lastBrace = text.lastIndexOf('}');
  if (lastBrace <= firstBrace) return text;
  const candidate = text.slice(firstBrace, lastBrace + 1);
  try {
    JSON.parse(candidate);
    return text.slice(0, firstBrace).trim();
  } catch (e) {
    return text;
  }
}

// Render cleaned text into human-friendly paragraphs.
function renderCoverLetter(rawContent) {
  if (!rawContent || !rawContent.trim()) {
    coverLetterContentEl.innerHTML =
      '<p class="empty-note">No cover letter returned.</p>';
    return '';
  }

  let cleaned = cleanModelDividers(rawContent);
  cleaned = stripTrailingJsonBlock(cleaned);

  // Split paragraphs on two-or-more newlines; preserve single-line breaks inside paragraphs.
  const paragraphs = cleaned
    .split(/\n{2,}/)
    .map((p) => p.trim())
    .filter(Boolean);

  // Helper: append a paragraph element that preserves single-line breaks
  function appendParagraphWithLineBreaks(container, text) {
    // Create <p> element
    const pEl = document.createElement('p');
    pEl.className = ''; // keep classes if you want: e.g., 'prose-p'
    // Split by single newline to preserve line breaks
    const lines = text.split('\n');

    lines.forEach((line, idx) => {
      // Create a safe text node
      const tn = document.createTextNode(line);
      pEl.appendChild(tn);

      // If not last line, insert a <br> to preserve the newline
      if (idx < lines.length - 1) {
        pEl.appendChild(document.createElement('br'));
      }
    });

    container.appendChild(pEl);
  }

  // Build DOM safely using textContent & <br> nodes for internal newlines
  coverLetterContentEl.innerHTML = '';
  paragraphs.forEach((para, index) => {
    appendParagraphWithLineBreaks(coverLetterContentEl, para);

    // Add TWO <br> elements between paragraphs to create a visible blank line
    if (index < paragraphs.length - 1) {
      coverLetterContentEl.appendChild(document.createElement('br'));
      // coverLetterContentEl.appendChild(document.createElement('br'));
    }
  });

  // Return the full clean text to use for copying (paragraphs separated by two newlines)
  return paragraphs.join('\n\n');
}

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
  const files = ev.target.files;
  if (!files || files.length === 0) return;

  const f = files[0]; // Get the actual file object

  if (f.size > MAX_FILE_SIZE_BYTES) {
    alert('File too large. Max 10MB allowed.');
    fileInput.value = '';
    return;
  }

  // 2. Type Validation (PDF and Text)
  // Check for PDF specific MIME, generic text MIME, or common text-based extensions
  const isPdf = f.type === 'application/pdf';
  const isText =
    f.type.startsWith('text/') ||
    /\.(txt|md|csv|json|js|py|html|css|xml|log|ini|yaml|yml|rb|c|cpp|h)$/i.test(
      f.name
    );

  if (!isPdf && !isText) {
    alert('Invalid file type. Please upload a PDF or a Text file.');
    fileInput.value = ''; // Clear the invalid selection
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
// CATEGORY SELECTION HANDLING
// -----------------------------------------------------
document.querySelectorAll('.category-checkbox').forEach((checkbox) => {
  checkbox.addEventListener('change', (e) => {
    if (e.target.checked) {
      // Add to selected categories
      if (!selectedCategories.includes(e.target.value)) {
        selectedCategories.push(e.target.value);
      }
    } else {
      // Remove from selected categories
      selectedCategories = selectedCategories.filter(
        (cat) => cat !== e.target.value
      );
    }
    console.log('Selected categories:', selectedCategories);
  });
});

// -----------------------------------------------------
// PROGRESS UI
// -----------------------------------------------------
function setProgress(pct, text = 'Processing...') {
  document.body.classList.add('overflow-hidden');
  generateBtn.disabled = true;

  const dashOffset = 251.2 * (1 - pct / 100);
  const circle = document.getElementById('progressCircle1');
  const pctText = document.getElementById('progressPct1');
  const progressText1 = document.getElementById('progressText1');
  const subTextEl = document.getElementById('subText1');

  circle.style.strokeDashoffset = dashOffset;
  pctText.textContent = pct + '%';
  progressText1.textContent = text;

  progressOverlay.classList.remove('hidden');
}

// -----------------------------------------------------
// POPULATE OUTPUT SECTIONS WITH BACKEND DATA
// -----------------------------------------------------

// Helper function to populate the breakdown cards
function populateBreakdownCards(data) {
  console.log('[DEBUG] populateBreakdownCards received:', data);

  if (!data) {
    console.warn('[DEBUG] No data provided to populateBreakdownCards');
    return;
  }

  // ========================================
  // CARD 1: Main Objective (from main_objective field)
  // ========================================

  if (briefCard) {
    if (data.main_objective && data.main_objective.trim()) {
      const textEl = briefCard.querySelector('.card-content');
      if (textEl) textEl.textContent = data.main_objective;
      briefCard.classList.remove('hidden');
      console.log(
        '[DEBUG] Populated brief-message card with:',
        data.main_objective.substring(0, 50)
      );
    } else {
      briefCard.classList.add('hidden');
    }
  }

  // ========================================
  // CARD 2: Project Scope / Relevant Experience
  // ========================================
  if (scopeCard) {
    const textEl = scopeCard.querySelector('.card-content');
    if (data.experience_summary && !Array.isArray(data.experience_summary)) {
      if (textEl) textEl.textContent = data.experience_summary;
      scopeCard.classList.remove('hidden');
    } else {
      if (
      data.experience_summary &&
      Array.isArray(data.experience_summary) &&
      data.experience_summary.length > 0
    ) {
       const filteredReqs = data.experience_summary.filter(
          (req) => req && req.trim()
        );
        if (filteredReqs.length > 0) {
          textEl.innerHTML = filteredReqs
            .map((req) => `<li class="list-item">${req}</li>`)
            .join('');
        }

    }
      scopeCard.classList.add('hidden');
    }
  }

  // ========================================
  // CARD 3: Required Technologies
  // ========================================
  if (techCard) {
    if (
      data.required_technologies &&
      typeof data.required_technologies === 'object' &&
      Object.keys(data.required_technologies).length > 0
    ) {
      const textEl = techCard.querySelector('.card-content');
      if (textEl) {
        let techHtml = '';
        for (const [category, techs] of Object.entries(
          data.required_technologies
        )) {
          if (category && techs) {
            techHtml += `<div class="mb-3"><strong>${category}:</strong>`;
            techHtml += '<ul class="list-disc list-inside mt-1">';
            if (Array.isArray(techs)) {
              techs.forEach((tech) => {
                if (tech) techHtml += `<li>${tech}</li>`;
              });
            } else {
              techHtml += `<li>${techs}</li>`;
            }
            techHtml += '</ul></div>';
          }
        }
        if (techHtml) textEl.innerHTML = techHtml;
      }
      techCard.classList.remove('hidden');
    } else {
      techCard.classList.add('hidden');
    }
  }

  // ========================================
  // CARD 4: Non-Technical Requirements
  // ========================================
  if (nonTechReqCard) {
    if (
      data.non_technical_requirements &&
      Array.isArray(data.non_technical_requirements) &&
      data.non_technical_requirements.length > 0
    ) {
      const textEl = nonTechReqCard.querySelector('.card-content');
      if (textEl) {
        const filteredReqs = data.non_technical_requirements.filter(
          (req) => req && req.trim()
        );
        if (filteredReqs.length > 0) {
          textEl.innerHTML = filteredReqs
            .map((req) => `<li class="list-item">${req}</li>`)
            .join('');
        }
      }
      nonTechReqCard.classList.remove('hidden');
      console.log(
        '[DEBUG] Populated non-tech-req card with',
        data.non_technical_requirements.length,
        'items'
      );
    } else {
      nonTechReqCard.classList.add('hidden');
    }
  }

  // ========================================
  // CARD 5: Clarifying Questions
  // ========================================
  if (unclearCard) {
    if (
      data.clarifying_questions &&
      Array.isArray(data.clarifying_questions) &&
      data.clarifying_questions.length > 0
    ) {
      const textEl = unclearCard.querySelector('.card-content');
      if (textEl) {
        const filteredQuestions = data.clarifying_questions.filter(
          (q) => q && q.trim()
        );
        if (filteredQuestions.length > 0) {
          textEl.innerHTML = filteredQuestions
            .map((q) => `<li class="list-item">${q}</li>`)
            .join('');
        }
      }
      unclearCard.classList.remove('hidden');
      console.log(
        '[DEBUG] Populated unclear-points card with',
        data.clarifying_questions.length,
        'questions'
      );
    } else {
      unclearCard.classList.add('hidden');
    }
  }

  // ========================================
  // CARD 6: Tool Recommendations (Technical)
  // ========================================

  if (techQuestionsCard) {
    let toolsHtml = '';

    if (
      data.technical_questions &&
      typeof data.technical_questions === 'object' &&
      Object.keys(data.technical_questions).length > 0
    ) {
      for (const [tool, reasoning] of Object.entries(
        data.technical_questions
      )) {
        if (tool && reasoning) {
          if (Array.isArray(reasoning)) {
            reasoning.forEach((r) => {
              if (r)
                toolsHtml += `<li class="list-item">${r}</li>`;
            });
          } else {
            toolsHtml += `<li class="list-item">${reasoning}</li>`;
          }
        }
      }
    }

    if (toolsHtml) {
      const textEl = techQuestionsCard.querySelector('.card-content');
      if (textEl) {
        textEl.innerHTML = toolsHtml;
      }
      techQuestionsCard.classList.remove('hidden');
      console.log(
        '[DEBUG] Populated tech-questions card with tool recommendations'
      );
    } else {
      techQuestionsCard.classList.add('hidden');
    }
  }

  // ========================================
  // CARD 7: Reference Sites / URLs
  // ========================================
  if (nonTechQuestionsCard) {
    if (
      data.non_technical_questions &&
      Array.isArray(data.non_technical_questions) &&
      data.non_technical_questions.length > 0
    ) {
      const textEl = nonTechQuestionsCard.querySelector('.card-content');
      if (textEl) {
        const filteredSites = data.non_technical_questions.filter(
          (site) => site && site.trim()
        );
        if (filteredSites.length > 0) {
          textEl.innerHTML = filteredSites
            .map((site) => `<li class="list-item">${site}</li>`)
            .join('');
        }
      }
      nonTechQuestionsCard.classList.remove('hidden');
      console.log(
        '[DEBUG] Populated non-tech-questions card with',
        data.non_technical_questions.length,
        'reference sites'
      );
    } else {
      nonTechQuestionsCard.classList.add('hidden');
    }
  }

  // ========================================
  // CARD 8: Important Point / Greeting
  // ========================================
  if (importantPointCard) {
    if (data?.important_point && data?.important_point.trim()) {
      const textEl = importantPointCard.querySelector('.card-content');
      if (textEl) textEl.textContent = data.important_point;
      importantPointCard.classList.remove('hidden');
      console.log(
        '[DEBUG] Populated important-point card with:',
        data.important_point.substring(0, 50)
      );
    } else {
      importantPointCard.classList.add('hidden');
    }
  }

  if (Recommendations) {
    const recs = data.recommendations;

    // Must be a non-null object with at least one key
    if (recs && typeof recs === 'object' && Object.keys(recs).length > 0) {
      const textEl = Recommendations.querySelector('.card-content');

      if (textEl) {
        const sections = Object.entries(recs)
          .map(([category, items]) => {
            if (!Array.isArray(items)) return '';

            const cleaned = items.filter((item) => item && item.trim());
            if (cleaned.length === 0) return '';

            return `
              <div class="mb-3">
                <div class="font-semibold mb-1">${category}</div>
                <ul class="list-disc list-inside">
                  ${cleaned
                    .map((item) => `<li class="list-item">${item}</li>`)
                    .join('')}
                </ul>
              </div>
            `;
          })
          .filter(Boolean) // remove empty strings
          .join('');

        if (sections.trim()) {
          textEl.innerHTML = sections;
          Recommendations.classList.remove('hidden');
          console.log(
            '[DEBUG] Populated recommendations card with categories:',
            Object.keys(recs)
          );
        } else {
          Recommendations.classList.add('hidden');
        }
      }
    } else {
      Recommendations.classList.add('hidden');
    }
  }

  if (refrenceWeb) {
    if (
      data.reference_websites &&
      Array.isArray(data.reference_websites) &&
      data.reference_websites.length > 0
    ) {
      const textEl = refrenceWeb.querySelector('.card-content');
      if (textEl) {
        const filteredSites = data.reference_websites.filter(
          (site) => site && site.trim()
        );
        if (filteredSites.length > 0) {
          textEl.innerHTML = filteredSites
            .map((site) => `<li class="list-item">${site}</li>`)
            .join('');
        }
      }
      refrenceWeb.classList.remove('hidden');
      console.log(
        '[DEBUG] Populated non-tech-questions card with',
        data.reference_websites.length,
        'reference sites'
      );
    } else {
      refrenceWeb.classList.add('hidden');
    }
  }

  console.log('[DEBUG] Breakdown card population complete');
}

// Helper function to extract text content from an element (handles nested lists)
function extractTextFromElement(element) {
  const clone = element.cloneNode(true);
  const listItems = clone.querySelectorAll('.list-item');

  if (listItems.length > 0) {
    // If there are list items, extract their text
    return Array.from(listItems)
      .map((li) => li.textContent.trim())
      .join('\n');
  }

  return clone.textContent.trim();
}

// Function to handle copy button clicks
function initializeCopyButtons() {
  // Handle all copy buttons for breakdown cards and cover letter
  document
    .querySelectorAll('[data-section] button, #coverLetterContentEl button')
    .forEach((btn) => {
      if (
        btn.querySelector('.material-symbols-outlined')?.textContent ===
        'content_copy'
      ) {
        btn.addEventListener('click', handleCopyClick);
      }
    });

  // Handle JSON copy button
  const jsonCopyBtn = document.getElementById('jsonCopyBtn');
  if (jsonCopyBtn) {
    jsonCopyBtn.addEventListener('click', handleCopyClick);
  }

  // Handle cover letter copy button
  const coverLetterCopyBtn = document
    .querySelector('#coverLetterContentEl')
    ?.parentElement?.querySelector('button');
  if (
    coverLetterCopyBtn &&
    coverLetterCopyBtn.querySelector('.material-symbols-outlined')
      ?.textContent === 'content_copy'
  ) {
    coverLetterCopyBtn.addEventListener('click', handleCopyClick);
  }
}

// Copy handler function
async function handleCopyClick(e) {
  e.preventDefault();
  const btn = this;

  let textToCopy = '';

  // Check if it's the JSON button
  if (btn.id === 'jsonCopyBtn') {
    const jsonEl = document.getElementById('structuredJson');
    textToCopy = jsonEl?.textContent || '';
  }
  // Check if it's in a breakdown card
  else {
    const card = btn.closest('[data-section]');
    if (card) {
      const contentEl = card.querySelector('.card-content');
      if (contentEl) {
        textToCopy = extractTextFromElement(contentEl);
      }
    }
  }

  if (!textToCopy || textToCopy === '{}') {
    return;
  }

  try {
    await navigator.clipboard.writeText(textToCopy);

    // Show feedback
    const originalHTML = btn.innerHTML;
    const originalClass = btn.className;

    btn.innerHTML =
      '<span class="material-symbols-outlined text-sm">check</span><span>Copied!</span>';
    btn.className =
      'flex items-center justify-center gap-1.5 rounded-md h-8 px-2.5 bg-green-200 dark:bg-green-500/30 text-green-700 dark:text-green-300 text-xs font-medium transition-colors';

    setTimeout(() => {
      btn.innerHTML = originalHTML;
      btn.className = originalClass;
    }, 2000);
  } catch (err) {
    console.error('Failed to copy:', err);
  }
}

// -----------------------------------------------------
// STREAMING (SSE-LIKE) FETCH HANDLER
// Buffer and display after completion
// -----------------------------------------------------
async function startStreaming(payload) {
  resetUI();
  loaderSeconds = 0;
  document.getElementById('loaderTime').textContent = `0s`;

  loaderInterval = setInterval(() => {
    loaderSeconds++;
    console.log(loaderSeconds);
    document.getElementById('loaderTime').textContent = `${loaderSeconds}s`;
  }, 1000);

  let reader;
  try {
    const res = await fetch(STREAM_URL, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });

    if (!res.ok) {
      errors.innerHTML = res;
      errors.classList.remove('hidden');
      hideProgress();
      return;
    }

    reader = res.body.getReader();
  } catch (error) {
    errors.innerHTML = error;
    errors.classList.remove('hidden');
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
    while ((idx = buf.indexOf('\n')) !== -1) {
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
      if (
        obj.type === 'token' ||
        obj.type === 'partial' ||
        obj.type === 'partial_gen'
      ) {
        // Buffer tokens - don't display yet
        bufferedCoverLetter += obj.content || obj.token || '';
      } else if (obj.type === 'progress') {
        // Update progress bar
        const pct = Number(obj.percent) || 0;
        const msg = obj.message || 'Processing...';
        setProgress(pct, msg);
      } else if (obj.type === 'cover_letter_done') {
        generateBtn.disabled = false;
        // Backend explicitly sends the final cover letter
        renderCoverLetter(obj.content);
      } else if (obj.type === 'structured_data') {
        console.log('obj.data ##############', obj.data);

        setTimeout(() => {
          populateBreakdownCards(obj.data);
        }, 500);
      } else if (obj.type === 'done' || obj.type === 'finished') {
        // Final completion event - now display everything
        generateBtn.disabled = false;
        setProgress(100, 'Completed!');

        setTimeout(() => {
          document.getElementById('progressOverlay').classList.add('hidden');
          document.body.classList.remove('overflow-hidden');
          clearInterval(loaderInterval);
          initializeCopyButtons();
          showOutput();
        }, 500);
      } else if (obj.type === 'error') {
        generateBtn.disabled = false;
        // alert('Server error: ' + (obj.message || 'Unknown'));
        errors.innerHTML = obj.message;
        errors.classList.remove('hidden');
        hideProgress();
        document.getElementById('progressOverlay').classList.add('hidden');
        return;
      } else if (obj.type === 'usage') {
        // Update token usage UI (if provided by backend)
        try {
          const usage = obj.usage || obj;
          const inTokens =
            usage.input_tokens ?? usage.input ?? usage.inputTokens ?? 0;
          const outTokens =
            usage.output_tokens ?? usage.output ?? usage.outputTokens ?? 0;
          const totalTokens =
            usage.total_tokens ??
            usage.total ??
            usage.totalTokens ??
            Number(inTokens) + Number(outTokens);

          const tokenInputEl = document.getElementById('token-input');
          const tokenOutputEl = document.getElementById('token-output');
          const tokenTotalEl = document.getElementById('token-total');
          const tokenCard = document.getElementById('tokenUsageCard');

          if (tokenInputEl) tokenInputEl.textContent = String(inTokens);
          if (tokenOutputEl) tokenOutputEl.textContent = String(outTokens);
          if (tokenTotalEl) tokenTotalEl.textContent = String(totalTokens);

          if (tokenCard) tokenCard.classList.remove('hidden');
        } catch (e) {
          console.error('Failed to update token usage:', e);
        }
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
    selected_categories: selectedCategories,
    // files: selectedFile,
    session_id: sessionId,
    base64_string: fileBase64,
    filename: filename
  };

  setProgress(1, 'Sending to server...');

  startStreaming(payload).catch((err) => {
    console.error('streaming error', err);
    hideProgress();
  });
});

// Optional: Ctrl+Enter to trigger generation
// clientText.addEventListener('keydown', (e) => {
//   if (e.ctrlKey && e.key === 'Enter') {
//     generateBtn.click();
//   }
// });

// -----------------------------------------------------
// SECTION VISIBILITY/NAVIGATION
// -----------------------------------------------------
function showOutput() {
  document.body.classList.remove('overflow-hidden');
  const inputSection = document.getElementById('inputSection');
  const outputSection = document.getElementById('outputSection');

  inputSection.classList.add('hidden');
  outputSection.classList.remove('hidden');

  requestAnimationFrame(() => {
    outputSection.classList.add('show');
  });

  // Smooth scroll to the very top
  window.scrollTo({
    top: 0,
    behavior: 'smooth'
  });
}

function showInput() {
  generateBtn.disabled = false;
  clientText.value = '';
  urlList.innerHTML = '';
  document.querySelectorAll('.category-checkbox').forEach((checkbox) => {
    checkbox.checked = false;
  });
  selectedCategories = [];
  selectedFile = null;

  const inputSection = document.getElementById('inputSection');
  const outputSection = document.getElementById('outputSection');
  generateBtn.classList.remove('hidden');

  outputSection.classList.remove('show');

  setTimeout(() => {
    outputSection.classList.add('hidden');
    inputSection.classList.remove('hidden');

    requestAnimationFrame(() => {
      inputSection.classList.add('show');
    });
  }, 200);

  window.scrollTo({
    top: 0,
    behavior: 'smooth'
  });
}

// Make functions globally available
window.showInput = showInput;
window.showOutput = showOutput;

// Copy behavior using Clipboard API, with fallback
async function copyToClipboard(text) {
  if (!text) return false;
  if (navigator.clipboard && navigator.clipboard.writeText) {
    await navigator.clipboard.writeText(text);
    return true;
  } else {
    // fallback
    const ta = document.createElement('textarea');
    ta.value = text;
    document.body.appendChild(ta);
    ta.select();
    try {
      document.execCommand('copy');
      document.body.removeChild(ta);
      return true;
    } catch (e) {
      document.body.removeChild(ta);
      return false;
    }
  }
}

// Show temporary feedback
function showCopyFeedback() {
  copyFeedback.classList.add('show');
  setTimeout(() => copyFeedback.classList.remove('show'), 1400);
}

// Wire copy button to copy the currently displayed proposal
let lastRenderedText = '';
copyBtn.addEventListener('click', async () => {
  if (!lastRenderedText) {
    // attempt to read current DOM and assemble text if needed
    lastRenderedText = Array.from(coverLetterContentEl.querySelectorAll('p'))
      .map((p) => p.textContent)
      .join('\n\n');
  }
  const ok = await copyToClipboard(lastRenderedText);
  if (ok) showCopyFeedback();
  else alert('Copy failed — please select the text and copy manually.');
});

regenerateBtn.addEventListener('click', async () => {
  const text =
    'regenerate a completely new cover letter. Use the same job description, same extracted fields, but produce a fresh, more accurate version. Do NOT repeat any previous wording. Give a new, unique human proposal + structured JSON output. Also, DO not add wording like you give me perfect version just only add cover letter content';

  // let generation_mode = document.querySelector('input[name="generation-mode"]:checked').value;

  const payload = {
    // generation_mode,
    client_text: text,
    session_id: sessionId
  };

  document.getElementById('progressOverlay').classList.remove('hidden');

  startStreaming(payload).catch((err) => {
    console.error('streaming error', err);
    document.getElementById('progressOverlay').classList.add('hidden');
  });
});

/**
 * Helper Function: Determine file type and extract text
 */
async function getFileContentSnippet(file) {
  console.log('Processing file:', file);
  try {
    if (file.type === 'application/pdf') {
      return await extractPdfText(file);
    } else if (
      file.type.startsWith('text/') ||
      file.name.match(/\.(md|json|js|py|txt|csv)$/i)
    ) {
      return await readTextFile(file);
    } else {
      return `[Binary file: ${file.type} - content cannot be read by frontend]`;
    }
  } catch (error) {
    console.error('Error processing file:', file.name, error);
    return 'Error extracting content.';
  }
}

/**
 * Helper: Read standard text files
 */
function readTextFile(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    // Read file as text
    reader.onload = (e) => {
      const text = e.target.result;
      // Limit to 1500 chars to avoid blowing up the token limit
      resolve(text.slice(0, 1500) + (text.length > 1500 ? '...' : ''));
    };
    reader.onerror = (e) => reject(e);
    reader.readAsText(file);
  });
}

/**
 * Helper: Extract text from PDF using pdfjs-dist
 */
async function extractPdfText(file) {
  if (typeof pdfjsLib === 'undefined') {
    console.warn('pdfjs-dist not found. Cannot extract PDF text.');
    return 'PDF content (parser not loaded).';
  }

  const arrayBuffer = await file.arrayBuffer();
  const pdf = await pdfjsLib.getDocument({ data: arrayBuffer }).promise;

  let fullText = '';
  // Only read the first 3 pages to keep it fast and light
  const maxPages = Math.min(pdf.numPages, 3);

  for (let i = 1; i <= maxPages; i++) {
    const page = await pdf.getPage(i);
    const textContent = await page.getTextContent();
    const pageText = textContent.items.map((item) => item.str).join(' ');
    fullText += `[Page ${i}] ${pageText}\n`;
  }

  return fullText.slice(0, 1500) + ' ...';
}
