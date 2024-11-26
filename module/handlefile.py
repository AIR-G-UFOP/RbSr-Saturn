from module.core import *


class HandleFiles:
    def __init__(self, datapath, batchlog):
        super(HandleFiles, self).__init__()

        self.datapath = datapath
        self.file_start_index = None
        self.file_end_index = None
        self.data_head = None
        self.alldatafiles = {}
        self.logfile = None
        self.batchlog = batchlog

    def open_datafiles(self):
        self.alldatafiles = {}
        for n, data_path in enumerate(self.datapath):
            run_name = os.path.basename(data_path)
            name_without_extention = os.path.splitext(run_name)[0]

            raw_file = []
            with open(data_path) as data:
                for line in data:
                    line_stripped = line.strip()
                    line_splitted = line_stripped.split(sep=',')
                    raw_file.append(line_splitted)
                if n == 0:
                    for j, line in enumerate(raw_file):
                        for i, item in enumerate(line):
                            if item == 'Time [Sec]':
                                self.file_start_index = j
                                self.data_head = self.head_masses(line)
                            if i == 0:
                                try:
                                    float(item)
                                    self.file_end_index = j - self.file_start_index
                                except:
                                    pass
                filedata = pd.read_csv(data_path, header=self.file_start_index)
                filedata.columns = self.data_head
                filedata = filedata.iloc[:self.file_end_index,:]
                filedata = filedata.astype(float)
                filedata.replace(0, 1, inplace=True)

            self.alldatafiles[name_without_extention] = filedata

    def head_masses(self, masses):
        head = []
        for i, mass in enumerate(masses):
            if i != 0:
                match = re.match(r'([a-zA-Z]+)(\d+) -> (\d+)', mass)
                new = mass
                if match:
                    element, mass1, mass2 = match.groups()
                    if mass1 == mass2:
                        new = element + mass1
                    else:
                        new = element + mass2
                head.append(new)
            else:
                head.append(mass)

        return head

