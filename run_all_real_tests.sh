#!/bin/bash
# run_all_real_tests.sh — Requires ANTHROPIC_API_KEY

echo ""
echo "=============================================="
echo "  DisSysLab: Running Real Component Tests"
echo "=============================================="
echo ""

if [ -z "$ANTHROPIC_API_KEY" ]; then
    echo "❌ ANTHROPIC_API_KEY not set!"
    echo "   export ANTHROPIC_API_KEY='sk-ant-...'"
    exit 1
fi
echo "✓ ANTHROPIC_API_KEY is set"
echo ""

echo "─── Testing API connection ───"
python3 -c "
from anthropic import Anthropic
client = Anthropic()
msg = client.messages.create(
    model='claude-sonnet-4-20250514',
    max_tokens=20,
    messages=[{'role': 'user', 'content': 'Say OK'}]
)
print(f'  API response: {msg.content[0].text}')
print('  ✓ API connection working')
" 2>&1

if [ $? -ne 0 ]; then
    echo "  ❌ API connection failed. Check your key."
    exit 1
fi
echo ""

echo "=============================================="
echo "  Running Real Examples (costs ~$0.10-0.20)"
echo "=============================================="
echo ""

for mod in \
    "examples.module_02.example_real" \
    "examples.module_03.example_real" \
    "examples.module_04.example_real"; do
    echo "─── $mod ───"
    python3 -m "$mod" 2>&1 && echo "  ✓ Completed" || echo "  ✗ Failed"
    echo ""
done

echo "=============================================="
echo "  All real tests complete!"
echo "  Check: module_02_output.jsonl"
echo "         module_03_output.jsonl"
echo "         module_04_positive.jsonl"
echo "=============================================="