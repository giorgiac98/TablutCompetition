from multiprocessing import Queue, Process, cpu_count
import numpy as np

import pytablut.config as cfg
import pytablut.loggers as lg
from pytablut.game import State


class Node:

    def __init__(self, state):
        """
        each node of represents a state
        :param state: state
        """
        self.state: State = state
        self.id: int = hash(state)
        self.edges: list = []

    def __eq__(self, other):
        return self.id == other.id

    def __ne__(self, other):
        return self.id != other.id

    def __str__(self):
        return f'ID: {self.id}\n' + '\n'.join([f'{edge}' for edge in self.edges])

    def __format__(self, format_spec):
        return self.__str__()

    def is_leaf(self) -> bool:
        return len(self.edges) == 0


class Edge:

    def __init__(self, in_node: Node, out_node: Node, action):
        """
        each edge represents an action from a state to another
        :param in_node: node of the initial state
        :param out_node: node of the next state
        :param action: the action
        """
        self.in_node: Node = in_node
        self.out_node: Node = out_node
        self.action: tuple = action
        self.N = 0  # number of times action has been taken from initial state
        self.W = 0.  # total value of next state
        self.Q = 0.  # mean value of next state

    def __str__(self):
        return f'{self.action}: N = {self.N:0>3d}, W = {self.W:>5.0f}, Q = {self.Q:>6.2f}'

    def __format__(self, format_spec):
        return self.__str__()


class MCTS:

    def __init__(self, player, root: Node, c_puct: float = cfg.CPUCT):
        self.player = player
        self.root: Node = root
        self.c_puct = c_puct
        self.new_root(self.root)

    def _delete_subtree(self, edge):
        node = edge.out_node
        del edge.out_node
        del edge.in_node
        del edge
        for out_edge in node.edges:
            self._delete_subtree(out_edge)
        del node.edges
        del node

    def delete_tree(self):
        for edge in self.root.edges:
            self._delete_subtree(edge)
        del self.root.edges
        self.root = None

    def new_root(self, node: Node):
        if self.root != node:
            tmp = self.root
            self.root = node
            for edge in [edge for edge in tmp.edges if edge.out_node != self.root]:
                self._delete_subtree(edge)
            del tmp.edges
        if self.root.is_leaf():
            self.expand_leaf(self.root)
        any_terminal = np.argwhere([edge.out_node.state.is_terminal for edge in self.root.edges])
        if np.any(any_terminal):
            return self.root.edges[any_terminal[0, 0]].action
        else:
            return None

    def select_leaf(self) -> (Node, list):
        lg.logger_mcts.info('SELECTING LEAF')
        node = self.root
        path = []

        while not node.is_leaf():
            max_QU = -np.inf
            Np = np.sum([edge.N for edge in node.edges])
            simulation_edge = None
            lg.logger_mcts.debug('PLAYER TURN {}'.format(node.state.turn))

            for i, edge in enumerate(node.edges):
                if edge.N == 0:
                    U = np.inf
                else:
                    U = self.c_puct * np.sqrt(np.log(Np) / edge.N)

                QU = edge.Q + U
                if QU > max_QU and edge not in path:
                    lg.logger_mcts.debug('UPDATING SIMULATION EDGE')
                    max_QU = QU
                    simulation_edge = edge

            node = simulation_edge.out_node
            path.append(simulation_edge)

        return node, path

    def expand_leaf(self, leaf: Node) -> bool:
        lg.logger_mcts.info('EXPANDING LEAF WITH ID {}'.format(leaf.id))
        found_terminal = False
        for action in leaf.state.actions:
            next_state = leaf.state.transition_function(action)
            new_leaf = Node(next_state)
            new_edge = Edge(leaf, new_leaf, action)
            leaf.edges.append(new_edge)
            if next_state.is_terminal:
                found_terminal = True
        return found_terminal

    def random_playout(self, leaf: Node, turn: int):
        lg.logger_mcts.info('PERFORMING RANDOM PLAYOUT')
        processes = []
        results = []
        q = Queue()
        current_state = leaf.state
        for i in range(cpu_count()):
            p = Process(target=self.__parallel_playout, args=(current_state, turn, q))
            processes.append(p)
            p.start()
        for _ in processes:
            r = q.get()
            results.append(r)
        for p in processes:
            p.join()

        final_v = 0
        n = 0
        sum_len_paths = 0
        for v, path in results:
            sum_len_paths += len(path)
            final_v += v
            n += np.abs(v)
        return final_v, n, sum_len_paths/len(processes)

    def __parallel_playout(self, current_state, turn, return_queue):
        rng = np.random.default_rng()
        path = []
        v = 1
        while not current_state.is_terminal:
            if turn > 2:
                next_states = ([current_state.transition_function(act) for act in current_state.actions])
                any_terminal = np.argwhere([state.is_terminal for state in next_states])
                if np.any(any_terminal):
                    act_idx = any_terminal[0, 0]
                    v = any_terminal.shape[0]
                else:
                    act_idx = rng.choice(list(range(len(current_state.actions))))
                path.append(current_state.actions[act_idx])
                current_state = next_states[act_idx]
            else:
                act_idx = rng.choice(list(range(len(current_state.actions))))
                path.append(current_state.actions[act_idx])
                current_state = current_state.transition_function(current_state.actions[act_idx])

        if current_state.turn != self.player:
            return_queue.put((v, path))
        else:
            return_queue.put((-v, path))

    def backpropagation(self, v, n, path: list):
        lg.logger_mcts.info('PERFORMING BACKPROPAGATION')
        direction = 1
        for edge in path:
            edge.N += n
            edge.W += v * direction
            direction *= -1
            edge.Q = edge.W / edge.N
            lg.logger_mcts.info('Act = {}, N = {}, W = {}, Q = {}'.format(edge.action, edge.N, edge.W, edge.Q))

    def swap_values(self):
        """ changes stats from white to black """
        def aux(node):
            for edge in node.edges:
                if edge.N > 0:
                    edge.W = edge.N - edge.W
                    edge.Q = edge.W / edge.N
        aux(self.root)

    def cut_tree(self, cutoff: int):
        """ deletes all nodes in the tree below a certain depth """
        def aux(node, depth):
            if depth <= 0:
                # delete all descendant of this node
                for edge in node.edges:
                    self._delete_subtree(edge)
                node.edges = []
            else:
                # this node and his children get to live
                for edge in node.edges:
                    aux(edge.out_node, depth - 1)
        aux(self.root, cutoff)
