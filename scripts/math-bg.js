(function() {
  var canvas = document.getElementById('math-canvas');
  if (!canvas) return;
  var ctx = canvas.getContext('2d');
  var symbols = ['+','÷','×','π','=','%','∑','−','∞','√','△','⊙','∫','≈','≠','∠','⊕','λ'];
  var colors = ['#6366f1','#10b981','#f43f5e','#8b5cf6','#f59e0b','#06b6d4','#ec4899','#14b8a6','#f97316','#84cc16','#a855f7','#2563eb'];
  var particles = [];
  var COUNT = 28;

  function resize() {
    canvas.width = window.innerWidth;
    canvas.height = window.innerHeight;
  }

  function init() {
    resize();
    particles = [];
    for (var i = 0; i < COUNT; i++) {
      particles.push({
        x: Math.random() * canvas.width,
        y: Math.random() * canvas.height * 2,
        speed: 0.2 + Math.random() * 0.5,
        drift: (Math.random() - 0.5) * 0.3,
        rotation: Math.random() * 360,
        rotSpeed: (Math.random() - 0.5) * 0.6,
        size: 26 + Math.random() * 22,
        symbol: symbols[i % symbols.length],
        color: colors[i % colors.length],
        opacity: 0.25 + Math.random() * 0.15
      });
    }
  }

  function draw() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    for (var i = 0; i < particles.length; i++) {
      var p = particles[i];
      p.y -= p.speed;
      p.x += p.drift;
      p.rotation += p.rotSpeed;

      if (p.y < -50) {
        p.y = canvas.height + 30;
        p.x = Math.random() * canvas.width;
      }

      ctx.save();
      ctx.translate(p.x, p.y);
      ctx.rotate(p.rotation * Math.PI / 180);
      ctx.globalAlpha = p.opacity;
      ctx.font = 'bold ' + p.size + 'px Nunito, sans-serif';
      ctx.fillStyle = p.color;
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillText(p.symbol, 0, 0);
      ctx.restore();
    }
    requestAnimationFrame(draw);
  }

  window.addEventListener('resize', resize);
  if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
  init();
  draw();
})();
