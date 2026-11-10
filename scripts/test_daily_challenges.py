import datetime
import itertools
import unittest
import unittest.mock
import xml.etree.ElementTree as ET

import gen_site
from daily_challenges import make_challenge, inject_daily_challenges
from gen_site import extract_qa_pairs, generate_html_from_text, parse_grade_sections


def quiz_fixture():
    return '\n'.join(f'## G{g}\n' + '\n'.join(
        f'{i}. **[{difficulty}] Original {i}**\n   - EN: Original {i}\n   - FR: Original {i}\n   - Choices: A) 1   B) 2   C) 3   D) 4\n   - Hint: Count\n   - Steps:\n     - Count\n   - Answer: 1\n'
        for i, difficulty in enumerate(['Easy'] * 4 + ['Medium'] * 4 + ['Hard'] * 2, 1))
        for g in range(1, 13))


class DailyChallengesTest(unittest.TestCase):
    def test_all_grades_dates_and_slots_are_valid_and_deterministic(self):
        for offset in range(30):
            day = datetime.date(2026, 11, 1) + datetime.timedelta(days=offset)
            for grade in range(1, 13):
                questions = [make_challenge(grade, day, slot) for slot in range(2)]
                self.assertEqual(questions, [make_challenge(grade, day, slot) for slot in range(2)])
                self.assertNotEqual(questions[0]['question'], questions[1]['question'])
                for q in questions:
                    self.assertEqual(len(set(q['choices'])), 4)
                    self.assertIn(q['answer'], q['choices'])
                    self.assertTrue(q['fr'])
                    self.assertTrue(q['steps'])
                    self.assertEqual(q['difficulty'], 'hard')
                    svg = ET.fromstring(q['diagram'])
                    self.assertEqual(svg.attrib['role'], 'img')
                    self.assertTrue(svg.attrib['aria-label'])
                    self.assertNotIn('<script', q['diagram'])

    def test_injection_appends_two_hard_questions_without_replacing_originals(self):
        result = inject_daily_challenges(quiz_fixture(), '2026-11-02')
        self.assertEqual(result.count('Math Challenge /'), 24)
        self.assertEqual(result.count('Original'), 360)
        self.assertEqual(result, inject_daily_challenges(result, '2026-11-02'))
        for code, section in parse_grade_sections(result).items():
            grade = int(code[1:])
            questions, answers = extract_qa_pairs(section)
            self.assertEqual(len(questions), 12)
            self.assertEqual(len(answers), 12)
            for idx in (10, 11):
                q = make_challenge(grade, '2026-11-02', idx - 10)
                self.assertEqual(questions[idx], q['question'])
                self.assertEqual(answers[idx], q['answer'])
                self.assertIn(f'{idx + 1}. **[Hard]', section)
        page = generate_html_from_text(result, '2026-11-02')
        self.assertNotIn('CHALLENGE-DIAGRAM-', page)
        self.assertEqual(page.count('<svg class="challenge-diagram"'), 24)

    def test_curated_gsm8k_questions_are_preserved(self):
        section = '## G4\n8. **[Medium] Curated GSM8K**\n   - EN: Curated\n   - Answer: 1\n'
        self.assertIn('Curated GSM8K', inject_daily_challenges(section, '2026-11-02'))

    def test_visual_combinatorics_by_enumeration(self):
        day = '2026-11-02'
        for grade in (9, 10):
            seats = grade - 2
            ways = sum(all(b - a > 1 for a, b in zip(chosen, chosen[1:]))
                       for chosen in itertools.combinations(range(seats), 3))
            self.assertEqual(int(make_challenge(grade, day, 0)['answer']), ways)
        for grade in (11, 12):
            size = grade - 8
            ways = sum(not any(sum(1 if pos in up else -1 for pos in range(k)) > 0 for k in range(1, 2 * size + 1))
                       for up in itertools.combinations(range(2 * size), size))
            self.assertEqual(int(make_challenge(grade, day, 0)['answer']), ways)

    def test_openai_quota_error_falls_back_to_gemini(self):
        class QuotaError(Exception):
            status_code = 429

        class FailingOpenAI:
            def __init__(self, **kwargs):
                raise QuotaError('insufficient_quota: credit_balance_exhausted')

        with unittest.mock.patch.object(gen_site, 'OpenAI', FailingOpenAI), \
             unittest.mock.patch.dict('os.environ', {'OPENAI_API_KEY': 'key'}), \
             unittest.mock.patch.object(gen_site, '_local_llm_reachable', return_value=False), \
             unittest.mock.patch.object(gen_site, 'call_gemini_llm', return_value='generated'):
            self.assertEqual(gen_site.call_llm('prompt'), 'generated')

    def test_gemini_can_generate_when_openai_is_absent(self):
        with unittest.mock.patch.dict('os.environ', {'OPENAI_API_KEY': '', 'GEMINI_API_KEY': 'key'}), \
             unittest.mock.patch.object(gen_site, '_local_llm_reachable', return_value=False), \
             unittest.mock.patch.object(gen_site, 'call_gemini_llm', return_value='generated'):
            self.assertEqual(gen_site.call_llm('prompt'), 'generated')

    def test_invalid_grade_and_slot(self):
        for grade in (0, 13):
            with self.assertRaises(ValueError):
                make_challenge(grade, '2026-11-02')
        with self.assertRaises(ValueError):
            make_challenge(1, '2026-11-02', 2)


if __name__ == '__main__':
    unittest.main()
