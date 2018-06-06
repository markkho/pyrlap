#!/usr/bin/env python
import copy
from itertools import product
import logging
logger = logging.getLogger(__name__)

import numpy as np

from pyrlap.core.mdp import MDP
from pyrlap.core.reward_function import RewardFunction
from pyrlap.algorithms.valueiteration import ValueIteration
from pyrlap.core.util import sample_prob_dict
class GridWorld(MDP):
    def __init__(self, width=None, height=None,
                 gridworld_array=None,

                 wait_action=False,
                 wall_action=False,
                 state_features=None,
                 absorbing_states=None,

                 slip_states=None,
                 slip_features=None,
                 sticky_states=None,

                 non_std_t_states=None,
                 non_std_t_features=None,

                 walls=None, #[((x, y), side),...]
                 wall_feature=None,

                 starting_states=None,
                 state_rewards=None, #deprecated
                 reward_dict=None,
                 default_reward=0,
                 step_cost=0,
                 feature_rewards=None,
                 include_intermediate_terminal=False,
                 init_state=None,

                 state_types=None,
                 feature_types=None):

        if gridworld_array is not None:
            w = len(gridworld_array[0])
            h = len(gridworld_array)
            state_features = {(x, y): gridworld_array[h - 1 - y][x] for x, y in
                              product(list(range(w)), list(range(h)))}
            width = w
            height = h

        self.width = width
        self.height = height
        self.states = list(product(list(range(width)), list(range(height)))) + [(-1, -1),
                                                                    (-2, -2)]
        self.wait_action = wait_action
        self.wall_action = wall_action
        self.cached_transitions = {}
        self.include_intermediate_terminal = include_intermediate_terminal
        self.intermediate_terminal = (-2, -2)
        self.terminal_state = (-1, -1)

        if absorbing_states is None:
            absorbing_states = []
        absorbing_states = copy.deepcopy(absorbing_states)
        self.absorbing_states = frozenset(absorbing_states)



        if state_features is None:
            state_features = {}
        self.state_features = state_features

        #non-standard transitions
        non_std_t_moves = ['forward', 'back', 'left', 'right',
                           '2forward', '2back', 'horseleft',
                           'horseright', 'diagleft', 'diagright',
                           'stay']
        self.non_std_t_moves = non_std_t_moves
        non_std_t_states = copy.deepcopy(non_std_t_states)

        if non_std_t_states is None:
            non_std_t_states = {}
        if slip_states is not None:
            non_std_t_states.update(slip_states)

        if non_std_t_features is None:
            non_std_t_features = {}
        if slip_features is not None:
            non_std_t_features.update(slip_features)

        if state_types is None:
            state_types = {}

        if feature_types is None:
            feature_types = {}

        # walls
        if walls is None:
            walls = []
        self.walls = walls

        for s in self.states:
            f = state_features.get(s, None)
            if f in non_std_t_features:
                non_std_t_states[s] = non_std_t_features[f]
            if f in feature_types:
                state_types[s] = state_types.get(s, [])
                state_types[s].append(feature_types[f])
            if wall_feature is not None and f == wall_feature:
                self.walls.append(s)

        for s, non_std_t in non_std_t_states.items():
            if 'side' in non_std_t:
                non_std_t['left'] = non_std_t['side'] / 2
                non_std_t['right'] = non_std_t['side'] / 2
                del non_std_t['side']
            if 'horsemove' in non_std_t:
                non_std_t['horseleft'] = non_std_t['horsemove'] / 2
                non_std_t['horseright'] = non_std_t['horsemove'] / 2
                del non_std_t['horsemove']
            if 'diag' in non_std_t:
                non_std_t['diagleft'] = non_std_t['diag'] / 2
                non_std_t['diagright'] = non_std_t['diag'] / 2
                del non_std_t['diag']
            non_std_t = [non_std_t.get(move, 0) for move in non_std_t_moves]
            non_std_t_states[s] = non_std_t
        self.non_std_t_states = non_std_t_states


        self.state_types = state_types





        #initial states
        if starting_states is None:
            starting_states = []
        starting_states = copy.deepcopy(starting_states)

        if init_state is not None:
            starting_states.append(init_state)
        self.starting_states = frozenset(starting_states)

        #reward function stuff
        self.reward_function = RewardFunction(state_features=state_features,
                                              state_rewards=state_rewards,
                                              feature_rewards=feature_rewards,
                                              reward_dict=reward_dict,
                                              default_reward=default_reward,
                                              step_cost=step_cost)

        self.rmax = self.reward_function.rmax
        self.terminal_state_reward = self.reward_function.terminal_state_reward

        self.TERMINAL_ACTION = '%'
        self.ACTION_LIST = [self.TERMINAL_ACTION, '>', '<', 'v', '^']
        if self.wait_action:
            self.ACTION_LIST.append('x')

        self.reward_cache = {}
        self.transition_cache = {}
        self.available_action_cache = {}
        self.solved = False

    def __hash__(self):
        try:
            return self.hash
        except AttributeError:
            pass

        self.hash = hash((
            self.width,
            self.height,
            self.wait_action,
            self.wall_action,
            self.reward_function,
            self.absorbing_states,
            frozenset([(s, nst) for s, nst in self.non_std_t_states.items()]),
            self.starting_states,
            self.include_intermediate_terminal,
            self.intermediate_terminal,
            self.terminal_state
        ))
        return self.hash

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return hash(self) == hash(other)
        return False

    # ============================================== #
    #                                                #
    #                                                #
    #          State/Action Related Methods          #
    #                                                #
    #                                                #
    # ============================================== #

    def is_terminal(self, s):
        return s == self.terminal_state

    def is_terminal_action(self, a):
        return a == self.TERMINAL_ACTION

    def is_any_terminal(self, s):
        return s in [self.terminal_state, self.intermediate_terminal]

    def is_absorbing(self, s):
        return s in self.absorbing_states

    def state_hasher(self, state):
        return state

    def state_unhasher(self, hashed):
        return hashed

    def get_init_state(self):
        if len(self.starting_states) == 0:
            raise ValueError("No initial state defined")
        starting_states = list(self.starting_states)
        i = np.random.choice(len(starting_states))
        return starting_states[i]

    def available_actions(self, s=None):
        if s is None:
            return self.ACTION_LIST
        try:
            return self.available_action_cache[s]
        except KeyError:
            pass
        actions = []

        # handle absorbing, terminal, and intermediate terminal states
        if s in self.absorbing_states:
            actions.append(self.TERMINAL_ACTION)
        elif s == self.terminal_state:
            actions.append(self.TERMINAL_ACTION)
        elif s == self.intermediate_terminal:
            actions.append(self.TERMINAL_ACTION)

        # handle 'normal' transitions with no wall actions
        elif not self.wall_action:
            if s[1] < self.height - 1 and (s, '^') not in self.walls:
                actions.append('^')
            if s[1] > 0 and (s, 'v') not in self.walls:
                actions.append('v')
            if s[0] < self.width - 1 and (s, '>') not in self.walls:
                actions.append('>')
            if s[0] > 0 and (s, '<') not in self.walls:
                actions.append('<')
        elif self.wall_action:
            actions.extend(['^','v','<','>'])

        if self.wait_action:
            actions.append('x')

        self.available_action_cache[s] = actions

        return actions

    def get_state_features(self, s, only_grid_location=False):
        '''returns unordered list of binary features'''
        if self.is_any_terminal(s):
            return ['term%d' % s[0]]
        features = ['x%dy%d' % (s[0], s[1])]
        if not only_grid_location:
            features.extend(self.state_features[s])
        return features

    def get_states(self):
        return self.states

    # ============================================== #
    #                                                #
    #                                                #
    #          Transition Function Methods           #
    #                                                #
    #                                                #
    # ============================================== #

    def _normal_transition(self, s, a):
        """
        "normal" transitions (taking into account walls)
        """

        # handle 1D walls
        if (s, a) in self.walls:
            ns = s

        #handle non-wall transitions
        elif s[1] < self.height - 1 and a == '^':
            ns = s[0], s[1] + 1
        elif s[1] > 0 and a == 'v':
            ns = s[0], s[1] - 1
        elif s[0] < self.width - 1 and a == '>':
            ns = s[0] + 1, s[1]
        elif s[0] > 0 and a == '<':
            ns = s[0] - 1, s[1]
        elif a == 'x':
            ns = s

        #handle default transition
        else:
            ns = s

        #handle 2D walls
        if ns in self.walls:
            ns = s

        return ns

    def _get_side_actions(self, a):
        if a in '^v':
            return ['<', '>']
        elif a in '<>':
            return ['^', 'v']
        else:
            return a

    def _get_back_action(self, a):
        if a == '^':
            a_ = 'v'
        elif a == 'v':
            a_ = '^'
        elif a == '<':
            a_ = '>'
        elif a == '>':
            a_ = '<'
        else:
            a_ = a
        return a_

    def _get_right_action(self, a):
        if a == '>':
            return 'v'
        elif a == 'v':
            return '<'
        elif a == '<':
            return '^'
        elif a == '^':
            return '>'
        else:
            return a

    def _get_left_action(self, a):
        if a == '>':
            return '^'
        elif a == 'v':
            return '>'
        elif a == '<':
            return 'v'
        elif a == '^':
            return '<'
        else:
            return a

    def transition_dist(self, s, a):
        try:
            return self.transition_cache[(s, a)]
        except KeyError:
            pass

        dist = {}

        # handle absorbing, terminal, and intermediate terminal states
        if s in self.absorbing_states:
            if self.include_intermediate_terminal:
                dist = {self.intermediate_terminal : 1}
            else:
                dist = {self.terminal_state : 1}

        elif s == self.terminal_state:
            dist = {self.terminal_state : 1}

        elif s == self.intermediate_terminal:
            dist = {self.terminal_state : 1}

        #non-standard transition states
        elif s in self.non_std_t_states:
            nst = self.non_std_t_states[s]


            for mi, move in enumerate(self.non_std_t_moves):
                p = nst[mi]
                if p == 0:
                    continue

                if move == 'forward':
                    res = self._normal_transition(s, a)
                elif move == 'back':
                    a_ = self._get_back_action(a)
                    res = self._normal_transition(s, a_)
                elif move == 'left':
                    a_ = self._get_left_action(a)
                    res = self._normal_transition(s, a_)
                elif move == 'right':
                    a_ = self._get_right_action(a)
                    res = self._normal_transition(s, a_)
                elif move == '2forward':
                    ns = self._normal_transition(s, a)
                    res = self._normal_transition(ns, a)
                elif move == '2back':
                    a_ = self._get_back_action(a)
                    ns = self._normal_transition(s, a_)
                    res = self._normal_transition(ns, a_)
                elif move == 'horseleft':
                    ns = self._normal_transition(s, a)
                    ns = self._normal_transition(ns, a)
                    a_ = self._get_left_action(a)
                    res = self._normal_transition(ns, a_)
                elif move == 'horseright':
                    ns = self._normal_transition(s, a)
                    ns = self._normal_transition(ns, a)
                    a_ = self._get_right_action(a)
                    res = self._normal_transition(ns, a_)
                elif move == 'diagleft':
                    ns = self._normal_transition(s, a)
                    a_ = self._get_left_action(a)
                    res = self._normal_transition(ns, a_)
                elif move == 'diagright':
                    ns = self._normal_transition(s, a)
                    a_ = self._get_right_action(a)
                    res = self._normal_transition(ns, a_)
                elif move == 'stay':
                    res = s
                dist[res] = dist.get(res, 0)
                dist[res] += p

        # "normal" transitions (taking into account walls)
        else:
            ns = self._normal_transition(s, a)
            dist = {ns :1}

        self.transition_cache[(s, a)] = dist
        return dist

    def transition(self, s, a):
        dist = self.transition_dist(s, a)
        ns, p = list(zip(*list(dist.items())))
        return ns[np.random.choice(len(ns), p=p)]

    def transition_reward(self, s, a):
        return sample_prob_dict(self.transition_reward_dist(s, a))

    def transition_reward_dist(self, s, a):
        tdist = self.transition_dist(s, a)
        r = lambda ns : self.reward(s, a, ns)
        trdist = {(ns, r(ns)): p for ns, p in tdist.items()}
        return trdist

    def gen_transition_dict(self, start_state=None):
        tf = {}
        for s in self.states:
            tf[s] = {}
            for a in self.available_actions(s):
                tf[s][a] = self.transition_dist(s, a)
        return tf

    def expected_transition(self, s, a):
        """Transition assuming no walls or whatever"""
        if a == '^':
            res = s[0], s[1]+1
        elif a == 'v':
            res = s[0], s[1] - 1
        elif a == '>':
            res = s[0] + 1, s[1]
        elif a == '<':
            res = s[0] - 1, s[1]
        else:
            res = s
        return res

    # ============================================== #
    #                                                #
    #                                                #
    #             Reward Function Methods            #
    #                                                #
    #                                                #
    # ============================================== #
    def reward(self, s=None, a=None, ns=None):
        try:
            return self.reward_cache[(s, a, ns)]
        except KeyError:
            pass
        res = self.reward_function.reward(s=s, a=a, ns=ns)
        self.reward_cache[(s, a, ns)] = res
        return res

    def reward_dist(self, s=None, a=None, ns=None):
        return {self.reward(s, a, ns) : 1}

    def get_state_actions(self):
        state_actions = {s: self.available_actions(s) for s in self.states}
        return state_actions

    def get_state_action_nextstates(self):
        state_action_nextstates = {}
        for s in self.states:
            state_action_nextstates[s] = {}
            for a in self.available_actions(s):
                state_action_nextstates[s][a] = \
                    copy.deepcopy(list(self.transition_dist(s, a).keys()))
        return state_action_nextstates

    def get_reward_dict(self,
                        include_actions=False,
                        include_nextstates=False):

        state_actions = self.get_state_actions()
        state_action_nextstates = self.get_state_action_nextstates()

        rf = self.reward_function.gen_reward_dict(
            states=self.states,
            state_actions=state_actions,
            state_action_nextstates=state_action_nextstates,
            tf={},
            include_actions=include_actions,
            include_nextstates=include_nextstates
        )
        return rf

    # ============================================== #
    #                                                #
    #                                                #
    #              Computation Methods               #
    #                                                #
    #                                                #
    # ============================================== #

    def solve(self,
              discount_rate,
              softmax_temp=0.0,
              randchoose=0.0,
              **kwargs):
        planner = ValueIteration(mdp=self,
                                 discount_rate=discount_rate,
                                 softmax_temp=softmax_temp,
                                 randchoose=randchoose,
                                 **kwargs)
        planner.solve()
        return planner

    # ============================================== #
    #                                                #
    #                                                #
    #            Visualization Methods               #
    #                                                #
    #                                                #
    # ============================================== #

    def plot(self, ax=None,
             tile_colors=None,
             feature_colors=None,
             plot_policy=False,
             plot_agent=False,
             annotations=None,
             softmax_temp=0.0,
             discount_rate=.99,
             randchoose=0.0):
        #depends on matplotlib, which not every dist will have
        from pyrlap.domains.gridworld.gridworldvis import visualize_states, \
            visualize_action_values, plot_agent_location, plot_text, \
            visualize_walls

        default_feature_colors = {
            'a': 'orange',
            'b': 'purple',
            'c': 'cyan',
            'x': 'red',
            'p': 'pink',
            '.': 'white',
            'y': 'yellow',
            'g': 'yellow',
            'n': 'white'
        }

        if feature_colors is None:
            feature_colors = default_feature_colors
        else:
            temp_fcolors = copy.deepcopy(default_feature_colors)
            temp_fcolors.update(feature_colors)
            feature_colors = temp_fcolors

        if tile_colors is None:
            tile_colors = {}
        plot_states = []
        for s in self.states:
            if self.is_any_terminal(s):
                continue
            if s in tile_colors:
                continue
            f = self.state_features.get(s, '.')
            tile_colors[s] = feature_colors[f]
            plot_states.append(s)

        ax = visualize_states(ax=ax,
                              states=plot_states,
                              tile_color=tile_colors)

        ax = visualize_walls(ax=ax, walls=self.walls)

        if annotations is not None:
            for annotation_dict in annotations:
                plot_text(axis=ax, **annotation_dict)

        if plot_policy:
            policy = self.solve(discount_rate=discount_rate,
                                softmax_temp=softmax_temp,
                                randchoose=randchoose)
            visualize_action_values(ax=ax,
                                    state_action_values=policy.to_dict())

        if plot_agent:
            agent = plot_agent_location(self.get_init_state(), ax=ax)

        return ax