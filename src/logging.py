import time

class Logger:
    def __init__(self, log_file = './logging.log'):
        print("Creating Logger")
        self.format = '{time} {level}| {message}'
        self.log_file = log_file

    def get_message_object(self, *args, level = 'INFO'):
        return {
            'time': time.strftime('%Y-%m-%d %H:%M:%S', time.localtime()),
            'level': level,
            'message': ' '.join([str(arg) for arg in args])
        }

    def output(self, message: str, level: str):
        message = message.encode('utf-8', errors='replace').decode('utf-8')
        try:
            print(message)
        except UnicodeEncodeError:
            print('Error encoding message')
        try:
            with open(self.log_file, 'a') as f:
                f.write(message + '\n')
        except Exception as e:
            print(f'Error writing to log file: {e}')
            # raise e

    def info(self, *args):
        message = self.get_message_object(*args, level='INFO')
        self.output(self.format.format(**message), 'INFO')

    def error(self, *args):
        message = self.get_message_object(*args, level='ERROR')
        self.output(self.format.format(**message), 'ERROR')

    def warning(self, *args):
        message = self.get_message_object(*args, level='WARNING')
        self.output(self.format.format(**message), 'WARNING')

    def warn(self, *args):
        self.warning(*args)

    def debug(self, *args):
        message = self.get_message_object(*args, level='DEBUG')
        self.output(self.format.format(**message), 'DEBUG')

logging = Logger() # Create a logger object to be used throughout the program