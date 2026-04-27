from tkinter import Tk, Label, Button, Frame, Toplevel, filedialog, StringVar, Entry

root = Tk()
root.title("Pantella Root - Ignore this window, it's just used for dialogs and will be hidden when not in use")
root.geometry("1x1")
root.withdraw() # hide the root window, we only use it for dialogs


class OptionDialog(Toplevel):
    """
        This dialog accepts a list of options.
        If an option is selected, the results property is to that option value
        If the box is closed, the results property is set to zero
    """
    def __init__(self,parent, title, question, options):
        Toplevel.__init__(self,parent)
        self.title(title)
        self.question = question
        self.transient(parent)
        self.protocol("WM_DELETE_WINDOW",self.cancel)
        self.options = options
        self.result = '_'
        self.createWidgets()
        self.grab_set()
        ## wait.window ensures that calling function waits for the window to
        ## close before the result is returned.
        self.wait_window()
    def createWidgets(self):
        frmQuestion = Frame(self)
        Label(frmQuestion,text=self.question).grid()
        frmQuestion.grid(row=1)
        frmButtons = Frame(self)
        frmButtons.grid(row=2)
        column = 0
        for option in self.options:
            btn = Button(frmButtons,text=option,command=lambda x=option:self.setOption(x))
            btn.grid(column=column,row=0)
            column += 1 
    def setOption(self,optionSelected):
        self.result = optionSelected
        self.destroy()
    def cancel(self):
        self.result = None
        self.destroy()

class FolderSelectionDialog(Toplevel): # Popup to let the user select a folder, returns the path to the folder selected
    def __init__(self, parent, title, question):
        Toplevel.__init__(self, parent)
        self.title(title)
        self.question = question
        self.transient(parent)
        self.protocol("WM_DELETE_WINDOW", self.cancel)
        self.result = None
        self.createWidgets()
        self.grab_set()
        self.wait_window()
    def createWidgets(self):
        frmQuestion = Frame(self)
        Label(frmQuestion, text=self.question).grid()
        frmQuestion.grid(row=1)
        frmButtons = Frame(self)
        frmButtons.grid(row=2)
        btnSelectFolder = Button(frmButtons, text="Select Folder", command=self.selectFolder)
        btnSelectFolder.grid(column=0, row=0)
    def selectFolder(self):
        from tkinter import filedialog
        folder_selected = filedialog.askdirectory()
        if folder_selected:
            self.result = folder_selected
            self.destroy()
    def cancel(self):
        self.result = None
        self.destroy()

class ConfirmationBox(Toplevel):
    def __init__(self, parent, title, question):
        Toplevel.__init__(self, parent)
        self.title(title)
        self.question = question
        self.transient(parent)
        self.protocol("WM_DELETE_WINDOW", self.cancel)
        self.result = None
        self.createWidgets()
        self.grab_set()
        self.wait_window()
    def createWidgets(self):
        frmQuestion = Frame(self)
        Label(frmQuestion, text=self.question).grid()
        frmQuestion.grid(row=1)
        frmButtons = Frame(self)
        frmButtons.grid(row=2)
        btnYes = Button(frmButtons, text="Yes", command=self.yes)
        btnYes.grid(column=0, row=0)
        btnNo = Button(frmButtons, text="No", command=self.no)
        btnNo.grid(column=1, row=0)
    def yes(self):
        self.result = True
        self.destroy()
    def no(self):
        self.result = False
        self.destroy()
    def cancel(self):
        self.result = False
        self.destroy()

class MessageBox(Toplevel):
    def __init__(self, parent, title, message, button_text="OK"):
        Toplevel.__init__(self, parent)
        self.title(title)
        self.message = message
        self.button_text = button_text
        self.transient(parent)
        self.protocol("WM_DELETE_WINDOW", self.close)
        self.createWidgets()
        self.grab_set()
        self.wait_window()
    def createWidgets(self):
        frmMessage = Frame(self)
        Label(frmMessage, text=self.message).grid()
        frmMessage.grid(row=1)
        frmButtons = Frame(self)
        frmButtons.grid(row=2)
        btnClose = Button(frmButtons, text=self.button_text, command=self.close)
        btnClose.grid(column=0, row=0)
    def close(self):
        self.destroy()

class StringInputPopup(Toplevel):
    def __init__(self, parent, title, question, hide_input=False):
        Toplevel.__init__(self, parent)
        self.title(title)
        self.question = question
        self.transient(parent)
        self.hide_input = hide_input
        self.protocol("WM_DELETE_WINDOW", self.cancel)
        self.result = None
        self.createWidgets()
        self.grab_set()
        self.wait_window()
    def createWidgets(self):
        frmQuestion = Frame(self)
        Label(frmQuestion, text=self.question).grid()
        frmQuestion.grid(row=1)
        frmInput = Frame(self)
        self.input_var = StringVar()
        if self.hide_input:
            self.input_entry = Entry(frmInput, textvariable=self.input_var, show="*")
        else:
            self.input_entry = Entry(frmInput, textvariable=self.input_var)
        self.input_entry.grid()
        frmInput.grid(row=2)
        frmButtons = Frame(self)
        frmButtons.grid(row=3)
        btnSubmit = Button(frmButtons, text="Submit", command=self.submit)
        btnSubmit.grid(column=0, row=0)
    def submit(self):
        self.result = self.input_var.get()
        self.destroy()
    def cancel(self):
        self.result = None
        self.destroy()