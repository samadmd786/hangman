# 🤖 AI-Powered Hangman

A classic Hangman game enhanced with OpenAI-powered features, built with Streamlit.

🔗 **[Play it live → ai-hangman.streamlit.app](https://ai-hangman.streamlit.app/)**

## ✨ Features

- **🎮 Difficulty Levels** — Easy (8 attempts), Medium (6 attempts), Hard (4 attempts) with word pools of varying lengths
- **🤖 AI Hints** — Get cryptic, context-aware hints from GPT to help you guess the word
- **🎯 Win Probability** — Live probability gauge using a hypergeometric model, with dynamic color-coded progress bar
- **🧠 Post-Game Analysis** — AI-generated word insights, strategy review, and fun facts after each game
- **🏆 Score & Streak Tracker** — Track wins, losses, current streak 🔥, and best streak 👑
- **🎨 Animated SVG Hangman** — Smooth fade-in animations replace traditional ASCII art

## 🚀 Getting Started

### Prerequisites

- Python 3.8+
- OpenAI API key (optional — game works without it, AI features are disabled)
  - Get one at [platform.openai.com/api-keys](https://platform.openai.com/api-keys)
  - You can either set the `OPENAI_API_KEY` environment variable or paste it directly in the app's 🔑 input

### Installation

```bash
# Clone the repo
git clone https://github.com/samadmd786/hangman.git
cd hangman

# Install dependencies
pip install -r requirements.txt
```

### Running Locally

```bash
# Without AI features
streamlit run ai_hangman.py

# With AI features
export OPENAI_API_KEY=your-api-key-here
streamlit run ai_hangman.py
```

### Running on Streamlit Cloud

1. Deploy the app from this repo
2. Paste your OpenAI API key in the 🔑 input in the sidebar (stored in memory only, never saved)

## 📁 Project Structure

| File | Description |
|------|-------------|
| `ai_hangman.py` | Main app — AI-powered hangman with all features |
| `app.py` | Original hangman game (no AI) |
| `requirements.txt` | Python dependencies |

## 🔒 Security

- API keys entered in the app are stored **only in session memory** and are never written to disk, logged, or persisted
- Environment variable `OPENAI_API_KEY` is the recommended approach for local development

## 🛠 Tech Stack

- **Frontend:** [Streamlit](https://streamlit.io/)
- **AI:** [OpenAI GPT-4o-mini](https://openai.com/)
- **Language:** Python