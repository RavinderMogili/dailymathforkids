process.env.JEST_OFFLINE = '1';
delete process.env.ANTHROPIC_API_KEY;
delete process.env.OPENAI_API_KEY;
delete process.env.SUPABASE_URL;
delete process.env.SUPABASE_SERVICE_ROLE;

if (typeof global.fetch === 'function') {
  global.fetch = (...args) => {
    throw new Error(`Unexpected network access in unit tests: ${args[0]}`);
  };
}
