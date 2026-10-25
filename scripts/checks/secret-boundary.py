"""Report filenames only, never credential values. Run before publishing source/artifacts."""
from pathlib import Path
from dotenv import dotenv_values

root = Path(__file__).resolve().parents[1]
values = dotenv_values(root / 'backend/.env')
private = [str(values[k]).encode() for k in ('GEMINI_API_KEY', 'MIRO_ACCESS_TOKEN', 'MIRO_CLIENT_SECRET') if values.get(k)]
if not private:
    raise SystemExit('No local credentials available for the boundary check.')
frontend = dotenv_values(root / '.env.local')
assert set(frontend).issubset({'BACKEND_URL', 'NEXT_DIST_DIR'}), 'Frontend environment must contain no provider configuration.'
files = []
for name in ('app', 'components', 'lib', 'public', '.next-build', '.next/static', '.next-test/static'):
    base = root / name
    if base.exists():
        files.extend(p for p in base.rglob('*') if p.is_file() and 'node_modules' not in p.parts)
found = []
for file in files:
    if file.stat().st_size > 50 * 1024 * 1024:
        continue
    content = file.read_bytes()
    if any(secret in content for secret in private):
        found.append(str(file.relative_to(root)))
if found:
    raise SystemExit('Private credential found in: ' + ', '.join(found))
print(f'PASS private credentials absent from {len(files)} frontend source/build files; frontend env contains no provider credentials.')
