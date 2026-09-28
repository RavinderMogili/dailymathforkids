# Third-Party Notices — GSM8K

Some practice questions in `data/practice-pool-extended.json` are adapted from
**GSM8K**, a dataset released by OpenAI.

- Source: https://github.com/openai/grade-school-math
- Paper: Cobbe et al., 2021, "Training Verifiers to Solve Math Word Problems"
  (arXiv:2110.14168)
- Files used: `grade_school_math/data/train.jsonl` (7,473 records) and
  `grade_school_math/data/test.jsonl` (1,319 records) — the original,
  human-written question/answer pairs only. `example_model_solutions.jsonl`
  and the `*_socratic.jsonl` files were **not** used (see
  `tools/word-problems/README.md`).
- Content fingerprint (SHA-256, since the local copy is a snapshot archive
  rather than a git checkout with a resolvable commit):
  - `train.jsonl`: `17f347dc51477c50d4efb83959dbb7c56297aba886e5544ee2aaed3024813465`
  - `test.jsonl`: `3730d312f6e3440559ace48831e51066acaca737f6eabec99bccb9e4b3c39d14`

## License

GSM8K is released by OpenAI under the MIT License. The full text, copied
verbatim from the upstream `LICENSE` file, is retained below as required:

```
MIT License

Copyright (c) 2021 OpenAI

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

This notice applies only to the GSM8K-derived content in
`data/practice-pool-extended.json` (tagged `_source: "gsm8k"` /
`_license: "MIT ..."` on each record). It does not change the license of the
rest of the Daily Math for Kids codebase or content (see the main
[README.md](../../README.md) `## License` section).

## User-facing attribution

Any practice question sourced from GSM8K displays "Adapted from GSM8K
(OpenAI, MIT License)" directly under the topic tag in Practice Mode
(`practice.html`, `#pq-attribution`, toggled by `q._source === 'gsm8k'`).
