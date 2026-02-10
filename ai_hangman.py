import streamlit as st
import random
import os
import math
from openai import OpenAI

# ─────────────────────────────────────────────
# Constants & Config (mirrored from app.py)
# ─────────────────────────────────────────────

WORD_LIST = [
    "APPLE", "BREAD", "CHAIR", "DANCE", "EARTH",
    "FLAME", "GRAPE", "HOUSE", "JUICE", "LIGHT",
    "MONEY", "MUSIC", "OCEAN", "PARTY", "QUEEN",
    "SMILE", "STONE", "TIGER", "TRAIN", "WATER"
]


MAX_ATTEMPTS = 6

HANGMAN_PICS = [
    """
       +---+
       |   |
           |
           |
           |
           |
    =========""",
    """
       +---+
       |   |
       O   |
           |
           |
           |
    =========""",
    """
       +---+
       |   |
       O   |
       |   |
           |
           |
    =========""",
    """
       +---+
       |   |
       O   |
      /|   |
           |
           |
    =========""",
    """
       +---+
       |   |
       O   |
      /|\\  |
           |
           |
    =========""",
    """
       +---+
       |   |
       O   |
      /|\\  |
      /    |
           |
    =========""",
    """
       +---+
       |   |
       O   |
      /|\\  |
      / \\  |
           |
    ========="""
]

# ─────────────────────────────────────────────
# Game Logic
# ─────────────────────────────────────────────

def generate_word_from_ai():
    """Ask OpenAI to generate a random 5-letter word."""
    api_key = os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        return None
    try:
        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a word generator for a hangman game."},
                {"role": "user", "content": (
                    "Generate exactly ONE random common English word that is exactly 5 letters long. "
                    "Reply with ONLY the word in uppercase, nothing else. No punctuation, no explanation."
                )},
            ],
            max_tokens=10,
            temperature=1.2,
        )
        word = response.choices[0].message.content.strip().upper()
        # Validate: must be exactly 5 alphabetic characters
        if len(word) == 5 and word.isalpha():
            return word
        return None
    except Exception:
        return None


def init_game():
    """Initializes or resets the game state."""
    ai_word = generate_word_from_ai()
    # if ai_word:
    #     st.session_state.target_word = ai_word
    #     st.session_state.word_source = "🤖 AI-generated"
    # else:
    st.session_state.target_word = random.choice(WORD_LIST)
    st.session_state.word_source = "📋 Word list"
    st.session_state.guessed_letters = set()
    st.session_state.remaining_attempts = MAX_ATTEMPTS
    st.session_state.game_over = False
    st.session_state.game_result = ""
    st.session_state.feedback = "Game started! Guess a letter."
    st.session_state.ai_hint = ""


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

    # Clear previous hint after a new guess
    st.session_state.ai_hint = ""
    check_win_loss()


def check_win_loss():
    """Checks if the game has ended."""
    word_set = set(st.session_state.target_word)

    if word_set.issubset(st.session_state.guessed_letters):
        st.session_state.game_over = True
        st.session_state.game_result = "win"
        st.session_state.feedback = "Congratulations! You won!"

    elif st.session_state.remaining_attempts == 0:
        st.session_state.game_over = True
        st.session_state.game_result = "loss"
        st.session_state.feedback = f"Game Over! The word was: {st.session_state.target_word}"


# ─────────────────────────────────────────────
# Win Probability Calculation
# ─────────────────────────────────────────────

def get_candidate_words():
    """Return words from WORD_LIST that still match the current game state."""
    guessed = st.session_state.guessed_letters
    target = st.session_state.target_word
    incorrect = {l for l in guessed if l not in target}

    # Build the revealed pattern  e.g. "A _ _ L E"
    pattern = [
        letter if letter in guessed else None
        for letter in target
    ]

    candidates = []
    for word in WORD_LIST:
        if len(word) != len(target):
            continue
        # Word must not contain any incorrectly guessed letters
        if any(ch in incorrect for ch in word):
            continue
        # Word must match revealed positions
        match = True
        for i, p in enumerate(pattern):
            if p is not None and word[i] != p:
                match = False
                break
            if p is None and word[i] in guessed:
                # If position is hidden but the letter was guessed, it means
                # this letter shouldn't appear here for the target, but the
                # candidate has it → mismatch only if the letter IS in guessed
                # and IS correct (already handled above). Actually if p is None
                # the letter at that position in target wasn't guessed, but if
                # the candidate has a guessed letter there, the candidate would
                # have revealed it, so it's a mismatch.
                match = False
                break
        if match:
            candidates.append(word)
    return candidates


def calculate_win_probability():
    """
    Estimate probability of winning from the current state.

    Uses a combinatorial approach:
    - For each candidate word, compute the probability of guessing
      all its remaining unique letters within the remaining attempts,
      assuming random letter picks from the un-guessed alphabet.
    - Average across all candidate words (each equally likely).
    """
    if st.session_state.game_over:
        return 1.0 if st.session_state.game_result == "win" else 0.0

    candidates = get_candidate_words()
    if not candidates:
        return 0.0

    guessed = st.session_state.guessed_letters
    remaining = st.session_state.remaining_attempts

    # Letters that haven't been guessed yet (the "pool" we pick from)
    all_letters = set("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
    pool_size = len(all_letters - guessed)  # unguessed letters in alphabet

    if pool_size == 0:
        return 1.0

    total_prob = 0.0
    for word in candidates:
        needed = len(set(word) - guessed)  # correct letters still needed
        if needed == 0:
            total_prob += 1.0
            continue

        wrong_in_pool = pool_size - needed  # wrong letters in the pool

        # We can tolerate at most (remaining - needed) wrong picks
        max_wrong = remaining - needed
        if max_wrong < 0:
            # Not enough attempts to even guess all needed letters
            total_prob += 0.0
            continue

        # P(win) = C(wrong_in_pool, <=max_wrong) * C(needed, needed)
        #          choosing (needed + w) letters from pool, where w <= max_wrong
        #          and all 'needed' correct letters are among them.
        #
        # = sum_{w=0}^{max_wrong} C(wrong_in_pool, w) / C(pool_size, needed + w)
        #   (order matters for the sequence of picks, but the ratio is the same)
        #
        # Hypergeometric: pick (needed + w) items from pool of pool_size
        # containing 'needed' good and 'wrong_in_pool' bad.
        # P(all good picked) = C(needed,needed)*C(wrong_in_pool,w) / C(pool_size, needed+w)

        p_word = 0.0
        for w in range(max_wrong + 1):
            draws = needed + w
            if draws > pool_size:
                break
            # Use log to avoid overflow with large factorials
            log_p = (
                _log_comb(wrong_in_pool, w)
                + _log_comb(needed, needed)
                - _log_comb(pool_size, draws)
            )
            p_word += math.exp(log_p)

        total_prob += min(p_word, 1.0)

    return total_prob / len(candidates)


def _log_comb(n, k):
    """Log of C(n, k) using math.lgamma for numerical stability."""
    if k < 0 or k > n:
        return float("-inf")
    return math.lgamma(n + 1) - math.lgamma(k + 1) - math.lgamma(n - k + 1)


# ─────────────────────────────────────────────
# OpenAI Hint
# ─────────────────────────────────────────────

def get_ai_hint(api_key: str):
    """Ask OpenAI for a cryptic hint about the target word."""
    guessed = st.session_state.guessed_letters
    target = st.session_state.target_word
    revealed = " ".join(
        ch if ch in guessed else "_" for ch in target
    )
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
        f"You are a helpful hangman hint-giver. The secret word is \"{target}\". "
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


# ─────────────────────────────────────────────
# Main Streamlit App
# ─────────────────────────────────────────────

def main():
    st.set_page_config(page_title="AI Hangman", page_icon="🤖")

    st.title("🤖 AI-Powered Hangman")
    st.markdown("Guess the hidden word — with AI hints and live win probability!")

    # Initialize session state
    if "target_word" not in st.session_state:
        init_game()

    # Read API key from environment
    api_key = os.environ.get("OPENAI_API_KEY", "")

    # ── Sidebar ──────────────────────────────
    with st.sidebar:

        st.divider()
        st.header("📊 Game Status")

        if st.button("🔄 New Game"):
            init_game()
            st.rerun()

        st.write(f"**Attempts Remaining:** {st.session_state.remaining_attempts}")

        # ── Win Probability ──────────────────
        prob = calculate_win_probability()
        prob_pct = prob * 100

        st.divider()
        st.subheader("🎯 Win Probability")

        # Dynamic color based on probability
        if prob_pct >= 70:
            bar_color = "#28a745"  # green
            bg_color = "rgba(40, 167, 69, 0.15)"
            border_color = "rgba(40, 167, 69, 0.4)"
            label = f"Looking good! {prob_pct:.0f}% chance to win"
        elif prob_pct >= 40:
            bar_color = "#ffa500"  # orange
            bg_color = "rgba(255, 165, 0, 0.15)"
            border_color = "rgba(255, 165, 0, 0.4)"
            label = f"It's getting tricky — {prob_pct:.0f}%"
        elif prob_pct > 0:
            bar_color = "#dc3545"  # red
            bg_color = "rgba(220, 53, 69, 0.15)"
            border_color = "rgba(220, 53, 69, 0.4)"
            label = f"Danger zone! Only {prob_pct:.0f}%"
        else:
            bar_color = "#dc3545"
            bg_color = "rgba(220, 53, 69, 0.15)"
            border_color = "rgba(220, 53, 69, 0.4)"
            label = "Very low chance — good luck!" if not st.session_state.game_over else "Game over"

        # Inject CSS to override the progress bar color
        st.markdown(f"""
        <style>
            .stProgress > div > div > div > div {{
                background-color: {bar_color} !important;
            }}
        </style>
        """, unsafe_allow_html=True)

        st.progress(prob, text=f"{prob_pct:.0f}%")

        # Colored message box
        st.markdown(f"""
        <div style="
            padding: 12px 16px;
            border-radius: 8px;
            background-color: {bg_color};
            border: 1px solid {border_color};
            color: {bar_color};
            font-weight: 600;
            font-size: 14px;
            margin-top: 4px;
        ">{label}</div>
        """, unsafe_allow_html=True)

    # ── Main Display ─────────────────────────
    wrong_guesses = MAX_ATTEMPTS - st.session_state.remaining_attempts
    col_left, col_center, col_right = st.columns([1, 2, 1])
    with col_center:
        st.code(HANGMAN_PICS[wrong_guesses], language=None)

    # Display the word
    display_word = " ".join(
        letter if letter in st.session_state.guessed_letters else "_"
        for letter in st.session_state.target_word
    )
    st.markdown(
        f"<h1 style='text-align:center; letter-spacing:5px; font-family:monospace;'>{display_word}</h1>",
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

    # ── Input / Game Over ────────────────────
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

        # ── AI Hint Button ───────────────────
        st.divider()
        hint_col1, hint_col2 = st.columns([1, 3])
        with hint_col1:
            hint_disabled = not bool(api_key)
            if st.button("🤖 Get AI Hint", disabled=hint_disabled):
                with st.spinner("Thinking..."):
                    st.session_state.ai_hint = get_ai_hint(api_key)

        if not api_key:
            with hint_col2:
                st.caption("⚠️ Set OPENAI_API_KEY env variable to enable AI hints")

        if st.session_state.get("ai_hint"):
            st.info(f"💡 **AI Hint:** {st.session_state.ai_hint}")

    else:
        if st.session_state.game_result == "win":
            st.balloons()
            st.markdown("### 🎉 Amazing! You guessed the word!")
        else:
            st.markdown(
                f"### 😔 Better luck next time! The word was **{st.session_state.target_word}**."
            )
        st.markdown("**Would you like to play again?**")
        if st.button("🔄 Play Again"):
            init_game()
            st.rerun()

    # Incorrect guesses
    incorrect_letters = sorted(
        l for l in st.session_state.guessed_letters
        if l not in st.session_state.target_word
    )
    if incorrect_letters:
        st.markdown("**Incorrect Guesses:** " + ", ".join(incorrect_letters))


if __name__ == "__main__":
    main()
