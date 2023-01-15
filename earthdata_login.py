from netrc import netrc
from subprocess import Popen
from getpass import getpass
import os

# Authentication Configuration
urs = 'urs.earthdata.nasa.gov'
prompts = [
    'Enter NASA Earthdata Login Username \n(or create an account at urs.earthdata.nasa.gov): ',
    'Enter NASA Earthdata Login Password: ',
]

# Determine if netrc file exists, and if so check for NASA Earthdata Login Credentials
try:
    netrc_dir = os.path.expanduser("~/.netrc")
    netrc(netrc_dir).authenticators(urs)[0]
except FileNotFoundError:
    home_dir = os.path.expanduser("~")
    Popen("touch {0}.netrc | chmod og-rw {0}.netrc | echo machine {1} >> {0}.netrc".format(home_dir + os.sep, urs), shell=True)
    Popen("echo login {} >> {}.netrc".format(getpass(prompt=prompts[0]), home_dir + os.sep), shell=True)
    Popen("echo password {} >> {}.netrc".format(getpass(prompt=prompts[1]), home_dir + os.sep), shell=True)

# Determine OS and edit netrc file if it exists but is not set up for NASA Earthdata Login
except TypeError:
    home_dir = os.path.expanduser("~")
    Popen('echo machine {1} >> {0}.netrc'.format(home_dir + os.sep, urs), shell=True)
    Popen('echo login {} >> {}.netrc'.format(getpass(prompt=prompts[0]), home_dir + os.sep), shell=True)
    Popen('echo password {} >> {}.netrc'.format(getpass(prompt=prompts[1]), home_dir + os.sep), shell=True)