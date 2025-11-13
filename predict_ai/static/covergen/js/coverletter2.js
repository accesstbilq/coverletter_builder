// Frontend JavaScript to handle dual output from SSE stream

class CoverLetterClient {
  constructor(apiUrl) {
    this.apiUrl = apiUrl;
    this.structuredData = null;
    this.formattedResponse = "";
  }

  async generateCoverLetter(payload, callbacks) {
    const {
      onStructuredData,
      onToken,
      onProgress,
      onDone,
      onError
    } = callbacks;

    try {
      const response = await fetch(this.apiUrl, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload)
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        
        // Keep last incomplete line in buffer
        buffer = lines.pop() || '';

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const jsonStr = line.slice(6);
            
            try {
              const event = JSON.parse(jsonStr);
              
              switch (event.type) {
                case 'structured_data':
                  this.structuredData = event.data;
                  if (onStructuredData) {
                    onStructuredData(event.data);
                  }
                  break;
                
                case 'token':
                  this.formattedResponse += event.content;
                  if (onToken) {
                    onToken(event.content);
                  }
                  break;
                
                case 'progress':
                  if (onProgress) {
                    onProgress(event.percent, event.message);
                  }
                  break;
                
                case 'done':
                  if (onDone) {
                    onDone({
                      structuredData: this.structuredData,
                      formattedResponse: this.formattedResponse
                    });
                  }
                  break;
                
                case 'error':
                  if (onError) {
                    onError(event.message);
                  }
                  break;
              }
            } catch (parseError) {
              console.error('Failed to parse SSE event:', parseError);
            }
          }
        }
      }
    } catch (error) {
      if (onError) {
        onError(error.message);
      }
    }
  }

  reset() {
    this.structuredData = null;
    this.formattedResponse = "";
  }
}

// ============================================
// USAGE EXAMPLE
// ============================================

const client = new CoverLetterClient('/api/generate-cover-letter/');

// DOM elements
const structuredContainer = document.getElementById('structured-output');
const responseContainer = document.getElementById('formatted-response');
const progressBar = document.getElementById('progress-bar');
const progressText = document.getElementById('progress-text');

// Send request
client.generateCoverLetter(
  {
    session_id: 'user-session-123',
    client_text: document.getElementById('cover-letter-input').value,
    context_snippets: [],
    file_base64: null,
    file_name: null
  },
  {
    onStructuredData: (data) => {
      console.log('Structured data received:', data);
      
      // Display structured data in the UI
      renderStructuredData(data);
    },
    
    onToken: (content) => {
      // Append token to formatted response display
      responseContainer.textContent += content;
    },
    
    onProgress: (percent, message) => {
      progressBar.style.width = `${percent}%`;
      progressText.textContent = `${percent}% - ${message}`;
    },
    
    onDone: (result) => {
      console.log('Generation complete!');
      console.log('Full structured data:', result.structuredData);
      console.log('Full formatted response:', result.formattedResponse);
      
      // Enable action buttons, etc.
      enableUIActions();
    },
    
    onError: (message) => {
      console.error('Error:', message);
      alert(`Error: ${message}`);
    }
  }
);

// ============================================
// HELPER: RENDER STRUCTURED DATA
// ============================================

function renderStructuredData(data) {
  const html = `
    <div class="structured-data">
      <h3>Analysis Results</h3>
      
      <div class="section">
        <h4>Client Information</h4>
        <p><strong>Name:</strong> ${data.client_name || 'Not provided'}</p>
        <p><strong>Greeting:</strong> ${data.greeting}</p>
      </div>
      
      <div class="section">
        <h4>Project Details</h4>
        <p><strong>Category:</strong> ${data.project_category}</p>
        <p><strong>Main Objective:</strong> ${data.main_objective}</p>
        <p><strong>Scope:</strong> ${data.project_scope}</p>
      </div>
      
      ${data.reference_sites.length > 0 ? `
        <div class="section">
          <h4>Reference Sites</h4>
          <ul>
            ${data.reference_sites.map(site => `<li>${site}</li>`).join('')}
          </ul>
        </div>
      ` : ''}
      
      ${Object.keys(data.technologies_needed).length > 0 ? `
        <div class="section">
          <h4>Technologies Needed</h4>
          ${Object.entries(data.technologies_needed).map(([category, techs]) => `
            <p><strong>${category}:</strong> ${techs.join(', ')}</p>
          `).join('')}
        </div>
      ` : ''}
      
      ${Object.keys(data.tool_recommendations).length > 0 ? `
        <div class="section">
          <h4>Recommended Tools</h4>
          ${Object.entries(data.tool_recommendations).map(([category, tools]) => `
            <p><strong>${category}:</strong></p>
            <ul>
              ${tools.map(tool => `<li>${tool}</li>`).join('')}
            </ul>
          `).join('')}
        </div>
      ` : ''}
      
      ${data.non_tech_requirements.length > 0 ? `
        <div class="section">
          <h4>Requirements</h4>
          <ul>
            ${data.non_tech_requirements.map(req => `<li>${req}</li>`).join('')}
          </ul>
        </div>
      ` : ''}
      
      ${data.clarifying_questions.length > 0 ? `
        <div class="section">
          <h4>Clarifying Questions</h4>
          <ol>
            ${data.clarifying_questions.map(q => `<li>${q}</li>`).join('')}
          </ol>
        </div>
      ` : ''}
    </div>
  `;
  
  structuredContainer.innerHTML = html;
}

function enableUIActions() {
  // Enable buttons, show export options, etc.
  document.getElementById('export-json-btn').disabled = false;
  document.getElementById('copy-response-btn').disabled = false;
}