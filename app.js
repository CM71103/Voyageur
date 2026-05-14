/* ── Voyageur app.js ── */
'use strict';

// ── State ──────────────────────────────────────────
let currentItinerary = null;
let chatHistory = [];
let testiIndex = 0;

// ── Navbar scroll effect ────────────────────────────
window.addEventListener('scroll', () => {
  document.getElementById('navbar').classList.toggle('scrolled', window.scrollY > 60);
});

// ── Hamburger menu ──────────────────────────────────
document.getElementById('hamburger').addEventListener('click', () => {
  document.getElementById('navLinks').classList.toggle('open');
});
document.querySelectorAll('.nav-link').forEach(l =>
  l.addEventListener('click', () => document.getElementById('navLinks').classList.remove('open'))
);

// ── Textarea char counter ───────────────────────────
document.getElementById('tripDescription').addEventListener('input', function () {
  const len = this.value.length;
  document.getElementById('charCount').textContent = `${len} / 500`;
  if (len > 500) this.value = this.value.slice(0, 500);
});

// ── Modal helpers ───────────────────────────────────
function openModal() {
  document.getElementById('modalBackdrop').classList.add('open');
  document.body.style.overflow = 'hidden';
  showPhase('phaseInput');
  loadMemoryGreeting();
}

function openModalWithDest(dest) {
  openModal();
  document.getElementById('tripDescription').value = `I want a trip to ${dest}`;
  document.getElementById('charCount').textContent = `${document.getElementById('tripDescription').value.length} / 500`;
}

function closeModal(e) {
  if (e && e.target !== document.getElementById('modalBackdrop')) return;
  document.getElementById('modalBackdrop').classList.remove('open');
  document.body.style.overflow = '';
}

document.addEventListener('keydown', e => {
  if (e.key === 'Escape') {
    document.getElementById('modalBackdrop').classList.remove('open');
    document.body.style.overflow = '';
  }
});

function showPhase(id) {
  ['phaseInput','phaseLoading','phaseResults','phaseBooked'].forEach(p => {
    document.getElementById(p).style.display = p === id ? 'block' : 'none';
  });
}

// ── Load memory greeting ────────────────────────────
async function loadMemoryGreeting() {
  try {
    const res = await fetch('/api/memories');
    const data = await res.json();
    const el = document.getElementById('memoryGreeting');
    if (data.memories && data.memories.length > 0) {
      el.textContent = `👋 Welcome back! I remember your past trips. Your preferences have been loaded.`;
      el.style.display = 'block';
    } else {
      el.style.display = 'none';
    }
  } catch {
    document.getElementById('memoryGreeting').style.display = 'none';
  }
}

// ── Start trip ──────────────────────────────────────
async function startTrip() {
  const desc = document.getElementById('tripDescription').value.trim();
  if (!desc) {
    alert('Please describe your trip first!');
    return;
  }

  showPhase('phaseLoading');
  animateLoadingSteps();

  try {
    const res = await fetch('/api/start', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ description: desc })
    });

    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'Server error');
    }

    const data = await res.json();
    currentItinerary = data.itinerary;
    chatHistory = [];

    renderBrief(data.brief);
    renderItinerary(data.itinerary);
    renderTotalCost(data.itinerary.total_estimated_cost);

    // Add initial bot message
    document.getElementById('chatMessages').innerHTML = '';
    addChatMessage('bot', `✈️ Your itinerary is ready! Feel free to ask me to adjust anything — pace, budget, activities, or anything else.`);

    showPhase('phaseResults');
  } catch (err) {
    showPhase('phaseInput');
    alert(`Sorry, something went wrong: ${err.message}`);
  }
}

// ── Animate loading steps ───────────────────────────
function animateLoadingSteps() {
  const steps = ['step1','step2','step3','step4'];
  const labels = [
    '✓ Understanding your preferences',
    '✓ Building trip brief',
    '✓ Generating day-by-day plan',
    '✓ Estimating costs'
  ];
  steps.forEach((id, i) => {
    const el = document.getElementById(id);
    el.className = 'load-step';
    el.textContent = el.textContent.replace('✓','⟳');
  });
  document.getElementById('step1').className = 'load-step active';

  let i = 0;
  const interval = setInterval(() => {
    if (i < steps.length) {
      if (i > 0) {
        document.getElementById(steps[i-1]).className = 'load-step done';
        document.getElementById(steps[i-1]).textContent = labels[i-1];
      }
      document.getElementById(steps[i]).className = 'load-step active';
      i++;
    } else {
      clearInterval(interval);
    }
  }, 1800);
}

// ── Render brief card ───────────────────────────────
function renderBrief(brief) {
  const el = document.getElementById('briefCard');
  const interests = Array.isArray(brief.interests) ? brief.interests.join(', ') : brief.interests;
  const dietary = Array.isArray(brief.dietary_needs) && brief.dietary_needs.length
    ? brief.dietary_needs.join(', ') : 'None';
  el.innerHTML = `
    <h3>✈ Trip Brief</h3>
    <div class="brief-grid">
      <div class="brief-item"><label>Destination</label><span>${brief.destination}</span></div>
      <div class="brief-item"><label>Duration</label><span>${brief.duration_days} day(s)</span></div>
      <div class="brief-item"><label>Travelers</label><span>${brief.num_travelers} person(s)</span></div>
      <div class="brief-item"><label>Budget</label><span style="text-transform:capitalize">${brief.budget_tier}</span></div>
      <div class="brief-item"><label>Pace</label><span style="text-transform:capitalize">${brief.pace}</span></div>
      <div class="brief-item"><label>Interests</label><span>${interests}</span></div>
      ${dietary !== 'None' ? `<div class="brief-item"><label>Dietary</label><span>${dietary}</span></div>` : ''}
      ${brief.notes ? `<div class="brief-item" style="grid-column:1/-1"><label>Notes</label><span>${brief.notes}</span></div>` : ''}
    </div>`;
}

// ── Render itinerary ────────────────────────────────
function renderItinerary(itinerary) {
  const wrap = document.getElementById('itineraryWrap');
  wrap.innerHTML = '';
  itinerary.days.forEach(day => {
    const block = document.createElement('div');
    block.className = 'day-block';
    block.innerHTML = `
      <div class="day-header" onclick="toggleDay(this)">
        <span>Day ${day.day_number}</span>
        <span class="chevron">▼</span>
      </div>
      <div class="day-content ${day.day_number === 1 ? 'open' : ''}">
        ${renderActivity('🌅 Morning', day.morning)}
        ${renderActivity('☀ Afternoon', day.afternoon)}
        ${renderActivity('🌙 Evening', day.evening)}
      </div>`;
    wrap.appendChild(block);
  });
}

function renderActivity(label, act) {
  const cost = act.estimated_cost_inr ? `₹${Number(act.estimated_cost_inr).toLocaleString('en-IN')}` : 'Free';
  return `
    <div class="activity-row">
      <div class="act-time">${label}</div>
      <div>
        <div class="act-name">${act.activity}</div>
        <div class="act-sub">📍 ${act.location}${act.notes ? ' · ' + act.notes : ''}</div>
      </div>
      <div class="act-dur">${act.duration_minutes} min</div>
      <div class="act-cost">${cost}</div>
    </div>`;
}

function toggleDay(header) {
  const content = header.nextElementSibling;
  const chevron = header.querySelector('.chevron');
  const isOpen = content.classList.contains('open');
  content.classList.toggle('open', !isOpen);
  chevron.style.transform = isOpen ? 'rotate(0deg)' : 'rotate(180deg)';
}

function renderTotalCost(total) {
  const el = document.getElementById('totalCost');
  el.innerHTML = total
    ? `<span>Total Estimated Cost</span><strong>₹${Number(total).toLocaleString('en-IN')}</strong>`
    : `<span>Total Estimated Cost</span><strong>Not calculated</strong>`;
}

// ── Chat refinement ─────────────────────────────────
function addChatMessage(role, text) {
  const el = document.getElementById('chatMessages');
  const msg = document.createElement('div');
  msg.className = `chat-msg ${role}`;
  msg.textContent = text;
  el.appendChild(msg);
  el.scrollTop = el.scrollHeight;
}

async function sendChat() {
  const input = document.getElementById('chatInput');
  const msg = input.value.trim();
  if (!msg || !currentItinerary) return;
  input.value = '';

  addChatMessage('user', msg);
  chatHistory.push({ role: 'user', content: msg });

  const sendBtn = document.getElementById('sendBtn');
  sendBtn.disabled = true;
  sendBtn.textContent = '...';

  try {
    const res = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: msg, current_itinerary: currentItinerary })
    });

    if (!res.ok) throw new Error('Server error');

    const data = await res.json();
    if (data.type === 'itinerary' && data.itinerary) {
      currentItinerary = data.itinerary;
      renderBrief(data.itinerary.brief);
      renderItinerary(data.itinerary);
      renderTotalCost(data.itinerary.total_estimated_cost);
      addChatMessage('bot', '✅ I\'ve updated your itinerary! Scroll up to review the changes.');
      chatHistory.push({ role: 'assistant', content: 'Updated itinerary.' });
    } else {
      addChatMessage('bot', data.content || 'Here\'s what I found!');
      chatHistory.push({ role: 'assistant', content: data.content });
    }
  } catch (err) {
    addChatMessage('bot', `Sorry, I ran into an issue: ${err.message}`);
  } finally {
    sendBtn.disabled = false;
    sendBtn.textContent = 'Send';
  }
}

document.getElementById('chatInput').addEventListener('keydown', e => {
  if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendChat(); }
});

// ── Book / Save trip ────────────────────────────────
async function bookTrip() {
  try {
    await fetch('/api/save-memories', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ history: chatHistory })
    });
  } catch { /* non-critical */ }

  const ref = `VOY-${new Date().getFullYear()}-${String(Math.floor(Math.random() * 9000) + 1000)}`;
  const dest = currentItinerary?.brief?.destination || 'Your destination';
  const days = currentItinerary?.brief?.duration_days || '?';
  const cost = currentItinerary?.total_estimated_cost
    ? `₹${Number(currentItinerary.total_estimated_cost).toLocaleString('en-IN')}` : 'TBD';

  document.getElementById('bookingRef').innerHTML = `
    <div><strong>Booking Ref:</strong> ${ref}</div>
    <div><strong>Destination:</strong> ${dest} · ${days} Days</div>
    <div><strong>Total:</strong> ${cost}</div>`;

  showPhase('phaseBooked');
}

// ── Copy itinerary to clipboard ─────────────────────
function copyItinerary() {
  if (!currentItinerary) return;
  let text = `VOYAGEUR TRIP ITINERARY\n${'='.repeat(40)}\n`;
  text += `Destination: ${currentItinerary.brief.destination}\n`;
  text += `Duration: ${currentItinerary.brief.duration_days} days\n\n`;
  currentItinerary.days.forEach(day => {
    text += `DAY ${day.day_number}\n${'-'.repeat(20)}\n`;
    ['morning','afternoon','evening'].forEach(slot => {
      const a = day[slot];
      text += `  ${slot.toUpperCase()}: ${a.activity} @ ${a.location} (${a.duration_minutes} min)\n`;
    });
    text += '\n';
  });
  text += `Total Cost: ₹${Number(currentItinerary.total_estimated_cost).toLocaleString('en-IN')}`;
  navigator.clipboard.writeText(text).then(() => alert('Itinerary copied to clipboard! ✅'));
}

function printItinerary() {
  window.print();
}

function subscribeNewsletter() {
  const email = document.getElementById('newsletterEmail').value;
  if (!email || !email.includes('@')) { alert('Please enter a valid email.'); return; }
  alert(`🎉 Thanks! You'll receive exclusive travel deals at ${email}`);
  document.getElementById('newsletterEmail').value = '';
}

// ── Testimonials carousel ───────────────────────────
function goToTesti(index) {
  const cards = document.querySelectorAll('.testi-card');
  const dots = document.querySelectorAll('.dot');
  cards[testiIndex].classList.remove('active');
  dots[testiIndex].classList.remove('active');
  testiIndex = index;
  cards[testiIndex].classList.add('active');
  dots[testiIndex].classList.add('active');
}

setInterval(() => goToTesti((testiIndex + 1) % 3), 5000);

// ── Scroll reveal animation ─────────────────────────
const observer = new IntersectionObserver((entries) => {
  entries.forEach(entry => {
    if (entry.isIntersecting) {
      entry.target.style.opacity = '1';
      entry.target.style.transform = 'translateY(0)';
    }
  });
}, { threshold: 0.1 });

// Only animate elements below the fold
document.querySelectorAll('.tour-card, .cat-card, .blog-card, .stat-item, .offer-card').forEach(el => {
  const rect = el.getBoundingClientRect();
  if (rect.top > window.innerHeight) {
    el.style.opacity = '0';
    el.style.transform = 'translateY(24px)';
    el.style.transition = 'opacity .5s ease, transform .5s ease';
  }
  observer.observe(el);
});
