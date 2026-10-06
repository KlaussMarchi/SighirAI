from utils.functions import sendEvent


class CustomForms:
    options = []

    def set(self, options=[]):
        self.options = []
        
        for i, (value, label) in enumerate(options.items()):
            data = {'id': i+1, 'value': value, 'label': label}
            self.options.append(data)

    def getChoice(self, question, target='value'):
        choice = input(question).strip().replace(' ', '').replace('\t', '')

        if not choice.isnumeric():
            choice = len(self.options) - 1

        choice   = int(choice)
        selected = self.options[-1]

        for option in self.options:
            if option['id'] == choice:
                selected = option

        sendEvent('selecionado', selected['label'], color='orange', end='\n\n')
        return selected[target]

    def get(self, title='selecione uma opção', target='value'):
        question = '\n' + title + ': \n'

        for option in self.options:
            question += f"  [{option['id']}] {option['label']}\n"

        question += '  digite: '
        return self.getChoice(question, target)
    
    def getBool(self, title='deseja continuar?', sep=True):
        question = '\n' if sep else ''
        question += title + '\n'

        for i, option in enumerate(['sim', 'não']):
            question += f"  [{i+1}] {option}\n"
        
        question += '  digite: '
        return input(question).strip() == '1'
