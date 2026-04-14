// ═══════════════════════════════════════════════
// MedLife — Main JavaScript
// ═══════════════════════════════════════════════

document.addEventListener('DOMContentLoaded', () => {

  // ── Navbar scroll effect ─────────────────────
  const publicNav = document.querySelector('.public-nav');
  if (publicNav) {
    window.addEventListener('scroll', () => {
      publicNav.classList.toggle('scrolled', window.scrollY > 30);
    });
  }

  // ── Scroll Reveal ────────────────────────────
  const revealEls = document.querySelectorAll('.reveal');
  const observer = new IntersectionObserver((entries) => {
    entries.forEach(el => {
      if (el.isIntersecting) {
        el.target.classList.add('visible');
        observer.unobserve(el.target);
      }
    });
  }, { threshold: 0.12 });
  revealEls.forEach(el => observer.observe(el));

  // ── Animated Counters ────────────────────────
  const counters = document.querySelectorAll('[data-count]');
  const countObserver = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        animateCounter(entry.target);
        countObserver.unobserve(entry.target);
      }
    });
  }, { threshold: 0.5 });
  counters.forEach(c => countObserver.observe(c));

  function animateCounter(el) {
    const target = parseInt(el.dataset.count, 10);
    const suffix = el.dataset.suffix || '';
    const duration = 2000;
    const start = performance.now();
    const update = (now) => {
      const elapsed = now - start;
      const progress = Math.min(elapsed / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3);
      el.textContent = Math.floor(eased * target).toLocaleString() + suffix;
      if (progress < 1) requestAnimationFrame(update);
    };
    requestAnimationFrame(update);
  }

  // ── FAQ Accordion ────────────────────────────
  document.querySelectorAll('.faq-question').forEach(q => {
    q.addEventListener('click', () => {
      const answer = q.nextElementSibling;
      const isOpen = q.classList.contains('open');
      // close all
      document.querySelectorAll('.faq-question.open').forEach(oq => {
        oq.classList.remove('open');
        oq.nextElementSibling.classList.remove('open');
      });
      if (!isOpen) {
        q.classList.add('open');
        answer.classList.add('open');
      }
    });
  });

  // ── Tabs ─────────────────────────────────────
  document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      const target = btn.dataset.tab;
      const parent = btn.closest('[data-tabs]') || btn.parentElement.parentElement;
      parent.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
      parent.querySelectorAll('.tab-pane').forEach(p => p.classList.remove('active'));
      btn.classList.add('active');
      const pane = parent.querySelector(`#${target}`);
      if (pane) pane.classList.add('active');
    });
  });

  // ── Network Canvas Background ─────────────────
  const canvas = document.getElementById('network-canvas');
  if (canvas) drawNetwork(canvas);

  function drawNetwork(canvas) {
    const ctx = canvas.getContext('2d');
    let nodes = [];
    const NODE_COUNT = 85;
    const MAX_DIST = 180;
    
    // Vibrant neon colors
    const neonColors = [
      'rgba(0,255,150,1)',      // Neon cyan-green
      'rgba(0,200,255,1)',      // Neon cyan
      'rgba(100,200,255,1)',    // Bright cyan
      'rgba(0,255,255,1)',      // Bright cyan
      'rgba(64,224,255,1)',     // Deep sky blue
    ];

    function resize() {
      canvas.width = canvas.offsetWidth;
      canvas.height = canvas.offsetHeight;
    }
    resize();
    window.addEventListener('resize', resize);

    for (let i = 0; i < NODE_COUNT; i++) {
      nodes.push({
        x: Math.random() * canvas.width,
        y: Math.random() * canvas.height,
        vx: (Math.random() - 0.5) * 0.8,
        vy: (Math.random() - 0.5) * 0.8,
        r: Math.random() * 3.5 + 1.5,
        colorIdx: Math.floor(Math.random() * neonColors.length),
      });
    }

    function draw() {
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      nodes.forEach(n => {
        n.x += n.vx; n.y += n.vy;
        if (n.x < 0 || n.x > canvas.width) n.vx *= -1;
        if (n.y < 0 || n.y > canvas.height) n.vy *= -1;
        ctx.beginPath();
        ctx.arc(n.x, n.y, n.r, 0, Math.PI * 2);
        ctx.fillStyle = neonColors[n.colorIdx];
        ctx.fill();
        // Add glow effect
        ctx.shadowColor = neonColors[n.colorIdx];
        ctx.shadowBlur = 15;
      });
      ctx.shadowColor = 'rgba(0,0,0,0)';
      ctx.shadowBlur = 0;
      
      for (let i = 0; i < nodes.length; i++) {
        for (let j = i + 1; j < nodes.length; j++) {
          const dx = nodes[i].x - nodes[j].x;
          const dy = nodes[i].y - nodes[j].y;
          const dist = Math.sqrt(dx * dx + dy * dy);
          if (dist < MAX_DIST) {
            ctx.beginPath();
            ctx.moveTo(nodes[i].x, nodes[i].y);
            ctx.lineTo(nodes[j].x, nodes[j].y);
            // Use the starting node's color for the line
            const color = neonColors[nodes[i].colorIdx];
            const opacity = 0.7 * (1 - dist / MAX_DIST);
            ctx.strokeStyle = color.replace('1)', opacity + ')');
            ctx.lineWidth = 1.5;
            ctx.stroke();
          }
        }
      }
      requestAnimationFrame(draw);
    }
    draw();
  }

  // ── Chart Bars (mockup) ──────────────────────
  document.querySelectorAll('.chart-bar').forEach(bar => {
    const h = Math.floor(Math.random() * 70 + 20);
    bar.style.height = h + '%';
  });

  // ── Progress Bars animate ────────────────────
  setTimeout(() => {
    document.querySelectorAll('.enc-progress-fill').forEach(bar => {
      const w = bar.dataset.width || '85';
      bar.style.width = w + '%';
    });
  }, 400);

  // ── Mobile sidebar toggle ────────────────────
  const sidebarToggle = document.getElementById('sidebar-toggle');
  const sidebar = document.querySelector('.sidebar');
  if (sidebarToggle && sidebar) {
    sidebarToggle.addEventListener('click', () => {
      sidebar.classList.toggle('open');
    });
  }

  // ── Notification bell ────────────────────────
  const notifBtn = document.getElementById('notif-btn');
  const notifDropdown = document.getElementById('notif-dropdown');
  if (notifBtn && notifDropdown) {
    notifBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      notifDropdown.classList.toggle('hidden');
    });
    document.addEventListener('click', () => notifDropdown.classList.add('hidden'));
  }

  // ── Chat input send ──────────────────────────
  const chatForm = document.getElementById('chat-form');
  if (chatForm) {
    chatForm.addEventListener('submit', (e) => {
      e.preventDefault();
      const input = chatForm.querySelector('input');
      const val = input.value.trim();
      if (!val) return;
      const chatWrap = document.getElementById('chat-messages');
      const bubble = document.createElement('div');
      bubble.className = 'chat-bubble out fade-up';
      bubble.innerHTML = `
        <div class="bubble-avatar">Y</div>
        <div class="bubble-content">
          <div class="bubble-text">${val}</div>
          <div class="bubble-meta">Just now &nbsp;·&nbsp; <span class="bubble-encrypted">🔒 AES-256 Encrypted</span></div>
        </div>`;
      chatWrap.appendChild(bubble);
      chatWrap.scrollTop = chatWrap.scrollHeight;
      input.value = '';
    });
  }

  // ── Modal ────────────────────────────────────
  document.querySelectorAll('[data-modal-open]').forEach(btn => {
    btn.addEventListener('click', () => {
      const id = btn.dataset.modalOpen;
      const modal = document.getElementById(id);
      if (modal) { modal.style.display = 'flex'; }
    });
  });
  document.querySelectorAll('[data-modal-close]').forEach(btn => {
    btn.addEventListener('click', () => {
      const modal = btn.closest('.modal-overlay');
      if (modal) modal.style.display = 'none';
    });
  });
  document.querySelectorAll('.modal-overlay').forEach(m => {
    m.addEventListener('click', (e) => {
      if (e.target === m) m.style.display = 'none';
    });
  });

  // ── Stagger animation delays ─────────────────
  document.querySelectorAll('.stagger > *').forEach((el, i) => {
    el.style.animationDelay = `${i * 0.1}s`;
    el.classList.add('fade-up');
  });

  // ── Toast notifications ──────────────────────
  window.showToast = function(msg, type = 'info') {
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.textContent = msg;
    document.body.appendChild(toast);
    setTimeout(() => toast.classList.add('show'), 10);
    setTimeout(() => { toast.classList.remove('show'); setTimeout(() => toast.remove(), 300); }, 3500);
  };

  // ── 2FA OTP input auto-advance ───────────────
  const otpInputs = document.querySelectorAll('.otp-input');
  otpInputs.forEach((inp, i) => {
    inp.addEventListener('input', () => {
      if (inp.value.length === 1 && otpInputs[i + 1]) otpInputs[i + 1].focus();
    });
    inp.addEventListener('keydown', (e) => {
      if (e.key === 'Backspace' && !inp.value && otpInputs[i - 1]) otpInputs[i - 1].focus();
    });
  });

});
