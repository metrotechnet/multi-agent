import re

# Read the file
with open('core/refusal_engine.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace escaped quotes
content = content.replace(r'\"', '"')

# Write back
with open('core/refusal_engine.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("Fixed!")
