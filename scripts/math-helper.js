/* ───────────────────────────────────────────────
   Math Helper — Chat-like guided help widget
   No AI API required — uses pre-built hints,
   topic detection, and concept explanations.
   Never reveals the direct answer.
   ─────────────────────────────────────────────── */
(function () {
  'use strict';

  /* ── Topic detection from question text ── */
  function detectTopic(question) {
    var q = (question || '').toLowerCase();
    // Specific topics first — avoid vague words like 'left' or 'total' stealing the topic
    if (/\bmass\b|\bweight\b|kilogram|\bkg\b|gram|\bg\b|pound|\blb\b|ounce|\boz\b|heavier|lighter|weigh/.test(q)) return 'mass';
    if (/\bvolume\b|cubic|capacity|\bliter\b|\blitre\b|milliliter|millilitre|\bgallon\b|\bquart\b|\bpint\b|\bcup\b|fill|\bcube\b|cuboid|\bbox\b|\btank\b|\bcontainer\b|\bhold\b/.test(q)) return 'volume';
    if (/\bfraction\b|\/\d+|\bquarter\b|\bhalf\b|\bthird\b|\bfourth\b|\bfifth\b|piece|slice|\bpart\s+of\b|numerator|denominator/.test(q)) return 'fractions';
    if (/\bpercent\b|%|\bpercentage\b/.test(q)) return 'percentage';
    if (/\barea\b|\bperimeter\b|\blength\b|\bwidth\b|\bheight\b|\brectangle\b|\bsquare\b|\btriangle\b|\bcircle\b|radius|diameter|circumference|polygon|\bangle\b|\bshape\b/.test(q)) return 'geometry';
    if (/\bmoney\b|\bdollar\b|\bcent\b|loonie|toonie|\$|cost|price|change|pay|bought|sell|wallet|bank/.test(q)) return 'money';
    if (/\bequation\b|solve\s+for|variable|(?:\b|\d)[xyz]\s*[+=]\s*\d|unknown|\bexpression\b/.test(q)) return 'algebra';
    if (/÷|divide|division|share[ds]?\s+equally|splits?\b|split\b|split\s+.*\s+into\s+groups?\s+of|equally\s+among|quotient|each\s+(get|receive|friend|student|person|group)/.test(q)) return 'division';
    if (/\btimes\b|×|multiply|multiplication|rows?\s+of|groups?\s+of|\beach\b|per\s+\d+|product/.test(q)) return 'multiplication';
    if (/subtract|minus|difference|take\s+away|giv[ae]\s+away|give\s+away|spent|ate|used\s+up|how\s+many\s+more|how\s+much\s+more|decrease|\bleft\b|left\s+over|remain|remaining\s+after|away/.test(q)) return 'subtraction';
    if (/add|\+|\btotal\b|altogether|in\s+all|combined|\bsum\b|more\s+than|how\s+many\s+together|joined|increase|both|all\s+of\s+them/.test(q)) return 'addition';
    if (/\bpattern\b|sequence|what\s+comes\s+next|continue\s+the|\brule\b/.test(q)) return 'patterns';
    if (/\btime\b|\bhour\b|\bminute\b|clock|elapsed|\bam\b|\bpm\b|schedule|duration|start\s+at|finish\s+at/.test(q)) return 'time';
    if (/\bmean\b|\bmedian\b|\bmode\b|average|data|graph|chart|bar\s+graph|line\s+graph|pie\s+chart|probability|chance|likely|unlikely/.test(q)) return 'statistics';
    return 'general';
  }

  /* ── Concept library ── */
  var concepts = {
    addition: {
      name: 'Addition',
      explain: "Addition means combining groups together. Look for clue words like 'total', 'altogether', 'in all', or 'how many combined'.",
      strategy: "Try breaking numbers into tens and ones. For example, 23 + 15 → (20 + 10) + (3 + 5) = 30 + 8 = 38. This is called 'decomposing'!",
      tip: "Always line up the ones and tens columns. Start adding from the right side!"
    },
    subtraction: {
      name: 'Subtraction',
      explain: "Subtraction means finding the difference or taking away. Clue words: 'left', 'remaining', 'fewer', 'how many more', 'gave away'.",
      strategy: "Try counting up from the smaller number. For example, 52 − 38: start at 38, add 2 → 40, add 12 → 52. So the answer is 2 + 12 = 14!",
      tip: "You can also think of subtraction as 'what do I add to get from the small number to the big number?'"
    },
    multiplication: {
      name: 'Multiplication',
      explain: "Multiplication is repeated addition — it means equal groups! 'Times', 'groups of', 'rows of', and 'each' are clue words.",
      strategy: "Think of it as equal groups. For example, 3 × 6 means 3 groups of 6: 6 + 6 + 6 = 18. Try drawing the groups!",
      tip: "You can also use skip counting! For 4 × 5, count by 5s: 5, 10, 15, 20. Four jumps = 20!"
    },
    division: {
      name: 'Division',
      explain: "Division means splitting into equal groups or sharing equally. Clue words: 'each', 'equally', 'share', 'split among'.",
      strategy: "Think backwards from multiplication! If 12 ÷ 3 = ?, ask: 3 × ? = 12. Use your times tables in reverse!",
      tip: "You can also draw circles for the groups and deal out items one at a time, like dealing cards."
    },
    fractions: {
      name: 'Fractions',
      explain: "A fraction shows parts of a whole. The top number (numerator) = how many parts you have. The bottom (denominator) = total equal parts.",
      strategy: "Draw a shape and divide it into equal parts. For 3/4: divide into 4 equal parts, shade 3. This helps you visualize!",
      tip: "Think of fractions like pizza slices — how many slices total, and how many are you looking at?"
    },
    percentage: {
      name: 'Percentages',
      explain: "Percent means 'out of 100'. 50% = half, 25% = quarter, 10% = one-tenth.",
      strategy: "Start with easy percentages: 10% = divide by 10, 50% = divide by 2, 25% = divide by 4. Build from these!",
      tip: "For example, to find 30% of 80: find 10% first (80 ÷ 10 = 8), then multiply by 3 (8 × 3 = 24)."
    },
    volume: {
      name: 'Volume',
      explain: "Volume is the amount of space inside a 3D object. Think of it as how much a box, tank, or container can hold.",
      strategy: "For a box or cube, multiply length × width × height. For a cylinder, the formula is area of the circle × height. Make sure all measurements use the same units!",
      tip: "Volume units are often cubic (cm³, m³) or liquid (liters, milliliters). 1 liter = 1000 milliliters."
    },
    mass: {
      name: 'Mass and Weight',
      explain: "Mass tells us how much matter is in an object. Weight is how heavy it feels due to gravity. Grams (g) and kilograms (kg) are common units.",
      strategy: "Compare by looking at the units first. 1 kg = 1000 g. If one item is in kg and another in g, convert them to the same unit before comparing.",
      tip: "Lighter objects are usually measured in grams. Heavier objects are usually measured in kilograms."
    },
    geometry: {
      name: 'Geometry',
      explain: "Geometry is about shapes, sizes, and measurements. Perimeter = distance around. Area = space inside.",
      strategy: "For perimeter, add all sides. For area of a rectangle: length × width. Always draw and label the shape!",
      tip: "Remember: perimeter is like walking around the fence, area is like covering the floor with tiles."
    },
    patterns: {
      name: 'Patterns',
      explain: "Patterns repeat or follow a rule. Look at what changes between each number or shape.",
      strategy: "Write out the differences between consecutive numbers. Is it always the same? That's your rule! For example: 2, 5, 8, 11 → each goes up by 3.",
      tip: "Once you find the rule, apply it to the last number to find the next one."
    },
    time: {
      name: 'Time',
      explain: "Time problems involve hours, minutes, or elapsed time. Remember: 1 hour = 60 minutes.",
      strategy: "For elapsed time, count forward by hours first, then add the extra minutes. Use a number line if it helps!",
      tip: "Drawing a simple clock face can help you visualize the problem."
    },
    money: {
      name: 'Money',
      explain: "Money problems involve adding, subtracting, or making change with coins and bills. Remember: $1 = 100 cents.",
      strategy: "Start with the biggest coins/bills first, then add smaller ones. For making change, count up from the price to the amount paid.",
      tip: "Line up the decimal points when adding or subtracting money amounts!"
    },
    algebra: {
      name: 'Algebra',
      explain: "Algebra uses letters (variables) to represent unknown numbers. Your goal is to find what the letter equals.",
      strategy: "Do the same thing to both sides of the equation. To isolate x, use the opposite operation. If it says x + 5 = 12, subtract 5 from both sides.",
      tip: "Think of the equation like a balance scale — whatever you do to one side, do to the other!"
    },
    statistics: {
      name: 'Statistics',
      explain: "Statistics is about understanding data. Mean = average, Median = middle value, Mode = most common value.",
      strategy: "For the mean: add all numbers, then divide by how many there are. For median: put numbers in order, find the middle one.",
      tip: "Always arrange numbers from smallest to largest before finding the median!"
    },
    general: {
      name: 'Math',
      explain: "Read the problem carefully. What information do you have? What are you trying to find?",
      strategy: "Try drawing a picture or diagram. Sometimes seeing the problem makes it much clearer!",
      tip: "Break the problem into smaller parts. Solve each part one at a time."
    }
  };

  /* ── Chat state ── */
  var state = {
    open: false,
    question: '',
    hint: '',
    topic: 'general',
    step: 0,       // 0=greeting, 1=concept, 2=hint, 3=strategy, 4=tip, 5=done
    messages: []
  };

  /* ── Create the chat panel DOM ── */
  var panel, msgContainer, quickRepliesEl;

  function buildPanel() {
    if (panel) return;

    panel = document.createElement('div');
    panel.id = 'math-helper-panel';
    panel.style.cssText =
      'display:none;position:fixed;bottom:80px;right:16px;width:360px;max-width:calc(100vw - 32px);' +
      'max-height:70vh;background:#fff;border-radius:16px;box-shadow:0 8px 30px rgba(0,0,0,.18);' +
      'z-index:9999;font-family:inherit;overflow:hidden;flex-direction:column;border:2px solid #6366f1;';

    // Header
    var header = document.createElement('div');
    header.style.cssText =
      'background:linear-gradient(135deg,#6366f1,#8b5cf6);color:#fff;padding:12px 16px;' +
      'display:flex;align-items:center;justify-content:space-between;';
    header.innerHTML =
      '<div style="display:flex;align-items:center;gap:8px">' +
      '<span style="font-size:1.4rem"></span>' +
      '<div><strong style="font-size:.95rem">Math Helper</strong>' +
      '<div style="font-size:.7rem;opacity:.85">I help you learn, not just answer!</div></div></div>' +
      '<button id="math-helper-close" style="background:none;border:none;color:#fff;font-size:1.3rem;cursor:pointer;padding:4px">✕</button>';
    panel.appendChild(header);

    // Messages area
    msgContainer = document.createElement('div');
    msgContainer.id = 'math-helper-messages';
    msgContainer.style.cssText =
      'flex:1;overflow-y:auto;padding:12px 14px;display:flex;flex-direction:column;gap:8px;' +
      'min-height:180px;max-height:calc(70vh - 120px);background:#f8fafc;';
    panel.appendChild(msgContainer);

    // Quick replies area
    quickRepliesEl = document.createElement('div');
    quickRepliesEl.id = 'math-helper-replies';
    quickRepliesEl.style.cssText =
      'padding:10px 14px;border-top:1px solid #e2e8f0;display:flex;flex-wrap:wrap;gap:6px;background:#fff;';
    panel.appendChild(quickRepliesEl);

    document.body.appendChild(panel);

    // Close button
    document.getElementById('math-helper-close').addEventListener('click', closeHelper);
  }

  /* ── Message rendering ── */
  function addBotMessage(text) {
    var bubble = document.createElement('div');
    bubble.style.cssText =
      'background:#ede9fe;color:#1e1b4b;padding:10px 14px;border-radius:14px 14px 14px 4px;' +
      'max-width:88%;align-self:flex-start;font-size:.88rem;line-height:1.45;animation:mh-fadein .3s ease;';
    bubble.innerHTML = text;
    msgContainer.appendChild(bubble);
    msgContainer.scrollTop = msgContainer.scrollHeight;
  }

  function addUserMessage(text) {
    var bubble = document.createElement('div');
    bubble.style.cssText =
      'background:#6366f1;color:#fff;padding:10px 14px;border-radius:14px 14px 4px 14px;' +
      'max-width:88%;align-self:flex-end;font-size:.88rem;line-height:1.45;animation:mh-fadein .3s ease;';
    bubble.textContent = text;
    msgContainer.appendChild(bubble);
    msgContainer.scrollTop = msgContainer.scrollHeight;
  }

  function setQuickReplies(replies) {
    quickRepliesEl.innerHTML = '';
    replies.forEach(function (r) {
      var btn = document.createElement('button');
      btn.textContent = r.label;
      btn.style.cssText =
        'padding:7px 14px;border:2px solid #6366f1;border-radius:20px;background:#fff;color:#6366f1;' +
        'font-size:.82rem;font-weight:600;cursor:pointer;font-family:inherit;transition:all .15s;';
      btn.onmouseenter = function () { btn.style.background = '#6366f1'; btn.style.color = '#fff'; };
      btn.onmouseleave = function () { btn.style.background = '#fff'; btn.style.color = '#6366f1'; };
      btn.addEventListener('click', function () {
        addUserMessage(r.label);
        r.action();
      });
      quickRepliesEl.appendChild(btn);
    });
  }

  /* ── Chat flow ── */
  function showGreeting() {
    var c = concepts[state.topic] || concepts.general;
    addBotMessage(
      "Hi! I'm your <strong>Math Helper</strong><br><br>" +
      "I can see you're working on a <strong>" + c.name + "</strong> problem. " +
      "I won't give you the answer, but I'll help you figure it out yourself!"
    );
    setQuickReplies([
      { label: 'What concept is this?', action: showConcept },
      { label: 'Give me a hint', action: showHint },
      { label: 'Walk me through it', action: showWalkthrough }
    ]);
    state.step = 0;
  }

  function showConcept() {
    var c = concepts[state.topic] || concepts.general;
    addBotMessage("<strong>" + c.name + "</strong><br><br>" + c.explain);
    state.step = 1;
    setQuickReplies([
      { label: 'Give me a hint', action: showHint },
      { label: 'Thanks, I\'ll try!', action: showGoodbye }
    ]);
  }

  function showHint() {
    var hintText = state.hint;
    if (hintText) {
      addBotMessage("<strong>Here's a hint:</strong><br><br>" + hintText);
    } else {
      var c = concepts[state.topic] || concepts.general;
      addBotMessage("<strong>Here's a strategy:</strong><br><br>" + c.strategy);
    }
    state.step = 2;
    setQuickReplies([
      { label: 'Still stuck', action: showStrategy },
      { label: 'Got it, thanks!', action: showGoodbye }
    ]);
  }

  function showStrategy() {
    var c = concepts[state.topic] || concepts.general;
    if (state.step < 3) {
      addBotMessage("<strong>Try this approach:</strong><br><br>" + c.strategy);
      state.step = 3;
      setQuickReplies([
        { label: 'One more tip?', action: showTip },
        { label: 'I\'ll try now!', action: showGoodbye }
      ]);
    } else {
      showTip();
    }
  }

  function showWalkthrough() {
    var c = concepts[state.topic] || concepts.general;
    addBotMessage(
      "Let's break this down!<br><br>" +
      "<strong>Step 1:</strong> Read the problem carefully. What numbers do you see? What is the question asking?<br><br>" +
      "<strong>Step 2:</strong> " + c.explain + "<br><br>" +
      "<strong>Step 3:</strong> " + c.strategy
    );
    state.step = 3;
    setQuickReplies([
      { label: 'Any more tips?', action: showTip },
      { label: 'I\'ll try now!', action: showGoodbye }
    ]);
  }

  function showTip() {
    var c = concepts[state.topic] || concepts.general;
    addBotMessage("<strong>Pro tip:</strong><br><br>" + c.tip);
    state.step = 4;
    addBotMessage(
      "Remember — making mistakes is how your brain grows! " +
      "Give it your best try. You can review the full solution after you submit!"
    );
    state.step = 5;
    setQuickReplies([
      { label: 'I\'ll give it a try!', action: showGoodbye }
    ]);
  }

  function showGoodbye() {
    var encouragements = [
      "You've got this! Good luck!",
      "Believe in yourself — you're learning every time you try!",
      "Go for it! Every math problem you solve makes your brain stronger!",
      "Awesome! Remember, it's OK to make mistakes. That's how we learn!"
    ];
    addBotMessage(encouragements[Math.floor(Math.random() * encouragements.length)]);
    quickRepliesEl.innerHTML = '';
    setTimeout(closeHelper, 2000);
  }

  /* ── Open / Close ── */
  function closeHelper() {
    if (panel) {
      panel.style.display = 'none';
      state.open = false;
    }
  }

  window.openMathHelper = function (questionText, hintText) {
    buildPanel();
    // Reset state
    state.question = questionText || '';
    state.hint = hintText || '';
    state.topic = detectTopic(state.question);
    state.step = 0;
    state.messages = [];
    msgContainer.innerHTML = '';
    quickRepliesEl.innerHTML = '';

    panel.style.display = 'flex';
    state.open = true;
    showGreeting();
  };

  // Expose for testing and debugging
  window.__mh_detectTopic = detectTopic;
  window.__mh_concepts = concepts;

  /* ── Inject animation keyframes ── */
  var style = document.createElement('style');
  style.textContent =
    '@keyframes mh-fadein{from{opacity:0;transform:translateY(6px)}to{opacity:1;transform:translateY(0)}}' +
    '#math-helper-panel{display:flex!important;}' +
    '#math-helper-panel[style*="display: none"]{display:none!important;}' +
    '@media(max-width:480px){#math-helper-panel{bottom:0!important;right:0!important;width:100vw!important;' +
    'max-width:100vw!important;max-height:80vh!important;border-radius:16px 16px 0 0!important;}}';
  document.head.appendChild(style);
})();
