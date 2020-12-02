import multiprocessing
import pickle
import time

import numpy as np

import pytablut.config as cfg
import pytablut.loggers as lg
from pytablut.MCTS import MCTS, Node
from pytablut.game import MAP
# from pytablut.neuralnet import ResidualNN
from pytablut.utils import Timeit


class Player:

    def __init__(self, color, name, nnet_ver=None, timeout=cfg.TIMEOUT,
                 turns_before_tau0=cfg.TURNS_BEFORE_TAU0, tau=cfg.TAU, tau_alpha=cfg.TAU_ALPHA,
                 simulations=cfg.MCTS_SIMULATIONS, c_puct=cfg.CPUCT, choice_strategy="max_child"):
        """
        Parameters:
        :param color: color of the player, either BLACK or WHITE
        :param name: name of the player
        :param timeout: timeout in seconds for each move computation
        :param choice_strategy: "max_child", "robust_child", "max_robut_child" or "secure_child"
        """
        self.name = name
        self.color: int = MAP[color]
        self.timeout: int = timeout
        self.mcts: MCTS = None
        if nnet_ver is not None:
            self.brain = ResidualNN()
            if nnet_ver > 0:
                self.brain.load_model(nnet_ver)
        else:
            self.brain = None
        self.simulations: int = simulations
        self.choice_strategy = choice_strategy
        self.c_puct: int = c_puct
        self.turns_before_tau0 = turns_before_tau0
        self.tau = tau
        self.tau_alpha = tau_alpha
        self.turn = 1
        self.__start_time = None

    def __start_timer(self):
        self.__start_time = time.perf_counter()

    def __timeover(self):
        return time.perf_counter() - self.__start_time >= 0.9 * self.timeout

    def reset(self):
        self.turn = 1
        if self.mcts is not None:
            self.mcts.delete_tree()
            self.mcts = None

    def build_mcts(self, state):
        """"""
        lg.logger_player.info("BUILDING MCTS")
        if self.mcts is None:
            if self.turn == 1:
                self.mcts = self.load_history(state)
                if self.color == -1:
                    self.mcts.new_root(Node(state))
                    self.mcts.swap_values()
            if self.mcts is None:  # may still be None if state does not exist in history
                self.mcts = MCTS(self.color, Node(state), self.c_puct)
            win_action = None
        else:
            win_action = self.mcts.new_root(Node(state))
        return win_action

    @Timeit(logger=lg.logger_player)
    def act(self, state):
        """
        computes best action based on given state
        :return tuple (action, pi)
        """
        lg.logger_player.info("COMPUTING ACTION FOR STATE {}".format(state.id))
        # v = self.brain.predict(state)
        win_action = self.build_mcts(state)
        if win_action is not None:
            return win_action
        else:
            self.simulate()
            action = self.choose_action()
            return action

    @Timeit(logger=lg.logger_player)
    def choose_action(self) -> tuple:
        """
        Chooses the best action from the current state,
        either deterministically or stochastically
        :return: tuple (action, pi), pi are normalized probabilities
        """
        if self.choice_strategy == "max_child":
            # select the action with the highest reward
            pi = np.array([edge.Q for edge in self.mcts.root.edges])
            pi += np.abs(np.min(pi)) + 1e-5
        elif self.choice_strategy == "robust_child":
            # select the most visited action
            pi = np.array([edge.N for edge in self.mcts.root.edges])
        elif self.choice_strategy == "max-robust_child":
            # select the action with both the highest visit count and the highest reward;
            # if none exists, then continue searching until an acceptable visit count is achieved
            raise NotImplementedError(f'{self.choice_strategy} strategy not yet implemented')
        elif self.choice_strategy == "secure child":
            # the action which maximizes the lower confidence bound (q + a/sqrt(n))
            raise NotImplementedError(f'{self.choice_strategy} strategy not yet implemented')
        else:
            raise ValueError(f'wrong choice strategy: {self.choice_strategy}')
        if self.turn >= self.turns_before_tau0:
            act_idx = np.argmax(pi)
            action = self.mcts.root.edges[act_idx].action
        else:  # FIXME testare nuove cose
            pvals = pi / np.sum(pi)  # normalization
            act_idx = np.argwhere(np.random.multinomial(1, pvals) == 1).reshape(-1)[0]
            action = self.mcts.root.edges[act_idx].action

        for edge in self.mcts.root.edges:
            lg.logger_player.info(f'ACTION: {edge.action}, N:{edge.N:0>6.0f}, W:{edge.W:0>5.0f}, Q:{edge.Q:0>2.2f}')

        lg.logger_player.info('COMPUTED ACTION: {}'.format(action))
        self.end_turn(self.mcts.root.edges[act_idx].out_node)
        return action

    def simulate(self) -> None:
        """
        Performs the monte carlo simulations, using the neural network to evaluate the leaves
        """
        self.__start_timer()
        simulations = 0
        segment = 6
        K = 1
        while not self.__timeover():
            if simulations >= np.exp2(segment):
                segment += 1
                K = np.exp2(segment - 6)
            # selection
            leaf, path = self.mcts.select_leaf()
            # expansion
            n = 1
            if leaf.state.is_terminal:
                if leaf.state.turn == self.color:
                    v = -1
                else:
                    v = 1
            else:
                found_terminal = self.mcts.expand_leaf(leaf)
                if found_terminal:
                    if leaf.state.turn == self.color:
                        v = 1
                    else:
                        v = -1
                elif self.brain is not None:
                    v = self.brain.predict(leaf.state)
                else:
                    v, n, _ = self.mcts.random_playout(leaf, self.turn)
            # backpropagation
            self.mcts.backpropagation(K * v, K * n, path)
            simulations += multiprocessing.cpu_count()
        lg.logger_player.info('{:3d} SIMULATIONS PERFORMED'.format(simulations))

    @Timeit(logger=lg.logger_player)
    def replay(self, memories) -> None:
        """
        Retrain the network using the given memories
        :param memories: iterable of memories, i.e. objects with attributes 'state', ' value', 'turn'
        """
        lg.logger_player.info('RETRAINING MODEL')

        for i in range(cfg.TRAINING_LOOPS):
            minibatch = np.random.choice(memories, min(cfg.BATCH_SIZE, len(memories)))
            X = np.array([memory['state'].convert_into_cnn() for memory in minibatch])
            y = np.array([memory['value'] for memory in minibatch])

            loss = self.brain.fit(X, y, epochs=cfg.EPOCHS, verbose=cfg.VERBOSE,
                                  validation_split=0, batch_size=minibatch.size)
            lg.logger_nnet.info('ITERATION {:3d}/{:3d}, LOSS {}'.format(i, cfg.TRAINING_LOOPS, loss.history))

    def _update_tau(self):
        self.tau = self.tau * self.tau_alpha

    def load_history(self, state):
        try:
            history = pickle.load(open('model/history/root.pkl', 'rb'))
            lg.logger_player.info('LOADING HISTORY FROM MEMORY')
            return history
        except FileNotFoundError:
            lg.logger_player.info('NO HISTORY FOUND FOR CURRENT STATE')
            return None

    def save_history(self):
        if self.turn == 1:
            self.mcts.cut_tree(2)
            if self.color == 1:
                pickle.dump(self.mcts, open('model/history/root.pkl', 'wb'))
            else:
                state = self.mcts.root.state
                # TODO implement merging and save on same file
                pickle.dump(self.mcts, open(f'model/history/{state.id}.pkl', 'wb'))
        else:
            raise Exception('Wrong level')

    def end_turn(self, node: Node):
        """
        :param node: node of the chosen action
        """

        if self.turn == 1 and self.brain is None:
            self.save_history()
        self.turn += 1
        self.mcts.new_root(node)
        self._update_tau()
