import asyncio
import os
from dotenv import load_dotenv
from claude_agent_sdk import query, ClaudeAgentOptions
from github_client import get_changed_files, post_pr_comment
from gather_context import gather_pr_context
from security_scan import run_security_scan
from quality_review import run_quality_review
from summarize_pr import run_summary
from post_results import post_review
load_dotenv()

async def main():
    pr_number = os.getenv("PR_NUMBER", "1")

    # Gather context
    context = gather_pr_context(pr_number)

    # Run security scan
    security_results = await run_security_scan(context)
    # Run quality review
    quality_results = await run_quality_review(context)
    # Run summary review
    summary_results = await run_summary(context)

    print("\n-- SUMMARY RESULTS ---")
    print("\n-- SECURITY RESULTS ---")
    print("\n-- QUALITY RESULTS ---")

    # Post comment to GitHub
    post_review(pr_number, summary_results, security_results, quality_results)
asyncio.run(main())