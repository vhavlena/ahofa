#!/usr/bin/env python3

import re
from collections import defaultdict

class Nfa:

    RE_transition_FA_format = re.compile('^\w+\s+\w+\s+\w+$')
    RE_state_FA_format = re.compile('^\w+$')

    def __init__(self):
        self._transitions = dict(defaultdict(set))
        self._initial_state = None
        self._final_states = set()

    ###########################################################################
    # PROPERTIES
    ###########################################################################

    @property
    def state_count(self):
        return len(self._transitions)

    @property
    def states(self):
        yield from self._transitions.keys()

    @property
    def pred(self):
        pred = {s:set() for s in self._transitions}

        for state, rules in self._transitions.items():
            for key, value in rules.items():
                for q in value:
                    pred[q].add(state)

        return pred

    @property
    def succ(self):
        succ = {s:set() for s in self._transitions}

        for state, rules in self._transitions.items():
            for key, value in rules.items():
                for q in value:
                    succ[state].add(q)

        return succ

    @property
    def state_depth(self):
        succ = self.succ
        sdepth = {state:0 for state in self.states}
        actual = set([self._initial_state])
        empty = set()
        depth = 0
        while True:
            empty = empty.union(actual)
            new = set()
            for q in actual:
                sdepth[q] = depth
                new = new.union(succ[q])
            new -= empty
            actual = new
            if not new:
                break
            depth += 1
        return sdepth

    ###########################################################################
    # NFA SETTER METHODS
    ###########################################################################

    def _add_state(self,state):
        if not state in self._transitions:
            self._transitions[state] = (defaultdict(set))

    def _add_rule(self, pstate, qstate, symbol):
        self._add_state(pstate)
        self._add_state(qstate)
        if 0 <= symbol <= 255:
            self._transitions[pstate][symbol].add(qstate)
        else:
            raise RuntimeError('Invalid rule format')

    def _add_initial_state(self, istate):
        self._add_state(istate)
        self._initial_state = istate

    def _add_final_state(self, fstate):
        self._add_state(fstate)
        self._final_states.add(fstate)

    ###########################################################################
    # NFA MANUPULATION
    ###########################################################################

    def selfloop_to_finals(self):
        for state in self._final_states:
            for c in range(256):
                self._transitions[state][c] = set([state])


    def remove_states(self, state_set):
        assert(not self._initial_state in state_set)
        for state, rules in self._transitions.copy().items():
            if state in state_set:
                del self._transitions[state]
            else:
                for symbol, states in rules.items():
                    self._transitions[state][symbol] = states - state_set

        self._final_states -= state_set

    def _has_path_over_alph(self, state1, state2):
        alph = [1 for x in range(256)]
        for key, val in self._transitions[state1].items():
            if state2 in val:
                alph[key] = 0
            else:
                return False

        return not sum(alph)

    def lightweight_minimization(self, collapse_finals=True):
        '''
        TODO Add comment.
        '''
        to_remove = set()
        succ = self.succ
        pred = self.pred
        for s in self.succ[self._initial_state]:
            if self._has_path_over_alph(self._initial_state, s) and \
               self._has_path_over_alph(s, s):
                to_remove.add(s)

        if to_remove:
            state = to_remove.pop()
        # remove states & add transitions
        for s in to_remove:
            for p in pred[s]:
                for key, val in self._transitions[p].items():
                    val.discard(s)

            for key, val in self._transitions[s].items():
                for x in val:
                    self._add_rule(state, x, key)

        # merge all final states to one
        if collapse_finals:
            self.collapse_final_states()

        return self.remove_unreachable()

    def collapse_final_states(self):
        self.prune(self._final_states.copy())

    def clear_final_state_transitions(self):
        for fstate in self._final_states:
            self._transitions[fstate] = (defaultdict(set))

    def remove_unreachable(self):
        succ = self.succ
        actual = set([self._initial_state])
        reached = set()
        while actual:
            reached = reached.union(actual)
            new = set()
            for q in actual:
                new = new.union(succ[q])
            actual = new - reached

        self.remove_states(set([s for s in self.states if s not in reached]))

    def prune(self, to_prune):
        final_state_label = max(self.states) + 1
        self._add_final_state(final_state_label)

        for state in to_prune | self._final_states.copy():
            self.merge_states(final_state_label, state)

        self.clear_final_state_transitions()


    def merge_states(self, pstate, qstate):
        if pstate == qstate:
            return
        # redirect all rules with qstate on left side to pstate
        for symbol, states in self._transitions[qstate].items():
            for s in states:
                self._transitions[pstate][symbol].add(s)

        # redirect all rules with qstate on right side to pstate
        pred = self.pred[qstate]
        for state in pred:
            for symbol, states in self._transitions[state].items():
                if qstate in states:
                    self._transitions[state][symbol].discard(qstate)
                    self._transitions[state][symbol].add(pstate)

        # check if collapsed state is final one
        if qstate in self._final_states:
            self._final_states.discard(qstate)
            self._final_states.add(pstate)

        # remove state
        del self._transitions[qstate]



    ###########################################################################
    # LANGUAGE OPERATIONS
    ###########################################################################

    def forward_language_equivalence(self, state1, state2, n):

        if n == 0:
            return True

        # same symbols
        if len(self._transitions[state1]) != len(self._transitions[state2]):
            return False

        for symbol, states in self._transitions[state1]:
            if symbol in self._transitions[state2]:
                for p1 in states:
                    ret = False
                    for p2 in self._transitions[state2][symbol]:
                        if forward_language_equivavelnce(p1, p2, n - 1):
                            ret = True
                            break
                    if ret == False:
                        return False
            else:
                return False

        return True

    def forward_language_equivalence_groups(self, n):
        eq_groups = {}
        for p1 in range(self.state_count):
            eq_groups[p1] = set([p1])
            for p2 in range(p1, self.state_count):
                if (forward_language_equivalence(self, p1, p2, n)):
                    eq_groups[p1].add(p2)

        return eq_groups

    ###########################################################################
    # IO METHODS
    ###########################################################################

    @classmethod
    def parse_fa(cls, fname):
        out = Nfa()
        with open(fname, 'r') as f:
            out.read_fa(f)

        return out

    def read_fa(self, f):
        rules = 0
        for line in f:
            # erase new line at the end of the string
            if line[-1] == '\n':
                line = line[:-1]

            if rules == 0:
                # read initial state
                if Nfa.RE_state_FA_format.match(line):
                    self._add_initial_state(int(line))
                    rules = 1
                else:
                    raise RuntimeError('invalid syntax: \"' + line + '\"')
            elif rules == 1:
                # read transitions
                if Nfa.RE_transition_FA_format.match(line):
                    p, q, a = line.split()
                    p = int(p)
                    q = int(q)
                    a = int(a,0)
                    self._add_rule(p,q,a)
                elif Nfa.RE_state_FA_format.match(line):
                    self._add_final_state(int(line))
                    rules = 2
                else:
                    raise RuntimeError('invalid syntax: \"' + line + '\"')
            else:
                if Nfa.RE_state_FA_format.match(line):
                    self._add_final_state(int(line))
                else:
                    raise RuntimeError('invalid syntax: \"' + line + '\"')

    @classmethod
    def ba_to_fa(cls, data):
        for line in data:
            if ',' in line:
                a,s1,s2 = re.split('(?:,|->)\s*', line[:-1])
                yield s1[1:-1] + ' ' + s2[1:-1] + ' ' + a + '\n'
            else:
                yield line[1:-2] + '\n'

    @classmethod
    def fa_to_ba(cls, data):
        for line in data:
            if ' ' in line:
                s1, s2, a = line.split()
                yield a + ',[' + s1 + ']' + '->[' + s2 + ']\n'
            else:
                yield '[' + line[:-1] + ']\n'

    def write_fa(self):
        yield str(self._initial_state) + '\n'
        for state, rules in self._transitions.items():
            for key, value in rules.items():
                for q in value:
                    yield '{} {} {}\n'.format(state, q, hex(key))
        for qf in self._final_states:
            yield '{}\n'.format(qf)

    def print_fa(self, f=None):
        for line in self.write_fa():
            print(line, end='', file=f)

    def write_dot(self):
        yield 'digraph NFA {\n \
        rankdir=LR;size="8,5"\n \
        graph [ dpi = 400 ]\n \
        node [shape = doublecircle];'
        yield ';'.join(['q' + str(qf) for qf in self._final_states]) + '\n'

        yield 'node [shape = point]; qi\n \
        node [shape = circle];\n'
        yield 'qi -> q' + str(self._initial_state) + ';\n'

        succ = self.succ
        for state in self.states:
            for s in succ[state]:
                yield ' '.join(('q' + str(state), '->', 'q' + str(s), ';\n'))

        yield '}\n'

    def print_dot(self, f=None):
        for line in self.write_dot():
            print(line, end='', file=f)