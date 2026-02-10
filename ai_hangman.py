import streamlit as st
import streamlit.components.v1 as components
import random
import os
import math
from openai import OpenAI

# Constants & Config

WORD_LIST = {
    "easy": [
        "APPLE", "BREAD", "CHAIR", "DANCE", "FIRE", "GATE", "HAND", "JUMP",
        "KING", "LAMP", "MOON", "NEST", "OPEN", "PLAY", "RAIN", "STAR",
        "TREE", "WAVE", "BLUE", "CAKE", "FISH", "GOLD", "HOME", "LAKE",
    ],
    "medium": [
        "EARTH", "FLAME", "GRAPE", "HOUSE", "JUICE", "LIGHT", "MONEY",
        "MUSIC", "OCEAN", "PARTY", "QUEEN", "SMILE", "STONE", "TIGER",
        "TRAIN", "WATER", "BEACH", "CLOUD", "DREAM", "FROST", "GHOST",
        "HEART", "IVORY", "JEWEL", "KNEEL", "LEMON", "MAGIC", "NIGHT",
    ],
    "hard": [
        "BRIDGE", "CASTLE", "DANGER", "EMPIRE", "FALCON", "GUITAR",
        "HEAVEN", "ISLAND", "JUNGLE", "KNIGHT", "MUSEUM", "ORANGE",
        "PALACE", "QUARTZ", "ROCKET", "SHADOW", "TEMPLE", "VOYAGE",
        "WINTER", "ZOMBIE", "CRYPTIC", "BAFFLED", "PUZZLED", "COMPLEX",
    ],
}

DIFFICULTY_CONFIG = {
    "Easy 🟢":   {"key": "easy",   "attempts": 8, "label": "4–5 letters, 8 attempts"},
    "Medium 🟡": {"key": "medium", "attempts": 6, "label": "5–6 letters, 6 attempts"},
    "Hard 🔴":   {"key": "hard",   "attempts": 4, "label": "6–7 letters, 4 attempts"},
}


# SVG Animated Hangman

def get_hangman_svg(wrong_guesses, max_attempts):
    """Generate an SVG hangman with CSS fade-in animations."""
    # Map wrong guesses to body parts (scale to max 6 body parts)
    # For easy (8 attempts) we show a part every ~1.3 wrong guesses
    # For hard (4 attempts) we show a part every ~0.67 wrong guesses
    ratio = wrong_guesses / max_attempts if max_attempts > 0 else 0
    parts_to_show = min(6, int(ratio * 6 + 0.5))  # 0-6 body parts

    fade_css = """
    @keyframes fadeIn {
        from { opacity: 0; transform: scale(0.8); }
        to   { opacity: 1; transform: scale(1); }
    }
    .body-part { animation: fadeIn 0.5s ease-out forwards; }
    """

    # Body parts SVG elements
    body_parts = [
        # Head
        '<circle cx="150" cy="70" r="20" fill="none" stroke="#e74c3c" stroke-width="3" class="body-part"/>',
        # Body
        '<line x1="150" y1="90" x2="150" y2="140" stroke="#e74c3c" stroke-width="3" class="body-part"/>',
        # Left arm
        '<line x1="150" y1="100" x2="120" y2="130" stroke="#e74c3c" stroke-width="3" class="body-part"/>',
        # Right arm
        '<line x1="150" y1="100" x2="180" y2="130" stroke="#e74c3c" stroke-width="3" class="body-part"/>',
        # Left leg
        '<line x1="150" y1="140" x2="120" y2="175" stroke="#e74c3c" stroke-width="3" class="body-part"/>',
        # Right leg
        '<line x1="150" y1="140" x2="180" y2="175" stroke="#e74c3c" stroke-width="3" class="body-part"/>',
    ]

    # Gallows (always visible)
    gallows = """
        <line x1="60" y1="190" x2="200" y2="190" stroke="#8B4513" stroke-width="4"/>
        <line x1="100" y1="190" x2="100" y2="30"  stroke="#8B4513" stroke-width="4"/>
        <line x1="100" y1="30"  x2="150" y2="30"  stroke="#8B4513" stroke-width="4"/>
        <line x1="150" y1="30"  x2="150" y2="50"  stroke="#8B4513" stroke-width="3"/>
        <line x1="100" y1="60"  x2="120" y2="30"  stroke="#8B4513" stroke-width="2"/>
    """

    # Rope
    rope = '<line x1="150" y1="30" x2="150" y2="50" stroke="#DAA520" stroke-width="2"/>'

    # Dead face details (X eyes and frown)
    dead_face = ""
    if parts_to_show >= 6:
        dead_face = """
            <line x1="141" y1="64" x2="147" y2="70" stroke="#e74c3c" stroke-width="2" class="body-part"/>
            <line x1="147" y1="64" x2="141" y2="70" stroke="#e74c3c" stroke-width="2" class="body-part"/>
            <line x1="153" y1="64" x2="159" y2="70" stroke="#e74c3c" stroke-width="2" class="body-part"/>
            <line x1="159" y1="64" x2="153" y2="70" stroke="#e74c3c" stroke-width="2" class="body-part"/>
            <path d="M 141 80 Q 150 75 159 80" fill="none" stroke="#e74c3c" stroke-width="2" class="body-part"/>
        """

    visible_parts = "\n".join(body_parts[:parts_to_show])

    svg = f"""
    <div style="display:flex; justify-content:center; padding: 10px;">
        <svg viewBox="0 0 260 200" width="280" height="220" xmlns="http://www.w3.org/2000/svg">
            <style>{fade_css}</style>
            <rect width="260" height="200" rx="12" fill="#1a1a2e" opacity="0.9"/>
            {gallows}
            {rope}
            {visible_parts}
            {dead_face}
        </svg>
    </div>
    """
    return svg


# Game Logic

def init_stats():
    """Initialize score tracking if not present."""
    if "wins" not in st.session_state:
        st.session_state.wins = 0
        st.session_state.losses = 0
        st.session_state.total_games = 0
        st.session_state.current_streak = 0
        st.session_state.best_streak = 0


def generate_word_from_ai(difficulty_key):
    """Ask OpenAI to generate a word matching the difficulty."""
    api_key = os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        return None

    length_map = {"easy": "4 or 5", "medium": "5 or 6", "hard": "6 or 7"}
    target_len = length_map.get(difficulty_key, "5")

    try:
        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a word generator for a hangman game."},
                {"role": "user", "content": (
                    f"Generate exactly ONE random common English word that is exactly "
                    f"{target_len} letters long. "
                    "Reply with ONLY the word in uppercase, nothing else. "
                    "No punctuation, no explanation."
                )},
            ],
            max_tokens=10,
            temperature=1.2,
        )
        word = response.choices[0].message.content.strip().upper()
        if word.isalpha() and len(word) in range(4, 9):
            return word
        return None
    except Exception:
        return None


def init_game():
    """Initializes or resets the game state."""
    init_stats()

    # Get difficulty from session state (default Medium)
    difficulty = st.session_state.get("difficulty", "Medium 🟡")
    config = DIFFICULTY_CONFIG[difficulty]
    diff_key = config["key"]

    # Try AI-generated word, fall back to word list
    ai_word = generate_word_from_ai(diff_key)
    if ai_word:
        st.session_state.target_word = ai_word
        st.session_state.word_source = "🤖 AI"
    else:
        st.session_state.target_word = random.choice(WORD_LIST[diff_key])
        st.session_state.word_source = "📋 List"

    st.session_state.max_attempts = config["attempts"]
    st.session_state.remaining_attempts = config["attempts"]
    st.session_state.guessed_letters = set()
    st.session_state.game_over = False
    st.session_state.game_result = ""
    st.session_state.feedback = "Game started! Guess a letter."
    st.session_state.ai_hint = ""
    st.session_state.post_game_analysis = ""
    st.session_state.balloons_shown = False
    st.session_state.snow_shown = False


def check_guess(letter):
    """Processes the user's letter guess."""
    letter = letter.upper()

    if letter in st.session_state.guessed_letters:
        st.session_state.feedback = f"You already guessed '{letter}'."
        return

    st.session_state.guessed_letters.add(letter)

    if letter in st.session_state.target_word:
        st.session_state.feedback = f"Correct! '{letter}' is in the word."
    else:
        st.session_state.remaining_attempts -= 1
        st.session_state.feedback = f"Sorry, '{letter}' is not in the word."

    st.session_state.ai_hint = ""
    check_win_loss()


def check_win_loss():
    """Checks if the game has ended and updates stats."""
    word_set = set(st.session_state.target_word)

    if word_set.issubset(st.session_state.guessed_letters):
        st.session_state.game_over = True
        st.session_state.game_result = "win"
        st.session_state.feedback = "Congratulations! You won!"
        # Update stats
        st.session_state.wins += 1
        st.session_state.total_games += 1
        st.session_state.current_streak += 1
        st.session_state.best_streak = max(
            st.session_state.best_streak, st.session_state.current_streak
        )

    elif st.session_state.remaining_attempts == 0:
        st.session_state.game_over = True
        st.session_state.game_result = "loss"
        st.session_state.feedback = f"Game Over! The word was: {st.session_state.target_word}"
        # Update stats
        st.session_state.losses += 1
        st.session_state.total_games += 1
        st.session_state.current_streak = 0


# Win Probability Calculation

def get_candidate_words():
    """Return words from WORD_LIST that still match the current game state."""
    guessed = st.session_state.guessed_letters
    target = st.session_state.target_word
    incorrect = {l for l in guessed if l not in target}

    pattern = [
        letter if letter in guessed else None
        for letter in target
    ]

    # Search across all difficulty word lists
    all_words = []
    for words in WORD_LIST.values():
        all_words.extend(words)

    candidates = []
    for word in all_words:
        if len(word) != len(target):
            continue
        if any(ch in incorrect for ch in word):
            continue
        match = True
        for i, p in enumerate(pattern):
            if p is not None and word[i] != p:
                match = False
                break
            if p is None and word[i] in guessed:
                match = False
                break
        if match:
            candidates.append(word)
    return candidates


def _hypergeometric_prob(needed, pool_size, remaining):
    """Probability of drawing all *needed* letters within *remaining* attempts
    from a pool of *pool_size* un-guessed letters (hypergeometric model)."""
    if needed == 0:
        return 1.0
    wrong_in_pool = pool_size - needed
    max_wrong = remaining  # correct guesses don't cost attempts
    if max_wrong < 0:
        return 0.0

    p = 0.0
    for w in range(max_wrong + 1):
        draws = needed + w
        if draws > pool_size:
            break
        log_p = (
            _log_comb(wrong_in_pool, w)
            + _log_comb(needed, needed)
            - _log_comb(pool_size, draws)
        )
        p += math.exp(log_p)
    return min(p, 1.0)


def calculate_win_probability():
    """Estimate probability of winning using a hypergeometric model."""
    if st.session_state.game_over:
        return 1.0 if st.session_state.game_result == "win" else 0.0

    guessed = st.session_state.guessed_letters
    remaining = st.session_state.remaining_attempts
    target = st.session_state.target_word

    all_letters = set("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
    pool_size = len(all_letters - guessed)

    if pool_size == 0:
        # All letters guessed; already handled by check_win_loss
        return 1.0

    candidates = get_candidate_words()

    # If the word is AI-generated it won't appear in WORD_LIST, so
    # candidates may be empty. Fall back to the actual target word.
    if not candidates:
        needed = len(set(target) - guessed)
        return _hypergeometric_prob(needed, pool_size, remaining)

    total_prob = 0.0
    for word in candidates:
        needed = len(set(word) - guessed)
        total_prob += _hypergeometric_prob(needed, pool_size, remaining)

    return total_prob / len(candidates)


def _log_comb(n, k):
    """Log of C(n, k) using math.lgamma for numerical stability."""
    if k < 0 or k > n:
        return float("-inf")
    return math.lgamma(n + 1) - math.lgamma(k + 1) - math.lgamma(n - k + 1)


# OpenAI: Hints & Post-Game Analysis

def get_ai_hint(api_key: str):
    """Ask OpenAI for a cryptic hint about the target word."""
    guessed = st.session_state.guessed_letters
    target = st.session_state.target_word
    revealed = " ".join(ch if ch in guessed else "_" for ch in target)
    incorrect = sorted(l for l in guessed if l not in target)

    prompt = (
        f"We are playing Hangman. The secret word has {len(target)} letters.\n"
        f"Revealed so far: {revealed}\n"
        f"Incorrect guesses: {', '.join(incorrect) if incorrect else 'none'}\n"
        f"Remaining attempts: {st.session_state.remaining_attempts}\n\n"
        "Give the player a short, cryptic hint (one sentence) that nudges them "
        "toward the answer WITHOUT revealing the word itself or any of its "
        "un-guessed letters directly."
    )

    system_msg = (
        f'You are a helpful hangman hint-giver. The secret word is "{target}". '
        "Give a creative, cryptic hint that helps the player guess the word. "
        "NEVER say the word directly or spell out its un-guessed letters. "
        "Each hint should be unique and different from previous hints."
    )

    try:
        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_msg},
                {"role": "user", "content": prompt},
            ],
            max_tokens=80,
            temperature=1.0,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"⚠️ Error getting hint: {e}"


def get_post_game_analysis(api_key: str):
    """Ask OpenAI for a post-game analysis."""
    target = st.session_state.target_word
    guessed = st.session_state.guessed_letters
    result = st.session_state.game_result
    max_att = st.session_state.max_attempts
    remaining = st.session_state.remaining_attempts
    incorrect = sorted(l for l in guessed if l not in target)
    correct = sorted(l for l in guessed if l in target)

    prompt = (
        f"The hangman game just ended. Here are the details:\n"
        f"- Secret word: {target}\n"
        f"- Result: {'WIN' if result == 'win' else 'LOSS'}\n"
        f"- Difficulty: {st.session_state.get('difficulty', 'Medium 🟡')}\n"
        f"- Max attempts: {max_att}\n"
        f"- Wrong guesses used: {max_att - remaining}\n"
        f"- Correct guesses: {', '.join(correct) if correct else 'none'}\n"
        f"- Incorrect guesses: {', '.join(incorrect) if incorrect else 'none'}\n\n"
        "Please provide:\n"
        "1. **Word Insight**: A brief definition and use it in a sentence\n"
        "2. **Strategy Review**: A short analysis of the player's guessing strategy "
        "(what went well, what could improve)\n"
        "3. **Fun Fact**: One interesting/fun fact related to the word\n\n"
        "Keep the total response under 150 words. Use markdown formatting."
    )

    try:
        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a friendly hangman game analyst. Be concise and encouraging."},
                {"role": "user", "content": prompt},
            ],
            max_tokens=250,
            temperature=0.8,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"⚠️ Error getting analysis: {e}"


# Main Streamlit App

def main():
    st.set_page_config(page_title="AI Hangman", page_icon="🤖", layout="wide")

    st.title("🤖 AI-Powered Hangman")
    st.markdown("Guess the hidden word — with AI hints, live win probability & more!")

    # Initialize
    init_stats()
    if "target_word" not in st.session_state:
        init_game()

    # Resolve API key: user key overrides env, env can be temporarily disabled
    env_key = os.environ.get("OPENAI_API_KEY", "")
    env_disabled = st.session_state.get("env_key_disabled", False)
    user_key = st.session_state.get("user_api_key", "")
    if user_key:
        api_key = user_key
    elif env_key and not env_disabled:
        api_key = env_key
    else:
        api_key = ""

    # Show a stylish banner when no API key is set
    if not api_key:
        st.markdown("""
        <div style="
            padding: 14px 20px; border-radius: 10px;
            background: linear-gradient(135deg, rgba(99,102,241,0.12), rgba(168,85,247,0.12));
            border: 1px solid rgba(139,92,246,0.3);
            margin-bottom: 16px; text-align: center;
        ">
            <span style="font-size: 15px;">
                🔑 <strong>Enter your OpenAI API key</strong> in the sidebar to unlock
                <strong>AI-generated words</strong>, <strong>smart hints</strong>, and
                <strong>post-game analysis</strong>!
            </span>
        </div>
        """, unsafe_allow_html=True)

    # Sidebar (compact)
    with st.sidebar:

        # Difficulty + New Game
        current_diff = st.session_state.get("difficulty", "Medium 🟡")
        difficulty = st.selectbox(
            "Difficulty",
            list(DIFFICULTY_CONFIG.keys()),
            index=list(DIFFICULTY_CONFIG.keys()).index(current_diff),
            key="difficulty_radio",
            help="Changes take effect on New Game",
        )
        config = DIFFICULTY_CONFIG[difficulty]
        if difficulty != st.session_state.get("difficulty"):
            st.session_state.difficulty = difficulty

        if st.button("🔄 New Game", use_container_width=True):
            st.session_state.difficulty = difficulty
            init_game()
            st.rerun()

        st.divider()

        # Attempts + Probability (compact)
        max_att = st.session_state.get("max_attempts", 6)
        st.write(f"**Attempts:** {st.session_state.remaining_attempts} / {max_att}")
        if st.session_state.get("word_source"):
            st.caption(f"Word source: {st.session_state.word_source}")

        prob = calculate_win_probability()
        prob_pct = prob * 100

        if prob_pct >= 70:
            bar_color = "#28a745"
        elif prob_pct >= 40:
            bar_color = "#ffa500"
        else:
            bar_color = "#dc3545"

        st.markdown(f"""
        <style>
            .stProgress > div > div > div > div {{
                background-color: {bar_color} !important;
            }}
        </style>
        """, unsafe_allow_html=True)
        st.progress(prob, text=f"🎯 Win: {prob_pct:.0f}%")

        st.divider()

        # API Key (compact)
        if api_key:
            source = "environment" if (env_key and not env_disabled and not user_key) else "manual"
            st.markdown(f"**🔑** ✅ Connected ({source})")
            if st.button("🗑 Remove Key", use_container_width=True):
                st.session_state.user_api_key = ""
                st.session_state.env_key_disabled = True
                st.rerun()
        else:
            st.markdown("**🔑 OpenAI API Key**")
            st.caption(
                "Get a key at [platform.openai.com/api-keys](https://platform.openai.com/api-keys)"
            )
            key_input = st.text_input(
                "API Key", type="password", placeholder="sk-...",
                label_visibility="collapsed", key="api_key_input",
            )
            if st.button("Enter Key", use_container_width=True):
                if key_input:
                    st.session_state.user_api_key = key_input
                    st.session_state.env_key_disabled = False
                    st.rerun()
                else:
                    st.toast("Please paste a key first")

            if env_key and env_disabled:
                if st.button("🔁 Use env key", use_container_width=True):
                    st.session_state.env_key_disabled = False
                    st.rerun()

    # Main Display: two-column layout
    max_att = st.session_state.get("max_attempts", 6)
    wrong_guesses = max_att - st.session_state.remaining_attempts

    col_hangman, col_game = st.columns([1, 1], gap="large")

    with col_hangman:
        components.html(
            get_hangman_svg(wrong_guesses, max_att),
            height=240,
        )

        incorrect_letters = sorted(
            l for l in st.session_state.guessed_letters
            if l not in st.session_state.target_word
        )
        if incorrect_letters:
            st.markdown("**Incorrect Guesses:** " + ", ".join(incorrect_letters))

    with col_game:
        display_word = " ".join(
            letter if letter in st.session_state.guessed_letters else "_"
            for letter in st.session_state.target_word
        )
        st.markdown(
            f"<h2 style='text-align:center; letter-spacing:5px; font-family:monospace;'>"
            f"{display_word}</h2>",
            unsafe_allow_html=True,
        )

        if st.session_state.feedback:
            if "Correct" in st.session_state.feedback or "won" in st.session_state.feedback:
                st.success(st.session_state.feedback)
            elif "Sorry" in st.session_state.feedback or "Game Over" in st.session_state.feedback:
                st.error(st.session_state.feedback)
            else:
                st.info(st.session_state.feedback)

        if not st.session_state.game_over:
            with st.form(key="guess_form", clear_on_submit=True):
                col1, col2 = st.columns([3, 1])
                with col1:
                    guess_input = st.text_input(
                        "Enter a letter:", max_chars=1, key="input_letter"
                    )
                with col2:
                    st.write("")
                    st.write("")
                    submit_button = st.form_submit_button(label="Guess")

                if submit_button and guess_input:
                    if guess_input.isalpha():
                        check_guess(guess_input)
                        st.rerun()
                    else:
                        st.warning("Please enter a valid letter.")

            if api_key:
                if st.button("🤖 Get AI Hint"):
                    with st.spinner("Thinking..."):
                        st.session_state.ai_hint = get_ai_hint(api_key)

                if st.session_state.get("ai_hint"):
                    st.info(f"💡 **AI Hint:** {st.session_state.ai_hint}")

        else:
            if st.session_state.game_result == "win":
                if not st.session_state.get("balloons_shown"):
                    st.balloons()
                    st.session_state.balloons_shown = True
                st.markdown("### 🎉 Amazing! You guessed the word!")
            else:
                if not st.session_state.get("snow_shown"):
                    st.snow()
                    st.session_state.snow_shown = True
                st.markdown(
                    f"### 😔 Better luck next time! The word was **{st.session_state.target_word}**."
                )

            if api_key:
                if not st.session_state.get("post_game_analysis"):
                    with st.spinner("🧠 Generating post-game analysis..."):
                        st.session_state.post_game_analysis = get_post_game_analysis(api_key)

                if st.session_state.post_game_analysis:
                    with st.expander("🧠 Post-Game AI Analysis", expanded=True):
                        st.markdown(st.session_state.post_game_analysis)

            if st.button("🔄 Play Again", use_container_width=True):
                init_game()
                st.rerun()

    # Score & Streak (compact row below the game)
    st.divider()
    s1, s2, s3, s4 = st.columns(4)
    streak = st.session_state.current_streak
    best = st.session_state.best_streak
    streak_emoji = "🔥" if streak >= 3 else "⚡" if streak >= 1 else ""
    s1.metric("Wins", st.session_state.wins)
    s2.metric("Losses", st.session_state.losses)
    s3.metric(f"Streak {streak_emoji}", streak)
    s4.metric("Best 👑", best)


if __name__ == "__main__":
    main()
