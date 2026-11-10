import os, sys
sys.path.insert(0, r'd:\githubProjects\dailymathforkids-main\scripts')
import gen_site

key = os.environ.get('GEMINI_API_KEY', '')
if not key:
    print('ERROR: set GEMINI_API_KEY first')
    sys.exit(1)

result = gen_site.call_free_llm('Say "Gemini is working" in French, nothing else.')
print('RESULT:', result)