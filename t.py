"""
Quarto

0: vacant
1-16: occupied
"""
import numpy as np
from collections import Counter

def board_to_int(board):
    s = 0L
    for i in range(16):
        s += long(board[i]) * (17 ** i)
    return s

def board_to_possible_hands(board):
    return [i for i in range(16) if board[i] == 0]

def init_board():
    return np.zeros(16, dtype=np.int)

def init_Q():
    from scipy.sparse import dok_matrix
    return dok_matrix((17 ** 16, 16 * 16))

LINES = [
    [0, 1, 2, 3], [4, 5, 6, 7], [8, 9, 10, 11], [12, 13, 14, 15],
    [0, 4, 8, 12], [1, 5, 9, 13], [2, 6, 10, 14], [3, 7, 11, 15],
    [0, 5, 10, 15], [3, 6, 9, 12]
]
def is_win(board):
    for line in LINES:
        xs = board[line]
        if any(x == 0 for x in xs): continue
        a, b, c, d = xs - 1
        if a & b & c & d != 0:
            return 1
        if a | b | c | d != 15:
            return 1
    return 0

def print_board(board):
    """
    >>> print_board(range(16))
    . o x o | . o o x | . o o o | . o o o
    x o x o | x o o x | o x x x | o o o o
    x o x o | x o o x | x o o o | o x x x
    x o x o | x o o x | o x x x | x x x x
    """
    m = np.zeros((16, 4), dtype=np.int)
    for i in range(16):
        if board[i] == 0:
            m[i, :] = 0
        else:
            v = board[i] - 1
            for bit in range(4):  #  nth bit
                m[i, bit] = ((v >> bit) & 1) + 1

    for y in range(4):
        print ' | '.join(
            ' '.join(
                ['.ox'[v] for v in m[y * 4 : (y + 1) * 4, bit]]
            )
        for bit in range(4))
    print


def policy_random(env):
    from random import choice
    position = choice(board_to_possible_hands(env.board))
    piece = choice(env.available_pieces)
    return (position, piece)


class Environment(object):
    def __init__(self, policy=policy_random):
        self.op_policy = policy
        self.result_log =[]
        self.init_env()

    def init_env(self):
        self.board = init_board()
        self.available_pieces= range(2, 17)
        self.selected_piece = 1

    def _update(self, action, k=1, to_print=False):
        position, piece = action

        if self.board[position] != 0:
            # illegal move
            print 'illegal pos'
            self.init_env()
            self.result_log.append(-1 * k)
            return (self.board, -1 * k)

        if piece not in self.available_pieces:
            # illegal move
            print 'illegal piece'
            self.init_env()
            self.result_log.append(-1 * k)
            return (self.board, -1 * k)

        self.board[position] = self.selected_piece
        self.available_pieces.remove(piece)
        self.selected_piece = piece

        if to_print:
            print k, action
            print_board(self.board)

        b = is_win(self.board)
        if b:
            self.init_env()
            self.result_log.append(+1 * k)
            return (self.board, +1 * k)

        if not self.available_pieces:
            # put selected piece
            self.board[self.board==0] = self.selected_piece
            b = is_win(self.board)
            if to_print:
                print 'last move'
                print_board(self.board)

            self.init_env()
            if b:
                # opponent win
                self.result_log.append(-1 * k)
                return (self.board, -1 * k)
            else:
                # tie
                self.result_log.append(0)
                return (self.board, -1)

        return None

    def __call__(self, action, to_print=False):
        ret = self._update(action, k=1, to_print=to_print)
        if ret: return ret
        op_action = self.op_policy(self)
        ret = self._update(op_action, k=-1, to_print=to_print)
        if ret: return ret
        return (self.board, 0)


def play(policy1, policy2=policy_random, to_print=False):
    env = Environment()
    result = 0

    for i in range(9):
        a = policy1(env)
        s, r = env(a, to_print=to_print)
        if r != 0: break
    if to_print:
        print env.result_log[-1]
    return env.result_log[-1]

#play(policy_random, to_print=True)


class Greedy(object):
    def __init__(self):
        self.Qtable = init_Q()

    def __call__(self, env):
        from random import choice
        s = board_to_int(env.board)
        actions = (action_to_int((pos, piece))
            for pos in board_to_possible_hands(env.board)
            for piece in env.available_pieces
        )
        qa = [(self.Qtable[s, a], a) for a in actions]
        bestQ, bestA = max(qa)
        bextQ, bestA = choice([(q, a) for (q, a) in qa if q == bestQ])
        return int_to_action(bestA)


class EpsilonGreedy(object):
    def __init__(self, eps=0.1):
        self.Qtable = init_Q()
        self.eps = eps

    def __call__(self, env):
        from random import choice, random
        s = board_to_int(env.board)
        if random() < self.eps:
            pos = choice(board_to_possible_hands(env.board))
            piece = choice(env.available_pieces)
            return (pos, piece)

        actions = (action_to_int((pos, piece))
            for pos in board_to_possible_hands(env.board)
            for piece in env.available_pieces
        )
        qa = [(self.Qtable[s, a], a) for a in actions]
        bestQ, bestA = max(qa)
        bextQ, bestA = choice([(q, a) for (q, a) in qa if q == bestQ])
        return int_to_action(bestA)


def board_to_state(board):
    return board_to_int(board)

def action_to_int(action):
    pos, piece = action
    return pos * 16 + (piece - 1)

def int_to_action(i):
    assert 0 <= i < 16 * 16
    return (i / 16, i % 16 + 1)


from kagura.utils import Digest
digest = Digest(1)
battle_per_seconds = []

def sarsa(alpha, policyClass=Greedy):
    global environment, policy
    gamma = 0.9
    num_result = batch_width * num_batch
    environment = Environment()
    policy = policyClass()

    action = policy(environment)
    state = board_to_state(environment.board)
    while True:
        next_board, reward = environment(action)
        next_state = board_to_state(next_board)

        # determine a'
        next_action = policy(environment)
        nextQ = policy.Qtable[next_state, action_to_int(next_action)]

        # update Q(s, a)
        s_a = (state, action_to_int(action))
        Qsa = policy.Qtable[s_a]
        estimated_reward = reward + gamma * nextQ
        diff = estimated_reward - Qsa
        policy.Qtable[s_a] += alpha * diff

        state = next_state
        action = next_action
        if len(environment.result_log) == num_result:
            break
        t = digest.digest(len(environment.result_log))
        if t:
            battle_per_seconds.append(t)

    vs = []
    for i in range(num_batch):
        c = Counter(environment.result_log[batch_width * i : batch_width * (i + 1)])
        print c
        vs.append(float(c[1]) / batch_width)
    return vs


def qlearn(alpha, policyClass=Greedy):
    global environment, policy
    gamma = 0.9
    num_result = batch_width * num_batch
    environment = Environment()
    policy = policyClass()

    state = board_to_state(environment.board)
    while True:
        action = policy(environment)
        next_board, reward = environment(action)
        next_state = board_to_state(next_board)

        # update Q(s, a)
        maxQ = max(policy.Qtable[next_state, a] for a in board_to_possible_hands(next_board))
        s_a = (state, action_to_int(action))

        Qsa = policy.Qtable[s_a]
        estimated_reward = reward + gamma * maxQ
        diff = estimated_reward - Qsa
        policy.Qtable[s_a] += alpha * diff

        state = next_state

        if len(environment.result_log) == num_result:
            break
        t = digest.digest(len(environment.result_log))
        if t:
            battle_per_seconds.append(t)

    vs = []
    for i in range(num_batch):
        c = Counter(environment.result_log[batch_width * i : batch_width * (i + 1)])
        print c
        vs.append(float(c[1]) / batch_width)
    return vs



def plot_log():
    from kagura import load
    result_log = load("sarsa_0.05_result_log")
    batch_width = 1000
    num_batch = 1000
    vs = []
    for i in range(num_batch):
        c = Counter(result_log[batch_width * i : batch_width * (i + 1)])
        print c
        vs.append(float(c[1]) / batch_width)

    label = 'Sarsa(0.05)'
    imgname = 'sarsa_0.05.png'
    plot()

def plot():
    import matplotlib.pyplot as plt
    plt.clf()
    plt.plot([0.475] * len(vs), label = "baseline")
    plt.plot(vs, label=label)
    plt.xlabel("iteration")
    plt.ylabel("Prob. of win")
    plt.legend(loc = 4)
    plt.savefig(imgname)


def f(n, m):
    if m == 1: return n + 1
    return n * f(n - 1, m - 1) + f(n, m - 1)


if not'ex1':
    from collections import Counter
    print Counter(
        play(policy_random) for i in range(10000))
elif not'ex2':
    batch_width = 1000
    num_batch = 100
    vs = sarsa(0.5)
elif not'ex3':
    batch_width = 1000
    num_batch = 1000
    vs = sarsa(0.5)

if 0:
    batch_width = 1000
    num_batch = 1000
    vs = qlearn(0.5)
    label = 'Qlearn(0.5)'
    imgname = 'qlearn.png'
elif 0:
    batch_width = 1000
    num_batch = 1000
    vs = qlearn(0.05)
    label = 'Qlearn(0.05)'
    imgname = 'qlearn_0.05.png'


from kagura import dump
if 0:
    batch_width = 1000
    num_batch = 1000
    vs = sarsa(0.5, policyClass=EpsilonGreedy)
    label = 'Sarsa(0.5, eps=0.1)'
    imgname = 'sarsa_0.5_eps0.1.png'
    dump(environment.result_log, imgname.replace('.png', '_result_log'))
elif 0:
    batch_width = 1000
    num_batch = 1000
    vs = sarsa(0.05, policyClass=EpsilonGreedy)
    label = 'Sarsa(0.05, eps=0.1)'
    imgname = 'sarsa_0.05_eps0.1.png'
    dump(environment.result_log, imgname.replace('.png', '_result_log'))

if 0:
    batch_width = 100
    num_batch = 1000
    vs = sarsa(0.05, policyClass=Greedy)
    label = 'Sarsa(0.05)'
    imgname = 'sarsa_0.05_2.png'
    dump(environment.result_log, imgname.replace('.png', '_result_log'))


batch_width = 1000
num_batch = 100
vs = sarsa(0.5)
label = 'Sarsa(0.5)'
imgname = 'sarsa_0.5_2.png'

plot()

