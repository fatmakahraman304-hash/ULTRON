"""Kill only processes owned by this launcher if its process exits unexpectedly."""
import os

class ProcessJob:
    def __init__(self):
        self.handle=None
        if os.name=='nt':
            import win32job
            self.handle=win32job.CreateJobObject(None,"")
            info=win32job.QueryInformationJobObject(self.handle,win32job.JobObjectExtendedLimitInformation)
            info['BasicLimitInformation']['LimitFlags']=win32job.JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
            win32job.SetInformationJobObject(self.handle,win32job.JobObjectExtendedLimitInformation,info)
    def add(self,process):
        if self.handle:
            import win32api,win32con,win32job
            handle=win32api.OpenProcess(win32con.PROCESS_SET_QUOTA|win32con.PROCESS_TERMINATE,False,process.pid)
            try:win32job.AssignProcessToJobObject(self.handle,handle)
            finally:handle.Close()
    def close(self):
        if self.handle:self.handle.Close();self.handle=None
