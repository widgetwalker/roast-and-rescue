<div align="center">
  <h1>🔥 GitHub Roast & Rescue 🛟</h1>
  <p><strong>A terminal tool that hits your GitHub with a heavy vibe check, then drops the ultimate glow-up routine. No cap.</strong></p>
  <p>
    <img src="https://img.shields.io/badge/Vibe-Immaculate-blue?style=for-the-badge" alt="Vibe" />
    <img src="https://img.shields.io/badge/Architecture-Cloud%20Run-orange?style=for-the-badge" alt="Arch" />
    <img src="https://img.shields.io/badge/Style-Bento%20Box-green?style=for-the-badge" alt="Style" />
    <img src="https://img.shields.io/badge/Agent-Antigravity-9cf?style=for-the-badge" alt="Antigravity Agent" />
  </p>
</div>

---

## ⚡ What is this?

**GitHub Roast and Rescue** is the ultimate tool to give your GitHub profile a professional reality check. We fetch your public data, let our AI cook up a humorous (but kind) roast, and then serve you a "rescue" plan full of actionable, high-ROI steps to make your profile recruiter-ready. 

Whether your repo history is a massive **W** or looking a little mid, we've got you covered.

### 🧠 The Core Loop

1. **Input**: You drop a GitHub username.
2. **Recon**: We safely fetch public profile info, repos, and recent activity (zero sketchy auth required).
3. **The Analysis (Letting the AI Cook)**:
   - ⏱️ **30-Second Recruiter Glance**: Exactly what a hiring manager sees before they get bored.
   - 🔥 **The Roast**: Playful, witty banter about your coding habits (for entertainment only).
   - 🛟 **The Rescue**: A prioritized, actionable roadmap (Quick Wins, Mid-Term, Long-Term) to glow up your profile.
4. **The Serve**: Everything is output in a gorgeous, highly readable **Bento Box-style** terminal layout.

---

## 🚀 Quickstart / How to run

Get it up and running on your local machine faster than you can say "git push origin main --force".

```bash
# 1. Clone it & enter the arena
git clone https://github.com/your-org/roast-and-rescue.git
cd roast-and-rescue

# 2. Install dependencies (it's light, we promise)
pip install -r requirements.txt

# 3. Authenticate with GitHub CLI to bypass rate limits (Massive W)
# Make sure you have the `gh` CLI installed and authenticated
export GITHUB_TOKEN=$(gh auth token)

# 4. Run the vibe check
python main.py octocat
```

---

## 🎨 Design Philosophy 

- **Professional but GenZ-coded**: The roast is witty and culturally relevant, but never toxic or mean-spirited. We keep it strictly HR-friendly but extremely fun.
- **High ROI Actions**: The "Rescue" isn't just generic advice; it gives you measurable, actionable steps that *actually* increase your hireability.
- **Aesthetic Terminal**: Why do CLIs have to be ugly? We use a **Bento Style** grid layout that organizes content into beautifully partitioned, easy-to-read sections. It slaps.

---

## 🏗️ Architecture (The 3-Agent Triad)

This project was built during an 8-hour hackathon utilizing three parallel AI agents working in sync:

1. 💻 **OpenCode (API & Ingestion)**: Engineered the GitHub REST API client ([github_client.py](file:///home/widget/Projects/roast-and-rescue/github_client.py)), fetching public data safely, implementing in-memory TTL caching, and handling rate limits.
2. 🤖 **Claude (Analysis & Synthesis)**: Architected the core feedback logic ([analyzer.py](file:///home/widget/Projects/roast-and-rescue/analyzer.py)), structuring the 30-second recruiter glance, roast generation, and prioritized rescue roadmap.
3. 🕊️ **Antigravity (UI, Cloud Run & Zero-Gravity)**: Engineered the Bento terminal layout ([output.py](file:///home/widget/Projects/roast-and-rescue/output.py)), the threaded Google Cloud Run server ([server.py](file:///home/widget/Projects/roast-and-rescue/server.py)), and the zero-gravity interactive web dashboard.

---

## ⚡ Antigravity Triad Integration

The project architecture features the 3-agent triad required by the hackathon plan:

- **CLI Status Check:**
  ```bash
  python main.py --antigravity
  ```
  *Prints status of the Antigravity serving layer and triad components.*

- **Web Dashboard Zero-Gravity Mode:**
  Visit the dashboard at `http://localhost:8080/` and press `A` (or click **🕊️ Fly Mode**) to activate floating card animations!

- **Cloud Run Agent Endpoint:**
  ```bash
  curl http://localhost:8080/antigravity
  ```

---

## 📜 License

MIT License - Feel free to fork, modify, and build your own vibe checks. Let's get this bread. 🍞