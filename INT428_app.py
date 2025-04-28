from flask import Flask, render_template, request, session, redirect, url_for
import random
from functools import wraps

app = Flask(__name__)
app.secret_key = 'INT428_secret_key_2025'

users = {'user': 'user123'}

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

class MemoryGameBot:
    def __init__(self):
        self.bot_name = "GameBot"
        self.score = 0
        self.games_played = 0
        self.current_game = None
        self.game_state = None

    class MemoryMatch:
        def __init__(self):
            self.cards = ['🍎', '🍎', '🍊', '🍊', '🍋', '🍋', '🍇', '🍇', '🍓', '🍓', '🍍', '🍍']
            self.board = []
            self.revealed = []
            self.memory = {}

        def setup(self):
            self.board = self.cards.copy()
            random.shuffle(self.board)
            self.revealed = [False] * len(self.board)
            self.memory.clear()

        def bot_move(self):
            unrevealed = [i for i, rev in enumerate(self.revealed) if not rev]
            if len(unrevealed) < 2:
                return None, "Not enough cards to flip!", False

            for pos1 in unrevealed:
                if pos1 in self.memory:
                    value1 = self.memory[pos1]
                    for pos2 in unrevealed:
                        if pos2 != pos1 and pos2 in self.memory and self.memory[pos2] == value1:
                            self.revealed[pos1] = True
                            self.revealed[pos2] = True
                            return [pos1, pos2], "Match found from memory!", True

            pos1 = random.choice(unrevealed)
            unrevealed.remove(pos1)
            if pos1 in self.memory:
                value1 = self.memory[pos1]
                for pos2 in unrevealed:
                    if pos2 in self.memory and self.memory[pos2] == value1:
                        self.revealed[pos1] = True
                        self.revealed[pos2] = True
                        return [pos1, pos2], "Match found from memory!", True

            pos2 = random.choice(unrevealed)
            self.memory[pos1] = self.board[pos1]
            self.memory[pos2] = self.board[pos2]

            if self.board[pos1] == self.board[pos2]:
                self.revealed[pos1] = True
                self.revealed[pos2] = True
                return [pos1, pos2], "Match found!", True
            return [pos1, pos2], "No match!", False

        def is_complete(self):
            return all(self.revealed)

    class NumberGuess:
        def __init__(self):
            self.target = random.randint(1, 100)
            self.guesses = 0
            self.max_guesses = 10
            self.low = 1
            self.high = 100

        def bot_move(self):
            if self.guesses >= self.max_guesses:
                return None, "Max guesses reached!", False
            guess = (self.low + self.high) // 2
            self.guesses += 1
            if guess < self.target:
                self.low = guess + 1
                return guess, "Too low!", False
            elif guess > self.target:
                self.high = guess - 1
                return guess, "Too high!", False
            return guess, "Correct!", True

    class WordScramble:
        def __init__(self):
            self.words = ['python', 'robot', 'coding', 'game', 'brain']
            self.word = random.choice(self.words)
            self.scrambled = ''.join(random.sample(self.word, len(self.word)))
            self.attempts = 0
            self.max_attempts = 5
            self.past_guesses = set()

        def bot_move(self):
            if self.attempts >= self.max_attempts:
                return None, "Max attempts reached!", False
            guess = ''.join(random.sample(self.scrambled, len(self.scrambled)))
            while guess in self.past_guesses and len(self.past_guesses) < self.max_attempts:
                guess = ''.join(random.sample(self.scrambled, len(self.scrambled)))
            self.past_guesses.add(guess)
            self.attempts += 1
            if guess.lower() == self.word:
                return guess, "Correct!", True
            return guess, "Wrong!", False

bots = {}

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if username in users and users[username] == password:
            session['username'] = username
            bots[username] = MemoryGameBot()
            return redirect(url_for('index'))
        return render_template('INT428_login.html', error="Invalid credentials")
    return render_template('INT428_login.html', error=None)

@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('login'))

@app.route('/')
@login_required
def index():
    username = session['username']
    if username not in bots:
        bots[username] = MemoryGameBot()
    bot = bots[username]
    return render_template('INT428_index.html', score=bot.score, games_played=bot.games_played, username=username)

@app.route('/start_game', methods=['POST'])
@login_required
def start_game():
    bot = bots[session['username']]
    game_type = request.form['game']
    bot.current_game = game_type

    if game_type == 'memory':
        bot.game_state = bot.MemoryMatch()
        bot.game_state.setup()
        board = [(i, bot.game_state.board[i]) for i in range(len(bot.game_state.board))]
        revealed = [i for i, r in enumerate(bot.game_state.revealed) if r]
        game_content = render_template('memory_match_partial.html', board=board, revealed=revealed, temporarily_revealed=[])
        message = 'Memory Match started!'
    elif game_type == 'number':
        bot.game_state = bot.NumberGuess()
        game_content = render_template('number_guess_partial.html', guesses=0, last_guess='', feedback='', target=bot.game_state.target)
        message = 'Number Guess started! Bot will guess the number.'
    elif game_type == 'scramble':
        bot.game_state = bot.WordScramble()
        game_content = render_template('word_scramble_partial.html', attempts=0, scrambled=bot.game_state.scrambled, last_attempt='', feedback='', solution=bot.game_state.word)
        message = f'Word Scramble started! Bot will try to unscramble: {bot.game_state.scrambled}'
    else:
        return "Invalid game!", 400

    return render_template('game_update.html', game_content=game_content, 
                           score=bot.score, games_played=bot.games_played, 
                           message=message, complete='false', match='')

@app.route('/play', methods=['POST'])
@login_required
def play():
    bot = bots[session['username']]
    if not bot.current_game or not bot.game_state:
        return "No game selected!", 400

    if bot.current_game == 'memory':
        flipped, message, match = bot.game_state.bot_move()
        board = [(i, bot.game_state.board[i]) for i in range(len(bot.game_state.board))]
        revealed = [i for i, r in enumerate(bot.game_state.revealed) if r]
        if flipped is None:
            complete = 'true'
            temporarily_revealed = []
            message = "Game over!"
        else:
            temporarily_revealed = flipped if not match else []
            complete = 'true' if bot.game_state.is_complete() else 'false'
        game_content = render_template('memory_match_partial.html', board=board, revealed=revealed, temporarily_revealed=temporarily_revealed)
    elif bot.current_game == 'number':
        guess, message, success = bot.game_state.bot_move()
        complete = 'true' if guess is None or success else 'false'
        game_content = render_template('number_guess_partial.html', guesses=bot.game_state.guesses, last_guess=guess or '', feedback=message, target=bot.game_state.target)
    elif bot.current_game == 'scramble':
        guess, message, success = bot.game_state.bot_move()
        complete = 'true' if guess is None or success else 'false'
        game_content = render_template('word_scramble_partial.html', attempts=bot.game_state.attempts, scrambled=bot.game_state.scrambled, last_attempt=guess or '', feedback=message, solution=bot.game_state.word)

    if complete == 'true':
        bot.games_played += 1

    return render_template('game_update.html', game_content=game_content, 
                           score=bot.score, games_played=bot.games_played, 
                           message=message, complete=complete, 
                           match=str(match).lower() if bot.current_game == 'memory' else '')

if __name__ == '__main__':
    app.run(debug=True)