class InitTracker:
    def __init__(self, creature_dict):
        names_in_order = sorted(creature_dict, key=creature_dict.__getitem__, reverse=True)
        self.initiative = {}
        self.conditions = {}
        self.index = 0

        for i, name in enumerate(names_in_order):
            self.initiative[i + 1] = name
            self.conditions[i + 1] = []

    def get_players(self):
        string = ''
        for key in self.initiative.keys():
            string += '%s: %s\n' % (key, self.initiative[key])
        return string

    def add_cond(self, creature, creator , length, description):
        self.conditions[creature].append({'len': length, 'desc': description, 'creator': creator})
        return 'Added %s to %s for %s rounds.' % (description, self.initiative[creature], length)

    def remove_cond(self, creature, cond):
        string = 'Removed %s from %s!' % (self.conditions[creature][cond - 1]['desc'], self.initiative[creature])
        self.conditions[creature].pop(cond - 1)
        return string

    def __call__(self):
        self.index += 1
        if self.index > len(self.initiative):
            self.index = 1

        string = 'It is %s\'s turn to move.' % self.initiative[self.index]
        if len(self.conditions[self.index]) > 0:
            string += '\nCurrent Conds:\n'

        for cond in self.conditions[self.index]:
            string += '\t%s | %s | %s' % (cond['len'], cond['desc'], self.initiative[cond['creator']])

        for i, creature in self.conditions.items():
            for cond in creature:
                if cond['creator'] == self.index:
                    cond['len'] -= 1
                    if cond['len'] <= 0:
                        string += '\n%s\'s %s has expired!' % (self.initiative[i], cond['desc'])
                    else:
                        string += '\n%s rounds left on %s\'s %s.' % (cond['len'], self.initiative[i], cond['desc'])

        if string[-1] != '\n':
            string += '\n'
        return string
