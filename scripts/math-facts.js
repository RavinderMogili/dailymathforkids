// Daily "Did You Know?" math facts — one per day based on date
(function() {
  var facts = [
    "A googol is 1 followed by 100 zeros — bigger than the number of atoms in the universe!",
    "The Fibonacci sequence appears in sunflowers, pinecones, and seashells.",
    "Zero was invented in India around the 5th century — before that, there was no way to write 'nothing'.",
    "A circle has infinite lines of symmetry.",
    "If you shuffle a deck of cards, the order you get has probably never existed before in history.",
    "The word 'hundred' comes from the Norse word 'hundrath', which actually meant 120.",
    "Ancient Egyptians used fractions — but only with 1 on top (unit fractions).",
    "Katherine Johnson calculated NASA's flight paths by hand — her math sent astronauts to the moon.",
    "Pi has been calculated to over 100 trillion digits and it never repeats.",
    "A pizza with radius 'z' and height 'a' has volume Pi × z × z × a.",
    "The equals sign (=) was invented in 1557 because a mathematician was tired of writing 'is equal to'.",
    "Bees build hexagonal honeycombs because hexagons use the least wax for the most space.",
    "There are more possible chess games than atoms in the observable universe.",
    "The number 7 is considered the most 'random' number people pick between 1 and 10.",
    "Euler's identity (e^iπ + 1 = 0) connects five fundamental constants in one equation.",
    "Roman numerals have no symbol for zero.",
    "A jiffy is an actual unit of time: 1/100th of a second.",
    "The Pythagorean theorem was known to Babylonians 1000 years before Pythagoras.",
    "Eleven plus two is an anagram of twelve plus one — and they both equal 13.",
    "Every odd number has the letter 'e' in it.",
    "From 0 to 1000, the only number with the letter 'a' is one thousand.",
    "Srinivasa Ramanujan taught himself math from a single borrowed textbook — and became one of history's greatest mathematicians.",
    "A 'palindrome' number reads the same forwards and backwards, like 12321.",
    "If you multiply 111,111,111 × 111,111,111 you get 12345678987654321.",
    "The number 1729 is special — it's the smallest number expressible as the sum of two cubes in two different ways.",
    "Honey bees can count up to 4!",
    "The word 'algebra' comes from the Arabic 'al-jabr', meaning 'reunion of broken parts'.",
    "A baseball diamond is actually a square rotated 45 degrees.",
    "The symbol for division (÷) is called an obelus.",
    "Maryam Mirzakhani was the first woman to win the Fields Medal — math's highest honour."
  ];
  var el = document.getElementById('math-fact');
  if (!el) return;
  var d = new Date();
  var dayIndex = (d.getFullYear() * 366 + d.getMonth() * 31 + d.getDate()) % facts.length;
  el.innerHTML = '<strong>Did you know?</strong> ' + facts[dayIndex];
})();
