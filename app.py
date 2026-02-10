import streamlit as st
import random

# Constants & Config
WORD_LIST = [
    "APPLE", "BREAD", "CHAIR", "DANCE", "EARTH",
    "FLAME", "GRAPE", "HOUSE", "JUICE", "LIGHT",
    "MONEY", "MUSIC", "OCEAN", "PARTY", "QUEEN",
    "SMILE", "STONE", "TIGER", "TRAIN", "WATER"
]

MAX_ATTEMPTS = 6

# Simple ASCII art for Hangman stages
HANGMAN_PICS = [
    """
       +---+
       |   |
           |
           |
           |
           |
    =========
    """,
    """
       +---+
       |   |
       O   |
           |
           |
           |
    =========
    """,
    """
       +---+
       |   |
       O   |
       |   |
           |
           |
    =========
    """,
    """
       +---+
       |   |
       O   |
      /|   |
           |
           |
    =========
    """,
    """
       +---+
       |   |
       O   |
      /|\\  |
           |
           |
    =========
    """,
    """
       +---+
       |   |
       O   |
      /|\\  |
      /    |
           |
    =========
    """,
    """
       +---+
       |   |
       O   |
      /|\\  |
      / \\  |
           |
    =========
    """
]

# Helper Functions

def init_game():
    """Initializes or resets the game state."""
    st.session_state.target_word = random.choice(WORD_LIST)
    st.session_state.guessed_letters = set()
    st.session_state.remaining_attempts = MAX_ATTEMPTS
    st.session_state.game_over = False
    st.session_state.game_result = "" # 'win' or 'loss'
    st.session_state.feedback = "Game started! Guess a letter."

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

    check_win_loss()

def check_win_loss():
    """Checks if the game has ended."""
    word_set = set(st.session_state.target_word)
    
    # Check Win
    if word_set.issubset(st.session_state.guessed_letters):
        st.session_state.game_over = True
        st.session_state.game_result = "win"
        st.session_state.feedback = "Congratulations! You won!"
    
    # Check Loss
    elif st.session_state.remaining_attempts == 0:
        st.session_state.game_over = True
        st.session_state.game_result = "loss"
        st.session_state.feedback = f"Game Over! The word was: {st.session_state.target_word}"

# Main App Interface

def main():
    st.set_page_config(page_title="Streamlit Hangman", page_icon="🎮")
    
    st.title("🎮 Classic Hangman")
    st.markdown("Guess the hidden word letter by letter.")

    # Initialize session state if first run
    if 'target_word' not in st.session_state:
        init_game()

    # Sidebar (Game Info)
    with st.sidebar:
        st.header("Game Status")
        if st.button("New Game"):
            init_game()
            st.rerun()
        
        st.write(f"**Attempts Remaining:** {st.session_state.remaining_attempts}")

    # Main Display Area

    # Display Hangman ASCII Art (centered)
    wrong_guesses = MAX_ATTEMPTS - st.session_state.remaining_attempts
    col_left, col_center, col_right = st.columns([1, 2, 1])
    with col_center:
        st.code(HANGMAN_PICS[wrong_guesses], language=None)
    
    # Display the Word
    display_word = " ".join(
        [letter if letter in st.session_state.guessed_letters else "_" 
         for letter in st.session_state.target_word]
    )
    
    st.markdown(
        f"<h1 style='text-align: center; letter-spacing: 5px; font-family: monospace;'>{display_word}</h1>", 
        unsafe_allow_html=True
    )
    

    # Feedback Message
    if st.session_state.feedback:
        if "Correct" in st.session_state.feedback or "won" in st.session_state.feedback:
            st.success(st.session_state.feedback)
        elif "Sorry" in st.session_state.feedback or "Game Over" in st.session_state.feedback:
            st.error(st.session_state.feedback)
        else:
            st.info(st.session_state.feedback)

    # Input Section
    if not st.session_state.game_over:
        with st.form(key='guess_form', clear_on_submit=True):
            col1, col2 = st.columns([3, 1])
            with col1:
                guess_input = st.text_input(
                    "Enter a letter:", 
                    max_chars=1, 
                    key="input_letter"
                )
            with col2:
                # Vertical alignment spacer
                st.write("") 
                st.write("")
                submit_button = st.form_submit_button(label='Guess')

            if submit_button and guess_input:
                if guess_input.isalpha():
                    check_guess(guess_input)
                    st.rerun()
                else:
                    st.warning("Please enter a valid letter.")
    else:
        # Game Over Restart Option
        if st.session_state.game_result == "win":
            st.balloons()
            st.markdown("### 🎉 Amazing! You guessed the word!")
            st.markdown("**Would you like to play again?**")
        else:
            st.markdown(f"### 😔 Better luck next time! The word was **{st.session_state.target_word}**.")
            st.markdown("**Would you like to try again?**")
        
        if st.button("🔄 Play Again"):
            init_game()
            st.rerun()

    # Incorrect Guesses Display
    incorrect_letters = sorted(
        [l for l in st.session_state.guessed_letters if l not in st.session_state.target_word]
    )
    if incorrect_letters:
        st.markdown("**Incorrect Guesses:** " + ", ".join(incorrect_letters))

    # Debug/Cheat Area (Optional)
    # st.caption(f"Debug: The word is {st.session_state.target_word}")

if __name__ == "__main__":
    main()