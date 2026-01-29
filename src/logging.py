import time
import inspect
import os

bcolors = {
    "WARNING": '\033[93m',
    "ERROR": '\033[91m',
    "OUTPUT": '\033[96m',
    "CONFIG": '\033[0;35m',
    "ENDC": '\033[0m',
    "DEBUG": '\033[92m',
    "SUCCESS": '\033[92m',
}

class Logger:
    def __init__(self, log_file = './logging.log', block_logs_from = []):
        print("Creating Logger")
        self.format = '{time} [{location}] [{level}] {message}'
        self.log_file = log_file
        self.block_logs_from = block_logs_from

    def get_message_object(self, *args, level = 'INFO', filepath = None):
        return {
            'time': time.strftime('%Y-%m-%d %H:%M:%S', time.localtime()),
            'level': level,
            'location': filepath,
            'message': ' '.join([str(arg) for arg in args])
        }

    def _output(self, message: str, level: str):
        message = message.encode('utf-8', errors='replace').decode('utf-8')
        try:
            if level in bcolors:
                print(bcolors[level]+message+bcolors["ENDC"])
            else:
                print(message)
        except UnicodeEncodeError:
            print('Error encoding message')
        try:
            with open(self.log_file, 'a') as f:
                remove_colors = message
                for color in bcolors.values():
                    remove_colors = remove_colors.replace(color, '')
                f.write(remove_colors + '\n')
        except Exception as e:
            print(f'Error writing to log file: {e}')
            # raise e

    def info(self, *args):
        # get the caller's stack frame and extract its file path
        frame_info = inspect.stack()[1]
        filepath = frame_info[1]  # in python 3.5+, you can use frame_info.filename
        del frame_info  # drop the reference to the stack frame to avoid reference cycles

        # make the path absolute (optional)
        filepath = os.path.relpath(filepath)
        if filepath in self.block_logs_from:
            return
        line = inspect.currentframe().f_back.f_lineno
        message = self.get_message_object(*args, level='INFO', filepath=filepath+":"+str(line))
        self._output(self.format.format(**message), 'INFO')

    def output(self, *args):
        # get the caller's stack frame and extract its file path
        frame_info = inspect.stack()[1]
        filepath = frame_info[1]  # in python 3.5+, you can use frame_info.filename
        del frame_info  # drop the reference to the stack frame to avoid reference cycles

        # make the path absolute (optional)
        filepath = os.path.relpath(filepath)
        if filepath in self.block_logs_from:
            return
        line = inspect.currentframe().f_back.f_lineno
        message = self.get_message_object(*args, level='OUTPUT', filepath=filepath+":"+str(line))
        self._output(self.format.format(**message), 'OUTPUT')
        
    def config(self, *args):
        # get the caller's stack frame and extract its file path
        frame_info = inspect.stack()[1]
        filepath = frame_info[1]  # in python 3.5+, you can use frame_info.filename
        del frame_info  # drop the reference to the stack frame to avoid reference cycles

        # make the path absolute (optional)
        filepath = os.path.relpath(filepath)
        if filepath in self.block_logs_from:
            return
        line = inspect.currentframe().f_back.f_lineno
        message = self.get_message_object(*args, level='CONFIG', filepath=filepath+":"+str(line))
        self._output(self.format.format(**message), 'CONFIG')

    def error(self, *args):
        # get the caller's stack frame and extract its file path
        frame_info = inspect.stack()[1]
        filepath = frame_info[1]  # in python 3.5+, you can use frame_info.filename
        del frame_info  # drop the reference to the stack frame to avoid reference cycles

        # make the path absolute (optional)
        filepath = os.path.relpath(filepath)
        if filepath in self.block_logs_from:
            return
        line = inspect.currentframe().f_back.f_lineno
        message = self.get_message_object(*args, level='ERROR', filepath=filepath+":"+str(line))
        # message['message'] += '\n\nStack Trace:\n'+traceback.format_exc()
        self._output(self.format.format(**message), 'ERROR')

    def warning(self, *args):
        # get the caller's stack frame and extract its file path
        frame_info = inspect.stack()[1]
        filepath = frame_info[1]  # in python 3.5+, you can use frame_info.filename
        del frame_info  # drop the reference to the stack frame to avoid reference cycles

        # make the path absolute (optional)
        filepath = os.path.relpath(filepath)
        if filepath in self.block_logs_from:
            return
        line = inspect.currentframe().f_back.f_lineno
        message = self.get_message_object(*args, level='WARNING', filepath=filepath+":"+str(line))
        self._output(self.format.format(**message), 'WARNING')

    def debug(self, *args):
        # get the caller's stack frame and extract its file path
        frame_info = inspect.stack()[1]
        filepath = frame_info[1]  # in python 3.5+, you can use frame_info.filename
        del frame_info  # drop the reference to the stack frame to avoid reference cycles

        # make the path absolute (optional)
        filepath = os.path.relpath(filepath)
        if filepath in self.block_logs_from:
            return
        line = inspect.currentframe().f_back.f_lineno
        message = self.get_message_object(*args, level='DEBUG', filepath=filepath+":"+str(line))
        self._output(self.format.format(**message), 'DEBUG')

    def success(self, *args):
        # get the caller's stack frame and extract its file path
        frame_info = inspect.stack()[1]
        filepath = frame_info[1]  # in python 3.5+, you can use frame_info.filename
        del frame_info  # drop the reference to the stack frame to avoid reference cycles

        # make the path absolute (optional)
        filepath = os.path.relpath(filepath)
        if filepath in self.block_logs_from:
            return
        line = inspect.currentframe().f_back.f_lineno
        message = self.get_message_object(*args, level='SUCCESS', filepath=filepath+":"+str(line))
        self._output(self.format.format(**message), 'SUCCESS')

    def warn(self, *args):
        # get the caller's stack frame and extract its file path
        frame_info = inspect.stack()[1]
        filepath = frame_info[1]  # in python 3.5+, you can use frame_info.filename
        del frame_info  # drop the reference to the stack frame to avoid reference cycles

        # make the path absolute (optional)
        filepath = os.path.relpath(filepath)
        if filepath in self.block_logs_from:
            return
        line = inspect.currentframe().f_back.f_lineno
        message = self.get_message_object(*args, level='WARNING', filepath=filepath+":"+str(line))
        self._output(self.format.format(**message), 'WARNING')
        
    def out(self, *args):
        # get the caller's stack frame and extract its file path
        frame_info = inspect.stack()[1]
        filepath = frame_info[1]  # in python 3.5+, you can use frame_info.filename
        del frame_info  # drop the reference to the stack frame to avoid reference cycles

        # make the path absolute (optional)
        filepath = os.path.relpath(filepath)
        if filepath in self.block_logs_from:
            return
        line = inspect.currentframe().f_back.f_lineno
        message = self.get_message_object(*args, level='OUTPUT', filepath=filepath+":"+str(line))
        self._output(self.format.format(**message), 'OUTPUT')

logging = Logger() # Create a logger object to be used throughout the program

def getLogger(app_name):
    if app_name == 'werkzeug':
        return None
    return logging