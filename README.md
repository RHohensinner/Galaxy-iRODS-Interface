# Galaxy iRODS Interface

Author:
Richard Hohensinner

## Tools:

The Galaxy iRODS Interface consists of two tools. 
1. The **Download Tool** can be used to load data from iRODS directly into 
   your Galaxy History. 
   It provides a User Interface for secure authentication and for file selection. In addition, it 
   is also possible to specify file paths to files stored in iRODS for an easier and faster loading process.
   

2. The **Upload Tool** makes it possible to extract data from your Galaxy History to an iRODS DM system. This way, your 
   research data can be easily saved, back-uped and shared with collaborators.
   
## Development:

The Galaxy iRODS tools were developed with [planemo](https://planemo.readthedocs.io/en/latest/writing.html) in Python 
code. Additionally, .xml files and .png icons are used for the tools infrastructure and User Interface. The Python
library "TK" was used to build the UI and "python-irods-client" was used for the iRODS session management.
