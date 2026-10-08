# GitHub Roast and Rescue - Plan (Updated with Bento Style & Skills)

## Context

This is an 8-hour AI hackathon project to build a tool that analyzes a GitHub public profile and provides honest, funny (but not cruel) feedback, plus actionable improvement advice. The user inputs a GitHub username, and the app reads their public GitHub data, analyzes it, and returns a "roast" with rescue recommendations.

**Design Style: Bento Style** - A grid-based dashboard layout that partitions content into clear, organize sections (recruiter glance, roast, rescue with quick wins/medium/long-term). Inspired by bento boxes, this style is terminal-friendly and naturally organizes the app's three main output sections.

Key constraints:
- Only cloud run is allowed (deployment target)
- 8-hour build window
- Must use Claude (this agent), antigravity, and opencode
- Three agents should run in parallel where possible
- **Skills from library integrated throughout**

## Incorporated Skills from Library

The following skills will be used by the three building agents:

### `update-config` - Harness Configuration
- Used by Agent 1 to configure Claude Code settings.json for allowed permissions
- Sets up env vars for GitHub API (though unauthenticated mode used)
- Configures permission allowlist to reduce prompts during development

### `keybindings-help` - Keyboard Shortcuts
- Used by Agent 3 to design terminal-friendly keyboard shortcuts
- Configures submit keys, chord bindings for the output UI
- Makes the terminal interface more efficient

### `code-review` - Code Quality Review
- Used by Agent 2 to review the analysis prompt quality
- Ensures prompts are correct, efficient, and follow code principles
- Checks for code smells in the generated feedback logic

### `simplify` - Code Simplification
- Used across all agents to review and refactor code
- Removes redundancy, simplifies complex prompt structures
- Upholds code cleanliness principles

### `security-review` - Security Review
- Used by Agent 1 to ensure GitHub API fetching is safe
- Validates no private data is requested or stored
- Ensures the app handles usernames safely

### `fewer-permission-prompts` - Permission Allowlist
- Used by Agent 1 to add read-only allowlist to settings.json
- Reduces permission prompts when running GitHub API calls
- Allows `curl`, `bash`, `read` operations without asking each time

### `workflow-authoring` - Workflow Scripting
- Used to structure the build process across the three agents
- Defines the pipeline: API fetch → analysis → output formatting
- Ensures proper ordering and dependencies

### `claude-api` - API Reference
- Referenced for prompt design patterns
- Ensures proper use of Claude Code features
- Model selection and parameter guidance

### `brag-slim` - Slim Bragging
- Used by Agent 2 to showcase concise profile highlights in the recruiter glance
- Helps distill the most important information for the "30-second recruiter glance"

## Architecture & Division of Labor

Three parallel agents will handle distinct responsibilities, each incorporating specific skills:

### Agent 1: GitHub API Integration & Harness Setup (Uses: `update-config`, `fewer-permission-prompts`, `security-review`)
- Fetch public GitHub REST API data
- Configure settings.json with `update-config` skill
- Add permission allowlist with `fewer-permission-prompts`
- Ensure safe API fetching with `security-review`
- Handle rate limiting and caching

**Key API endpoints:**
- `GET /users/{username}` — profile info
- `GET /users/{username}/repos` — repositories list
- `GET /users/{username}/events` — recent activity

### Agent 2: AI Analysis & Feedback Generation (Uses: `code-review`, `simplify`, `claude-api`, `brag-slim`)
- Craft prompts that extract meaningful insights from the data
- Generate the "recruiter glance" summary using code review principles and `brag-slim`
- Create humorous-but-not-cruel roast text
- Produce specific, actionable improvement advice
- Ensure tone consistency (funny → constructive)
- Use `simplify` to keep prompts clean and efficient

**Prompt design considerations (with code-review):**
- What does a recruiter notice in 30 seconds?
- How to be funny without crossing into cruelty
- What format helps someone actually improve afterwards

### Agent 3: UI/Output Formatting & Rescue Advice (Uses: `keybindings-help`, `security-review`)
- Format the output for readability using **Bento Style** grid layout
- Structure the rescue/improvement advice with prioritized steps
- Create visual layout (terminal-friendly Bento Style grid)
- Generate follow-up suggestions
- Design keyboard shortcuts with `keybindings-help`
- Security-check the output pipeline

## Technical Design

### Data Flow
```
User inputs username → Agent 1 fetches GitHub API → Data normalized → 
Agent 2 analyzes with Claude (using code-review/simplify) → Feedback generated → 
Agent 3 formats output (using Bento Style/keybindings-help) → Final presentation
```

### Key Design Decisions

1. **GitHub API only, no auth needed** for public data. Rate limit: 60/hr for unauthenticated.
   - `update-config` sets this up; `fewer-permission-prompts` reduces prompts

2. **Data we actually fetch** (keeping it lightweight):
   - Profile: bio, location, blog, company, followership
   - Repos: top 10 by stars, languages, last pushed, repo names
   - Activity: recent events (commits, issues, PRs)

3. **Claude prompt structure** (reviewed with `code-review`):
   - Raw data summary
   - "Recruiter questions" framing
   - Tone constraints (funny, not cruel; constructive)
   - Output format requirements (Bento Style)

4. **Output format** (Bento Style terminal-friendly markdown, designed with `keybindings-help`):
   - Header with profile summary
   - "30-Second Recruiter Glance" section (using `brag-slim` to distill key info)
   - "The Roast" (humorous, constructive)
   - "The Rescue" (actionable steps, prioritized into Quick Wins/Medium-term/Long-term)
   - "Quick Wins" (3 immediate things to fix)

5. **Cloud Run deployment**: The three agents build the application locally. The completed Python app (with `requirements.txt`) is then deployed to Cloud Run, which accepts POST requests with a `username` field.

## Critical Files to Create

1. `/home/widget/Projects/roast-and-rescue/main.py` — Main entry point
2. `/home/widget/Projects/roast-and-rescue/github_client.py` — GitHub API client
3. `/home/widget/Projects/roast-and-rescue/analyzer.py` — Claude-powered analysis
4. `/home/widget/Projects/roast-and-rescue/output.py` — Output formatting (Bento Style)
5. `/home/widget/Projects/roast-and-rescue/requirements.txt` — Dependencies
6. `/home/widget/Projects/roast-and-rescue/README.md` — Project documentation

## Agent Running Context

**During development/testing:**
- All three agents run locally in this session
- They collaborate via the plan file and codebase
- No cloudrun involvement until the very end
- The user can test the platform locally by running `python main.py --username <handle>`

**For cloudrun deployment:**
- After local testing passes, the app is packaged
- Deployed to cloudrun as the production target
- The cloudrun instance accepts HTTP POST with `{"username": "github_handle"}`
- No agents run on cloudrun — it's a static server

## Verification

End-to-end test flow (local testing):
1. Run `python main.py --username <github_handle>`
2. Verify output includes: profile summary, roast, rescue advice
3. Check that tone is funny but not cruel (self-audit via `code-review`)
4. Confirm all advice is specific and actionable
5. Test with a few known GitHub profiles

Cloud Run verification:
- Send POST request to the deployed endpoint
- Confirm it returns properly formatted feedback (Bento Style layout)
- Check error handling for invalid usernames

## Timeline (8 hours)

- **Hour 1**: Plan finalization, skill integration, Bento Style design
- **Hour 2**: Implement GitHub API client (Agent 1, using `update-config`/`fewer-permission-prompts`)
- **Hour 3**: Implement Claude analysis prompts (Agent 2, using `code-review`/`simplify`/`brag-slim`)
- **Hour 4**: Implement output formatting (Agent 3, using `Bento Style`/`keybindings-help`)
- **Hour 5**: Integrate all components, basic error handling
- **Hour 6**: Test with 3-4 test profiles, refine prompts with `code-review`
- **Hour 7**: Polish, error edge cases, optimize with `simplify`
- **Hour 8**: Final review, documentation, cloudrun deploy prep

## Notes

- Keep it simple — only public data, no auth
- The "humor" must be carefully bounded; we'll include a disclaimer
- Focus on *improvement* not just roasting — the "rescue" part is critical
- Three agents build locally; completed app deploys to cloudrun
- **Bento Style** design organizes roast/rescue into clear grid sections
- Skills integrated throughout for clean code and efficiency
- Permission prompts reduced via `fewer-permission-prompts` allowlist
- `brag-slim` used for concise recruiter glance summaries