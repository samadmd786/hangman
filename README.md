# 🤖 AI-Powered Hangman

A classic Hangman word-guessing game supercharged with **OpenAI GPT-4o-mini** — featuring AI-generated words, context-aware hints, live win probability, and post-game analysis. Built with [Streamlit](https://streamlit.io/) for instant deploy-and-play.

🔗 **[Play it live → ai-hangman.streamlit.app](https://ai-hangman.streamlit.app/)**


## ✨ Features

| Feature | Description |
|---------|-------------|
| 🎮 **3 Difficulty Levels** | Easy (8 attempts), Medium (6), Hard (4) — with scaled word lengths |
| 🤖 **AI Word Generation** | GPT generates fresh, unique words every round — no repeating word lists |
| 💡 **AI Hints** | Cryptic, context-aware one-liner hints that nudge without spoiling |
| 🎯 **Live Win Probability** | Real-time gauge using a hypergeometric probability model, color-coded green → red |
| 🧠 **Post-Game Analysis** | AI-generated word insight, strategy review, and fun facts after every game |
| 🏆 **Score & Streak Tracker** | Wins, losses, current streak 🔥, and best streak 👑 across sessions |
| 🎨 **Animated SVG Hangman** | Smooth CSS fade-in body parts replace traditional ASCII art |
| 📋 **Offline Fallback** | No API key? The game still works with a curated built-in word list |

## 🎮 How to Play

1. **Pick a difficulty** in the sidebar — this sets word length and number of allowed mistakes
2. **Guess one letter at a time** using the input field
3. Correct letters are revealed in the word; wrong guesses draw body parts on the gallows
4. **Use AI Hint** (🤖 button) if you're stuck — the AI gives a creative clue without spoiling the answer
5. Win by revealing all letters before the hangman is fully drawn
6. After each game, read the **Post-Game Analysis** for word trivia and strategy tips


## 🚀 Getting Started

### Prerequisites

- Python 3.8+
- OpenAI API key *(optional — the game works without it, AI features are simply disabled)*
  - Get one at [platform.openai.com/api-keys](https://platform.openai.com/api-keys)

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
# Without AI features (works out of the box)
streamlit run ai_hangman.py

# With AI features — option 1: secrets file (recommended)
# Create/edit .streamlit/secrets.toml and add:  OPENAI_API_KEY = "sk-..."
streamlit run ai_hangman.py

# With AI features — option 2: environment variable
export OPENAI_API_KEY=your-api-key-here
streamlit run ai_hangman.py

# With AI features — option 3: paste in the app
# Just run the app and enter your key in the sidebar 🔑 input
```

### Deploying on Streamlit Cloud

1. Push this repo to GitHub
2. Connect it at [share.streamlit.io](https://share.streamlit.io/)
3. Go to **App Settings → Secrets** and add:
   ```toml
   OPENAI_API_KEY = "sk-..."
   ```
4. Done — the key is loaded automatically via `st.secrets`

> End users can also paste their own key in the sidebar 🔑 input (stored in session memory only, never written to disk).


## 📁 Project Structure

| File | Description |
|------|-------------|
| `ai_hangman.py` | Main app — AI-powered hangman with all features (852 lines) |
| `app.py` | Original classic hangman (no AI, no OpenAI dependency) |
| `.streamlit/secrets.toml` | **Gitignored** — local-only secrets file for API keys |
| `requirements.txt` | Python dependencies (`streamlit`, `openai`) |
| `.gitignore` | Comprehensive Python + Streamlit gitignore |

## 🔒 Security

- `.streamlit/secrets.toml` is **gitignored** — your API key is never committed to the repo
- On Streamlit Cloud, secrets are stored securely via the dashboard and injected at runtime
- API keys entered in the sidebar are stored **only in session memory** and are never written to disk
- All OpenAI API calls happen **server-side** in Python — your key is never exposed in browser/client-side code
- Key resolution priority: manual sidebar input → `st.secrets` → `OPENAI_API_KEY` env var

## 🧮 How Win Probability Works

The app calculates a **live win probability** after every guess using a [hypergeometric distribution](https://en.wikipedia.org/wiki/Hypergeometric_distribution):

- **Pool** = 26 minus letters already guessed
- **Needed** = distinct un-revealed letters remaining in the word
- **Draws** = remaining wrong guesses allowed
- The model averages across all candidate words from the built-in list that match the current board state
- For AI-generated words not in the list, it falls back to the actual target word

The probability bar is color-coded: 🟢 ≥ 70% → 🟠 ≥ 40% → 🔴 < 40%.

## 🛠 Tech Stack

- **Frontend:** [Streamlit](https://streamlit.io/) (wide layout, sidebar, session state)
- **AI Model:** [OpenAI GPT-4o-mini](https://openai.com/) — word generation, hints, post-game analysis
- **Language:** Python 3.8+
- **Visualization:** Inline SVG with CSS keyframe animations
- **Math:** Hypergeometric probability model (`math.lgamma`)

## 📜 License

This project is open source. Feel free to fork, modify, and share.