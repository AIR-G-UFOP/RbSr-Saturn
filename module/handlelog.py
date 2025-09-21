from module.core import *


class HandleLog:
    def __init__(self):
        super(HandleLog, self).__init__()

        self.log_file = None
        self.names_log = {}  # {'position_run': 'name'}
        self.name_links = {}    # {'unique_name_file': 'laser_log_name'}

    def open_log_file(self, path):
        extention = os.path.splitext(os.path.basename(path))[1]
        if extention == '.csv':
            self.log_file = pd.read_csv(path, sep=",")
            return True
        else:
            return False

    def get_names_from_log(self):
        sequence = [int(x) for x in self.log_file[' Sequence Number'].to_list() if not pd.isna(x)]
        names = [x for x in self.log_file[' Comment'].to_list() if not pd.isna(x)]
        self.names_log = dict(zip(sequence, names))

    def link_unique_name_with_log(self, run_names):
        for unique_name in run_names:
            position = int(unique_name.split(' #')[0])
            self.name_links[unique_name] = self.names_log[position]
