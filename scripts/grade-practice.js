(function (root) {
  function gradeNumber(value) {
    const match = String(value ?? '').match(/(1[0-2]|[1-9])/);
    return match ? Number(match[1]) : null;
  }

  function formatGrade(value) {
    const number = gradeNumber(value);
    return number ? `Grade ${number}` : '';
  }

  function gradesMatch(officialGrade, practiceGrade) {
    return gradeNumber(officialGrade) === gradeNumber(practiceGrade);
  }

  function eligibilityMessage(officialGrade, practiceGrade) {
    return gradesMatch(officialGrade, practiceGrade)
      ? 'Points eligible — up to your remaining daily Practice limit.'
      : 'Extra Practice — no Math Stars points.';
  }

  function statusMessage(pointsToday) {
    const used = Math.max(0, Math.min(10, Number(pointsToday) || 0));
    return used >= 10
      ? "You've earned all 10 Practice Points today. Keep practising for fun!"
      : `${10 - used} points still available today`;
  }

  const api = { gradeNumber, formatGrade, gradesMatch, eligibilityMessage, statusMessage };
  root.DMKGradePractice = api;
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
})(typeof window !== 'undefined' ? window : globalThis);

