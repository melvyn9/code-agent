import asyncio
import os
from dotenv import load_dotenv
from claude_agent_sdk import query, ClaudeAgentOptions
from github_client import get_changed_files, post_pr_comment, commit_file
from gather_context import gather_pr_context
from security_scan import run_security_scan
from quality_review import run_quality_review
from summarize_pr import run_summary
from post_results import post_review
from detect_new_repo import is_new_repo
from explore_codebase import explore_codebase
from gen_contributing import gen_contributing
from gen_architecture import gen_architecture
from gen_setup_guide import gen_setup_guide
from config import load_config
from logger import SessionLogger
load_dotenv()

async def run_onboarding(config, logger):
    if not config["onboarding"]["enabled"]:
        print("Onboarding disabled in config. Skipping.")
        return
    
    print("Starting onboarding pipeline")
    codebase_summary = await explore_codebase()
    logger.log("explore_codebase", "explore", codebase_summary)

    print("Generating docs in parllel")
    contributing, architecture, setup = await asyncio.gather(
        gen_contributing(codebase_summary),
        gen_architecture(codebase_summary),
        gen_setup_guide(codebase_summary)
    )

    # Logger
    logger.log("gen_contributing", codebase_summary, contributing)
    logger.log("gen_architecture", codebase_summary, architecture)
    logger.log("gen_setup_guide", codebase_summary, setup)

    commit_file("CONTRIBUTING.md", contributing, "docs: add CONTRIBUTING.md using CodeGuard onboarding")
    commit_file("ARCHITECTURE.md", architecture, "docs: add ARCHITECTURE.md using CodeGuard onboarding")
    commit_file("SETUP.md", architecture, "docs: add SETUP.md using CodeGuard onboarding")
    print("Onboarding pipeline complete.")

async def main():
    config = load_config()
    logger = SessionLogger()
    event_name = os.getenv("EVENT_NAME", "pull_request")
    comment_body = os.getenv("COMMENT_BODY", "").strip()

    if event_name == "issue_comment":
        if comment_body == "/onboard":
            print("/onboard command detected. Running onboarding pipeline...")
            await run_onboarding(config, logger)
        else:
            print("Comment is not an onboard command. Skipping.")

    elif event_name == "push":
        if is_new_repo():
            await run_onboarding(config, logger)
        else:
            print("Repo already onboarded. Nothing to do.")
    
    else:
        pr_number = os.getenv("PR_NUMBER", "1")
        # Gather context
        context = gather_pr_context(pr_number)

        security_results = ""
        quality_results = ""
        summary_results = ""

        if config["security"]["enabled"]:
            security_results = await run_security_scan(
                context,
                severity_threshold=config["security"]["severity_threshold"]
                )
            logger.log("security_scan", context, security_results)
        else:
            security_results = "FINDINGS:]"
        if config["quality"]["enabled"]:
            quality_results = await run_quality_review(context)
            logger.log("quality_review", context, quality_results)
        else:
            quality_results = "QUALITY NOTES:\n- Quality review disabled in config"

        if config["summary"]["enabled"]:
            summary_results = await run_summary(context)
            logger.log("summary", context, summary_results)
        else:
            summary_results = "SUMMARY:\n- Summary disabled in config"
        # Post comment to GitHub
        post_review(pr_number, summary_results, security_results, quality_results)

    logger.save()
asyncio.run(main())