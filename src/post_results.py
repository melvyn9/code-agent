from github_client import post_pr_comment

# Assembles the three agent outputs into a single formatted markdown comment body.
def build_comment(summary, security, quality):
    return f"""## CodeGuard Review

### Summary
{summary.replace("SUMMARY: ", "").strip()}

### Security Findings
{security.replace("FINDINGS: ", "").strip()}

### Quality Notes
{quality.replace("QUALITY NOTES: ", "").strip()}

---
*Reviewed by CodeGuard using Claude Agent SDK. Model: claude-sonnet-4-6*"""

# Builds the review comment and posts it to the PR on GitHub.
def post_review(pr_number, summary, security, quality):
    print("Posting review to GitHub...")
    comment = build_comment(summary, security, quality)
    post_pr_comment(pr_number, comment)
    print("Review posted successfully.") 