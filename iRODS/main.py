___author___ = "Richard Hohensinner"
___created___ = "04.02.2021"
___last_modified___ = "20.05.2021"

# general imports
import os, sys, json
from shutil import copyfile
from datetime import datetime

# irods-client imports
from irods.session import iRODSSession
from irods.models import Collection, DataObject
from irods.query import SpecificQuery

# Tkinter imports
from tkinter import messagebox, Label, Button, Entry, Listbox, Tk, PhotoImage, Grid

# global variables
session = None
file_path_list = []
selected_file = ""
session_success = False
selection_success = False
iRODSCredentials = {"host": "", "port": "", "user": "", "pw": "", "zone": ""}


########################################################################################################################
#   Main function of the iRODS tools
#
#   IN:
#   JSON Object params (argv[1])
#   OUT:
#
########################################################################################################################
def main():

    # check input parameters
    if len(sys.argv) == 2:
        params = json.loads(sys.argv[1])
    else:
        raise Exception("Invalid Parameters submitted!")

    tool_type = params["tool_type"]

    try:
        if params["tool_type"] != "up" and params["tool_type"] != "down":
            raise Exception("Invalid tool-type parameter submitted!")
    except:
        raise Exception("No tool-type parameter submitted!")
    is_download_call = True
    if tool_type == "up":
        is_download_call = False

    # check params for integrity
    result_string, params_faulty = check_params(params)

    if params_faulty:
        raise Exception(result_string)

    global iRODSCredentials, session_success, selected_file, selection_success
    iRODSCredentials["host"] = params["irods_host"]
    iRODSCredentials["port"] = params["irods_port"]
    iRODSCredentials["zone"] = params["irods_zone"]

    # create login window
    make_login_window()
    # check tool settings and start tool execution
    if session_success:
        # initialize download tool
        if params["tool_type"] == "down":

            if params["selection_type"] == "explorer":
                make_file_select_window()
            else:
                if (params["file_path"] != ""): #and ("/" in params["file_path"]):
                    selected_file = params["file_path"]
                else:
                    raise Exception("Invalid File Path submitted!")

            if selection_success or params["selection_type"] == "path":
                params["user"] = iRODSCredentials["pw"]
                params["password"] = iRODSCredentials["user"]
                # start download routine
                handle_download_call(params)
            else:
                raise Exception("File Selection failed (No file selected)")

        # initialize upload tool
        elif params["tool_type"] == "up":

            if session_success:
                params["user"] = iRODSCredentials["pw"]
                params["password"] = iRODSCredentials["user"]
                # start upload routine
                handle_upload_call(params)
            else:
                raise Exception("Logging into iRODS failed")
    else:
        raise Exception("Logging into iRODS failed")
# -------------------------------------------------------------------------------------------------------------------- #


########################################################################################################################
#   Login Window class for Tkinter
#
#   IN:
#   Tk Window win
#   OUT:
#   (sets global variables iRODSCredentials, session and session_success)
#
########################################################################################################################
class LoginWindow:
    def __init__(self, win):
        self.window = win
        self.lbl1 = Label(win, text='iRODS Username:')
        self.lbl2 = Label(win, text='iRODS Password:')
        self.t1 = Entry(bd=3)
        self.t2 = Entry(show="*")
        self.b1 = Button(win, text='Login', command=self.login)

        self.window.grid()
        Grid.rowconfigure(self.window, 0, weight=1)
        Grid.rowconfigure(self.window, 1, weight=1)
        Grid.rowconfigure(self.window, 2, weight=1)
        Grid.rowconfigure(self.window, 3, weight=1)
        Grid.rowconfigure(self.window, 4, weight=1)
        Grid.columnconfigure(self.window, 0, weight=1)

        self.lbl1.grid(row=0, column=0, padx="20", pady="1", sticky="w")
        self.t1.grid(row=1, column=0, padx="10", pady="1", sticky="nsew")
        self.lbl2.grid(row=2, column=0, padx="20", pady="1", sticky="w")
        self.t2.grid(row=3, column=0, padx="10", pady="1", sticky="nsew")
        self.b1.grid(row=4, column=0, padx="50", pady="10", sticky="nsew")

    def login(self):
        global iRODSCredentials
        user = str(self.t1.get())
        password = str(self.t2.get())
        if user == "" or password == "":
            self.window.iconify()
            messagebox.showerror("Error", "Username or Password empty!")
            self.window.deiconify()
            return
        else:
            iRODSCredentials["user"] = user
            iRODSCredentials["pw"] = password

        get_irods_session(self.window)
        if not session_success:
            return

        self.window.destroy()
# -------------------------------------------------------------------------------------------------------------------- #


########################################################################################################################
#   File Selection Window class for Tkinter
#
#   IN:
#   Tk Window win
#   OUT:
#   (sets global variables selected_file and selection_success)
#
########################################################################################################################
class FileSelectWindow:
    def __init__(self, win):
        global session, iRODSCredentials
        self.session = session
        self.window = win
        self.b1 = Button(win, text='Select', command=self.select)
        self.lb1 = Listbox(win)

        self.window.grid()
        Grid.rowconfigure(self.window, 0, weight=1)
        Grid.rowconfigure(self.window, 1, weight=1)
        Grid.columnconfigure(self.window, 0, weight=1)

        self.lb1.grid(row=0, column=0, padx="20", pady="1", sticky="nswe")
        self.b1.grid(row=1, column=0, padx="50", pady="1", sticky="ew")

        coll = session.collections.get("/" + iRODSCredentials["zone"] + "/" + "home" + "/" + iRODSCredentials["user"])
        file_list = []

        self.get_files_from_collections(coll, file_list)

        for counter in range(len(file_list)):
            self.lb1.insert(counter, file_list[counter])

    def get_files_from_collections(self, coll, file_list):
        for obj in coll.data_objects:
            file_list.append(obj.path)

        for col in coll.subcollections:
            self.get_files_from_collections(col, file_list)

    def select(self):
        global session, selected_file, selection_success
        try:
            selection = self.lb1.get(self.lb1.curselection())
        except:
            self.window.iconify()
            messagebox.showerror("Error", "No file selected!")
            self.window.deiconify()
            return

        selected_file = selection
        selection_success = True
        self.window.destroy()
# -------------------------------------------------------------------------------------------------------------------- #


########################################################################################################################
#   Creates an iRODS session and sets the global session variable
#
#   IN:
#   Tk Window window
#
#   OUT:
#
########################################################################################################################
def get_irods_session(window):
    global iRODSCredentials
    host = iRODSCredentials["host"]
    port = iRODSCredentials["port"]
    user = iRODSCredentials["user"]
    password = iRODSCredentials["pw"]
    zone = iRODSCredentials["zone"]

    iRODSsession = get_iRODS_connection(host=host, port=port, user=user, password=password, zone=zone)
    global session, session_success
    try:
        coll = iRODSsession.collections.get("/" + zone + "/" + "home" + "/" + user)
    except Exception:
        window.iconify()
        messagebox.showerror("Error", "Invalid Authentification")
        window.deiconify()
        return

    if coll:
        session = iRODSsession
        session_success = True
# -------------------------------------------------------------------------------------------------------------------- #


########################################################################################################################
#   Helper function to initialize Login Window classes and Tk windows
#
#   IN:
#
#   OUT:
#
########################################################################################################################
def make_login_window():
    window = Tk()
    LoginWindow(window)
    window.title('iRODS Login')
    window.geometry("450x225+10+10")
    window.minsize(450, 225)
    window.tk.call('wm', 'iconphoto', window._w, PhotoImage(file='/home/richard/git/galaxy_irods_tools/login.png'))
    # alternative options:
    # window.iconphoto(False, PhotoImage(file='/path/to/ico/icon.png'))
    # window.iconbitmap("/home/richard/git/galaxy_irods_tools/login.ico")
    window.mainloop()
# -------------------------------------------------------------------------------------------------------------------- #


########################################################################################################################
#   Helper function to initialize File Selection Window classes and Tk windows
#
#   IN:
#
#   OUT:
#
########################################################################################################################
def make_file_select_window():
    window = Tk()
    FileSelectWindow(window)
    window.title('iRODS File Select')
    window.geometry("450x225+10+10")
    window.minsize(450, 225)
    window.mainloop()
# -------------------------------------------------------------------------------------------------------------------- #


########################################################################################################################
#   Checks whether arguments are valid and returns true/false depending on params
#
#   IN:
#   Dict params
#
#   OUT:
#   String res_string
#   Bool res_bool
########################################################################################################################
def check_params(params):
    res_string = ""
    res_bool = False

    try:
        if params["irods_host"] == "":
            res_string += "Host empty!\n"
            res_bool = True
        if params["irods_port"] == "":
            res_string += "Port empty!\n"
            res_bool = True
        if params["irods_zone"] == "":
            res_string += "Zone empty!\n"
            res_bool = True
        if params["selection_type"] == "path" and params["file_path"] == "":
            res_string += "Missing file path!\n"
            res_bool = True
    except:
        raise Exception("Invalid/Missing Parameters")

    return res_string, res_bool
# -------------------------------------------------------------------------------------------------------------------- #


########################################################################################################################
#   Function to handle iRODS download calls
#
#   IN:
#   Dict params
#
#   OUT:
#
########################################################################################################################
def handle_download_call(params):

    global session, selected_file

    # check if /ZONE/USER/...FILE... pattern is valid
    if len(selected_file.split("/")) < 2:
        raise Exception("Path to file is not valid in iRODS")

    file_list = []

    # check if file is a directory
    if "." not in selected_file:
        try:
            coll = session.collections.get(selected_file)
            for file in coll.data_objects:
                file_list.append(file.path)
        except:
            raise Exception("Invalid directory path specified!")
    else:
        file_list.append(selected_file)

    # get registry file
    reg_file = ""
    for dirpath, dirnames, filenames in os.walk(params["galaxy_root"]):
        for fn in filenames:
            if fn == "irods_galaxy_registry.xml":
                reg_file = os.path.join(dirpath, fn)
            if reg_file != "":
                break
        if reg_file != "":
            break

    # handle download for all files in file_list
    for file in file_list:

        file_to_get = file

        # handle path and file name
        name_file_to_get = file_to_get.split("/")[-1]
        path_file_to_get = "/".join(file_to_get.split("/")[0:len(file_to_get.split("/")) - 1])

        # check iRODS filesystem
        check_iRODS_destination(session, path_file_to_get, name_file_to_get)

        # get file object from iRODS
        iRODS_file_object = session.data_objects.get(path_file_to_get + "/" + name_file_to_get)
        input_file = iRODS_file_object.open("r+")
        output_file = open(name_file_to_get, "wb")
        output_file.write(input_file.read())

        input_file.close()
        output_file.close()

        abs_file_path = os.path.abspath(name_file_to_get)

        file_type = str(name_file_to_get.split(".")[-1])

        file_content = {"uuid": None,
                        "file_type": "auto",
                        "space_to_tab": False,
                        "dbkey": "?",
                        "to_posix_lines": True,
                        "ext": file_type,
                        "path": abs_file_path,
                        "in_place": True,
                        "dataset_id": params["job_id"],
                        "type": "file",
                        "is_binary": False,
                        "link_data_only": "copy_files",
                        "name": name_file_to_get
                        }

        with open("temporal.json", "w") as fileParams:
            fileParams.write(json.dumps(file_content))
        fileParams.close()

        # load file into Galaxy by using the integrated upload tool - Preparation
        python_command = params["galaxy_root"] + "/tools/data_source/upload.py"
        arg1 = params["galaxy_root"]
        arg2 = params["galaxy_datatypes"]
        arg3 = os.path.abspath(fileParams.name)
        arg4 = params["job_id"] + ":" + params["out_dir"] + ":" + params["out_file"]

        # copy sample registry.xml to working directory
        copyfile(reg_file, params["galaxy_datatypes"])

        # activate environment for new process call and call the python upload command either both with
        sys.path.append(params["galaxy_root"] + "/lib")
        os.system("python -c \'import sys;sys.path.append(\"" + params["galaxy_root"] + "/lib\")\'" + " python " +
                  python_command + " " + arg1 + " " + arg2 + " " + arg3 + " " + arg4)
    
    # close connection
    session.cleanup()
# -------------------------------------------------------------------------------------------------------------------- #


########################################################################################################################
#   Function to handle iRODS upload calls
#
#   IN:
#   Dict params
#
#   OUT:
#
########################################################################################################################
def handle_upload_call(params):

    global session, iRODSCredentials

    path_to_file = params["up_file_path"]
    name_of_file = params["up_file"]

    coll_path = "/" + iRODSCredentials["zone"] + "/home/" + iRODSCredentials["user"] + "/galaxyupload"
    try:
        coll = session.collections.get(coll_path)
    except:
        coll = session.collections.create(coll_path)

    now = datetime.now()

    # dd/mm/YY
    day = now.strftime("%d%m%Y")
    time = now.strftime("%H%M%S")

    coll_path = coll_path + "/" + day

    try:
        coll = session.collections.get(coll_path)
    except:
        coll = session.collections.create(coll_path)

    irods_file_name = time + "_" + name_of_file
    iRODS_file_object = session.data_objects.create(coll_path + "/" + irods_file_name)
    iRODS_file_object = session.data_objects.get(coll_path + "/" + irods_file_name)

    irods_file = iRODS_file_object.open("w")
    galaxy_file = open(path_to_file, "rb")
    content = galaxy_file.read()
    irods_file.write(content)

    # TODO can't close session without writing process finished - but reading/writing happens async.
    # session.cleanup()

    pass
# -------------------------------------------------------------------------------------------------------------------- #


########################################################################################################################
#   Function to initialize an iRODS Session - will raise an Exception if timeout is longer than 2 seconds
#
#   IN:
#   String host
#   String port
#   String user
#   String password
#   String zone
#
#   OUT:
#   iRODSSession-object session
########################################################################################################################
def get_iRODS_connection(host, port, user, password, zone):

    # initialize timeout checker - fires after 2 secs
    import signal
    signal.signal(signal.SIGALRM, timeout_checker)
    signal.alarm(2)

    try:
        session = iRODSSession(host=host, port=port, user=user, password=password, zone=zone)
    except Exception:
        raise Exception("There was a timeout creating the iRODS session")

    # void/reset alarm
    signal.alarm(0)

    return session
# -------------------------------------------------------------------------------------------------------------------- #


########################################################################################################################
#   Helper function to raise timeout exception when SIGALRM fires
#
#   IN:
#
#   OUT:
#
########################################################################################################################
def timeout_checker():

    raise Exception("iRODS session timeout")
# -------------------------------------------------------------------------------------------------------------------- #


########################################################################################################################
#   Function to check if file exists in iRODS
#
#   IN:
#   String path
#
#   OUT:
#   Bool ret_bool
#
########################################################################################################################
def check_if_file_exists(path):

    if os.path.isfile(path):
        ret_bool = True
    else:
        ret_bool = False

    return ret_bool
# -------------------------------------------------------------------------------------------------------------------- #


########################################################################################################################
#   Function to check iRODS destination
#
#   IN:
#   iRODSSession-object session
#   String path
#   String name
#
#   OUT:
#   Bool ret_bool
#
########################################################################################################################
def check_iRODS_destination(session, path, name):

    try:
        session.collections.get(path.rstrip("/"))
    except Exception:
        raise Exception("Collection doesn't exist in iRODS file system")

    try:
        session.data_objects.get(path.rstrip("/") + "/" + name)
    except Exception:
        raise Exception("File doesn't exist in iRODS file system")
# -------------------------------------------------------------------------------------------------------------------- #


if __name__ == "__main__":
    main()
