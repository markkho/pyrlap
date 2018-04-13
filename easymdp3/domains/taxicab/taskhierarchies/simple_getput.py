from easymdp3.core.hierarchicalrl import AbstractMachine, \
    HierarchyOfAbstractMachines
from easymdp3.domains.taxicab import TaxiCabMDP


class Root(AbstractMachine):
    def call(self, s, stack):
        return [
            ('get', (('passenger_i', 0),)),
            ('get', (('passenger_i', 1),)),
            ('put', ())
        ]

class Get(AbstractMachine):
    def is_terminal(self, s, stack, passenger_i, *args, **kwargs):
        if s.taxi.passenger_i == passenger_i:
            return True
        if s.taxi.passenger_i != -1:
            return True
        return False

    def call(self, s, stack, passenger_i):
        passenger = s.passengers[passenger_i]
        return [
            ('pickup', ()),
            ('navigate', (('dest', passenger.location),))
        ]

class Put(AbstractMachine):
    def is_terminal(self, s, stack, *args, **kwargs):
        if s.taxi.passenger_i == -1:
            return True
        return False

    def call(self, s, stack):
        passenger_i = s.taxi.passenger_i
        p = s.passengers[passenger_i]
        return [
            ('dropoff', ()),
            ('navigate', (('dest', p.destination),))
        ]

class Navigate(AbstractMachine):
    def is_terminal(self, s, stack, dest, *args, **kwargs):
        if s.taxi.location == dest:
            return True
        return False

    def call(self, s, stack, dest):
        return [
            ('v', ()),
            ('^', ()),
            ('<', ()),
            ('>', ())
        ]

taxicab = TaxiCabMDP(
    width=3, height=3, walls=[],
    locations = [(0, 0), (1, 2)],
    init_passengers = [
        {'location': (1, 2), 'destination': (0, 0), 'i': 0},
        {'location': (0, 0), 'destination': (1, 2), 'i': 1},
    ],
    init_location=(0, 2)
)

simple_getput = HierarchyOfAbstractMachines(
    mdp=taxicab,
    abstract_machines={
        'root': Root,
        'get': Get,
        'put': Put,
        'navigate': Navigate
    }
)