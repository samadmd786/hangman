"""AI-Powered Hangman Game.

A Streamlit-based Hangman game enhanced with OpenAI-powered features
including AI-generated words, smart hints, live win probability, and
post-game analysis.
"""

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
    """Generate an SVG hangman figure with CSS fade-in animations.

    Parameters:
        wrong_guesses (int): Number of incorrect guesses so far.
        max_attempts (int): Maximum allowed wrong guesses for this difficulty.

    Returns:
        str: HTML string containing the SVG hangman figure.
    """
    ratio = wrong_guesses / max_attempts if max_attempts > 0 else 0
    parts_to_show = min(6, int(ratio * 6 + 0.5))

    fade_css = """
    @keyframes fadeIn {
        from { opacity: 0; transform: scale(0.8); }
        to   { opacity: 1; transform: scale(1); }
    }
    .body-part { animation: fadeIn 0.5s ease-out forwards; }
    """

    body_parts = [
        '<circle cx="150" cy="70" r="20" fill="none" stroke="#e74c3c" stroke-width="3" class="body-part"/>',
        '<line x1="150" y1="90" x2="150" y2="140" stroke="#e74c3c" stroke-width="3" class="body-part"/>',
        '<line x1="150" y1="100" x2="120" y2="130" stroke="#e74c3c" stroke-width="3" class="body-part"/>',
        '<line x1="150" y1="100" x2="180" y2="130" stroke="#e74c3c" stroke-width="3" class="body-part"/>',
        '<line x1="150" y1="140" x2="120" y2="175" stroke="#e74c3c" stroke-width="3" class="body-part"/>',
        '<line x1="150" y1="140" x2="180" y2="175" stroke="#e74c3c" stroke-width="3" class="body-part"/>',
    ]

    gallows = """
        <line x1="60" y1="190" x2="200" y2="190" stroke="#8B4513" stroke-width="4"/>
        <line x1="100" y1="190" x2="100" y2="30"  stroke="#8B4513" stroke-width="4"/>
        <line x1="100" y1="30"  x2="150" y2="30"  stroke="#8B4513" stroke-width="4"/>
        <line x1="150" y1="30"  x2="150" y2="50"  stroke="#8B4513" stroke-width="3"/>
        <line x1="100" y1="60"  x2="120" y2="30"  stroke="#8B4513" stroke-width="2"/>
    """

    rope = '<line x1="150" y1="30" x2="150" y2="50" stroke="#DAA520" stroke-width="2"/>'

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
    """Initialize score and streak tracking in session state.

    Parameters:
        None

    Returns:
        None
    """
    if "wins" not in st.session_state:
        st.session_state.wins = 0
        st.session_state.losses = 0
        st.session_state.total_games = 0
        st.session_state.current_streak = 0
        st.session_state.best_streak = 0


def _get_secrets_key():
    """Retrieve the OpenAI API key from st.secrets (if available).

    Returns:
        str: The API key from st.secrets, or an empty string.
    """
    try:
        return st.secrets.get("OPENAI_API_KEY", "")
    except Exception:
        return ""


def generate_word_from_ai(difficulty_key):
    """Ask OpenAI to generate a word matching the given difficulty.

    Parameters:
        difficulty_key (str): One of 'easy', 'medium', or 'hard'.

    Returns:
        str or None: An uppercase word if successful, None otherwise.
    """
    api_key = _get_secrets_key() or os.environ.get("OPENAI_API_KEY", "")
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
    """Initialize or reset the game state for a new round.

    Uses the current difficulty setting to determine word length and
    max attempts. Tries AI word generation first, falls back to the
    built-in word list.

    Parameters:
        None

    Returns:
        None
    """
    init_stats()

    difficulty = st.session_state.get("difficulty", "Medium 🟡")
    config = DIFFICULTY_CONFIG[difficulty]
    diff_key = config["key"]

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
    """Process the player's letter guess and update game state.

    Parameters:
        letter (str): A single alphabetic character guessed by the player.

    Returns:
        None
    """
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
    """Check if the game has ended (win or loss) and update stats.

    Called after each guess to determine if the player has revealed
    all letters (win) or exhausted all attempts (loss).

    Parameters:
        None

    Returns:
        None
    """
    word_set = set(st.session_state.target_word)

    if word_set.issubset(st.session_state.guessed_letters):
        st.session_state.game_over = True
        st.session_state.game_result = "win"
        st.session_state.feedback = "Congratulations! You won!"
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
        st.session_state.losses += 1
        st.session_state.total_games += 1
        st.session_state.current_streak = 0


# Win Probability Calculation

def get_candidate_words():
    """Find words from the built-in list that match the current game state.

    Filters words by length, revealed letters, and incorrect guesses
    to estimate which words the target could be.

    Parameters:
        None

    Returns:
        list[str]: Words from WORD_LIST consistent with current guesses.
    """
    guessed = st.session_state.guessed_letters
    target = st.session_state.target_word
    incorrect = {l for l in guessed if l not in target}

    pattern = [
        letter if letter in guessed else None
        for letter in target
    ]

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


def _log_comb(n, k):
    """Compute log of C(n, k) using lgamma for numerical stability.

    Parameters:
        n (int): Total number of items.
        k (int): Number of items to choose.

    Returns:
        float: Natural log of the binomial coefficient C(n, k).
    """
    if k < 0 or k > n:
        return float("-inf")
    return math.lgamma(n + 1) - math.lgamma(k + 1) - math.lgamma(n - k + 1)


def _hypergeometric_prob(needed, pool_size, remaining):
    """Calculate probability of drawing all needed letters within remaining attempts.

    Uses a hypergeometric model where correct guesses don't cost
    attempts, only wrong guesses decrement the counter.

    Parameters:
        needed (int): Number of distinct un-guessed letters still required.
        pool_size (int): Total un-guessed letters in the alphabet.
        remaining (int): Number of wrong guesses the player can still make.

    Returns:
        float: Probability of winning (0.0 to 1.0).
    """
    if needed == 0:
        return 1.0
    wrong_in_pool = pool_size - needed
    max_wrong = remaining
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
    """Estimate the probability of winning from the current game state.

    Uses a hypergeometric model averaged over candidate words from the
    built-in list. Falls back to the actual target word for AI-generated
    words not present in the list.

    Parameters:
        None

    Returns:
        float: Estimated win probability (0.0 to 1.0).
    """
    if st.session_state.game_over:
        return 1.0 if st.session_state.game_result == "win" else 0.0

    guessed = st.session_state.guessed_letters
    remaining = st.session_state.remaining_attempts
    target = st.session_state.target_word

    all_letters = set("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
    pool_size = len(all_letters - guessed)

    if pool_size == 0:
        return 1.0

    candidates = get_candidate_words()

    if not candidates:
        needed = len(set(target) - guessed)
        return _hypergeometric_prob(needed, pool_size, remaining)

    total_prob = 0.0
    for word in candidates:
        needed = len(set(word) - guessed)
        total_prob += _hypergeometric_prob(needed, pool_size, remaining)

    return total_prob / len(candidates)


# OpenAI: Hints & Post-Game Analysis

def get_ai_hint(api_key):
    """Ask OpenAI for a cryptic hint about the target word.

    Constructs a prompt with the current game state and requests a
    creative, one-sentence hint that doesn't directly reveal the word.

    Parameters:
        api_key (str): OpenAI API key.

    Returns:
        str: A hint string, or an error message if the API call fails.
    """
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


def get_post_game_analysis(api_key):
    """Ask OpenAI for a post-game analysis of the completed round.

    Provides word insight, strategy review, and a fun fact based
    on the game outcome.

    Parameters:
        api_key (str): OpenAI API key.

    Returns:
        str: Markdown-formatted analysis, or an error message on failure.
    """
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


# UI Components

def resolve_api_key():
    """Resolve the active OpenAI API key.

    Priority: manually entered key > st.secrets > environment variable.
    Either automatic source can be temporarily disabled by the user.

    Parameters:
        None

    Returns:
        str: The active API key, or an empty string if none is available.
    """
    default_key = _get_secrets_key() or os.environ.get("OPENAI_API_KEY", "")
    env_disabled = st.session_state.get("env_key_disabled", False)
    user_key = st.session_state.get("user_api_key", "")
    if user_key:
        return user_key
    elif default_key and not env_disabled:
        return default_key
    return ""


def render_api_key_banner(api_key):
    """Display a styled banner prompting the user to enter an API key.

    Only shown when no API key is currently active. The banner uses a
    gradient background to attract attention.

    Parameters:
        api_key (str): The current API key (banner is hidden if non-empty).

    Returns:
        None
    """
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


def render_sidebar(api_key):
    """Render the sidebar with difficulty selector, game status, and API key input.

    Includes difficulty dropdown, new game button, attempts counter,
    win probability bar, and API key management controls.

    Parameters:
        api_key (str): The current API key (determines which key UI to show).

    Returns:
        None
    """
    default_key = _get_secrets_key() or os.environ.get("OPENAI_API_KEY", "")
    env_disabled = st.session_state.get("env_key_disabled", False)
    user_key = st.session_state.get("user_api_key", "")

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

        # Attempts + Probability
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

        # API Key
        if api_key:
            source = "environment" if (default_key and not env_disabled and not user_key) else "manual"
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

            if default_key and env_disabled:
                if st.button("🔁 Use default key", use_container_width=True):
                    st.session_state.env_key_disabled = False
                    st.rerun()


def render_hangman_column(wrong_guesses, max_attempts):
    """Render the hangman SVG figure and list of incorrect guesses.

    Parameters:
        wrong_guesses (int): Number of incorrect guesses so far.
        max_attempts (int): Maximum allowed wrong guesses for this difficulty.

    Returns:
        None
    """
    components.html(
        get_hangman_svg(wrong_guesses, max_attempts),
        height=240,
    )

    incorrect_letters = sorted(
        l for l in st.session_state.guessed_letters
        if l not in st.session_state.target_word
    )
    if incorrect_letters:
        st.markdown("**Incorrect Guesses:** " + ", ".join(incorrect_letters))


def render_game_column(api_key):
    """Render the game interaction column: word display, input, hints, and game-over.

    Shows the partially revealed word, feedback messages, the guess input
    form (or game-over results with post-game AI analysis).

    Parameters:
        api_key (str): OpenAI API key for AI hint and analysis features.

    Returns:
        None
    """
    # Word display
    display_word = " ".join(
        letter if letter in st.session_state.guessed_letters else "_"
        for letter in st.session_state.target_word
    )
    st.markdown(
        f"<h2 style='text-align:center; letter-spacing:5px; font-family:monospace;'>"
        f"{display_word}</h2>",
        unsafe_allow_html=True,
    )

    # Feedback
    if st.session_state.feedback:
        if "Correct" in st.session_state.feedback or "won" in st.session_state.feedback:
            st.success(st.session_state.feedback)
        elif "Sorry" in st.session_state.feedback or "Game Over" in st.session_state.feedback:
            st.error(st.session_state.feedback)
        else:
            st.info(st.session_state.feedback)

    # Active game: input form + AI hint
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

    # Game over: results + post-game analysis
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


def render_score_bar():
    """Render the compact score and streak tracker below the game area.

    Displays wins, losses, current streak, and best streak in a
    four-column metric row.

    Parameters:
        None

    Returns:
        None
    """
    st.divider()
    s1, s2, s3, s4 = st.columns(4)
    streak = st.session_state.current_streak
    best = st.session_state.best_streak
    streak_emoji = "🔥" if streak >= 3 else "⚡" if streak >= 1 else ""
    s1.metric("Wins", st.session_state.wins)
    s2.metric("Losses", st.session_state.losses)
    s3.metric(f"Streak {streak_emoji}", streak)
    s4.metric("Best 👑", best)


# Main Streamlit App

def main():
    """Entry point for the AI Hangman Streamlit application.

    Configures the page, initializes game state, resolves the API key,
    and renders all UI components in a wide two-column layout.

    Parameters:
        None

    Returns:
        None
    """
    st.set_page_config(page_title="AI Hangman", page_icon="🤖", layout="wide")

    st.title("🤖 AI-Powered Hangman")
    st.markdown("Guess the hidden word — with AI hints, live win probability & more!")

    init_stats()
    if "target_word" not in st.session_state:
        init_game()

    api_key = resolve_api_key()
    render_api_key_banner(api_key)
    render_sidebar(api_key)

    # Two-column game layout
    max_att = st.session_state.get("max_attempts", 6)
    wrong_guesses = max_att - st.session_state.remaining_attempts

    col_hangman, col_game = st.columns([1, 1], gap="large")

    with col_hangman:
        render_hangman_column(wrong_guesses, max_att)

    with col_game:
        render_game_column(api_key)

    render_score_bar()


if __name__ == "__main__":
    main()
