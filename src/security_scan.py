import asyncio
from claude_agent_sdk import query, ClaudeAgentOptions

async def run_security_scan(context, severity_threshold="low"):
    print("Running security scan...")

    prompt = f"""
You are a security-focused code revewier. Analyze the following pull request and identify any security vulnerabilities.
Instructions
- DO NOT USE HYPHENS UNLESS ABSOLUTELY NECESSARY
- DO NOT USE EMOJIS UNLESS ABSOLUTELY NECESSARY

Look specifically for:
- Hardcoded secrets, API keys, tokens, or other passwords
- SQL injection vulnerabilities
- Command injection vulnerabilities
- Unsafe use of eval(), exec(), or subprocess with user input
- Missing input validation on user-facing functions
- Insecure dependencies added in requirements.txt or package.json
- Sensitive data being logged or exposed

Only report findings with severity {severity_threshold.upper()} or higher.
{"Report only HIGH severity findings." if severity_threshold == "high" else ""}
{"Report only MEDIUM and HIGH severity findings." if severity_threshold == "medium" else ""}
{"Report findings of all severity levels." if severity_threshold == "low" else ""}

Here is the pull request:

{context}

Respond in this exact format:
FINDINGS:
- [SEVERITY: HIGH/MEDIUM/LOW] filename:line_number - description of issue

If no issues are found, respond with:
FINDINGS:
- No security issues found
"""
    
    try:
        result = ""
        async for message in query(
            prompt=prompt,
            options=ClaudeAgentOptions(
                allowed_tools=["Read"],
                model="claude-sonnet-4-6"
            ),
        ):
            if hasattr(message, "result"):
                result = message.result
            elif hasattr(message, "output"):
                result = message.output
        
        print("Security scan complete.")
        return result

    except Exception as e:
        print(f"Security scan failed: {e}")
        return f"FINDINGS: \n- Security scan failed: {str(e)}"