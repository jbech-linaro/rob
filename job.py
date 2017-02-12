#!/usr/bin/python3

import os
import queue
import subprocess
import time

class Job(object):
    """This class represents a build job"""
    # FIXME: Should be moved to the static flask folder?
    log_folder = os.getcwd() + "/logs"
    reference_folder = "/home/joakim.bech/devel/optee_projects/reference"

    def __init__(self, id, path):
        self.id = id
        self.jobtype = "None"
        self.cmds = queue.Queue()
        self.workspace = path
        output = subprocess.check_output("mkdir -p " + self.workspace, shell=True)
        output = subprocess.check_output("mkdir -p " + Job.log_folder, shell=True)

    def add_cmd(self, cmd):
        if self.cmds.empty():
            log_str =  " > %s/%s.txt  2>&1 " % (Job.log_folder, self.id)
        else:
            log_str =  " >> %s/%s.txt 2>&1" % (Job.log_folder, self.id)
        self.cmds.put(cmd + log_str)

    def build(self):
        """Start a build job"""
        rc = 0
        try:
            # Measure the time it takes to run the entire job
            t = time.time()

            while not self.cmds.empty():
                cmd = self.cmds.get()
                print("\n>>>>> Running cmd: '%s'" % cmd)
                output = subprocess.check_call(cmd, cwd=self.workspace, shell=True)
                print("<<<<< output cmd: '%s'" % output)

            log_str =  " 2>&1 | tee -a %s/%s.txt" % (Job.log_folder, self.id)
            delta = time.time() - t
            m, s = divmod(delta, 60)
            h, m = divmod(m, 60)
            cmd = "echo 'Total build time: %sh %sm %ss'%s" % (h, m, round(s, 2), log_str)
            output = subprocess.check_call(cmd, shell=True)
        except subprocess.CalledProcessError:
            print("Something went wrong, bail out ...")
            rc = 1
        finally:
            while not self.cmds.empty():
                self.cmds.get()

        return rc

    def log(self):
        """Return the log from a job"""
        return

    def query(self):
        """Query an ongoing job"""
        print("Job ID: %s" % self.id)
        return

    def stop(self):
        """Stop an ongoing job"""
        return

    def url(self):
        """Return the log from a job"""
        return

    def workspace(self, path):
        """Return the log from a job"""
        self.workspace = path
        return

class Qemu(Job):
    def __init__(self, id):
        """QEMU class that initialize the job queue"""
        super().__init__(id, "/home/joakim.bech/devel/optee_projects/qemu")
        self.jobtype = "qemu"
        # FIXME: All this could go into "config-files" instead of hardcoding it
        # here.
        if os.path.exists(self.workspace + "/.repo"):
            self.add_cmd("repo forall -c 'git checkout -f && git clean -xdf'")
        self.add_cmd("repo init -u https://github.com/OP-TEE/manifest.git -m default.xml --reference %s" % Job.reference_folder)
        self.add_cmd("repo sync -j3 -d")
        self.add_cmd("ln -sf %s/toolchains %s/toolchains" % (Job.reference_folder, self.workspace))
        self.add_cmd("cd build && make all -j12")

    def __str__(self):
        return "I'm a %s class" % self.jobtype

class Rpi3(Job):
    def __init__(self, id):
        """Raspberry Pi3 class that initialize the job queue"""
        super().__init__(id, "/home/joakim.bech/devel/optee_projects/rpi3")
        self.jobtype = "rpi3"
        # FIXME: All this could go into "config-files" instead of hardcoding it
        # here.
        if os.path.exists(self.workspace + "/.repo"):
            self.add_cmd("repo forall -c 'git checkout -f && git clean -xdf'")
        self.add_cmd("repo init -u https://github.com/OP-TEE/manifest.git -m %s.xml --reference %s" % (self.jobtype, Job.reference_folder))
        self.add_cmd("repo sync -j3 -d")
        self.add_cmd("ln -sf %s/toolchains %s/toolchains" % (Job.reference_folder, self.workspace))
        self.add_cmd("cd build && make all -j12")

    def __str__(self):
        return "I'm a %s class" % self.jobtype

class Fvp(Job):
    def __init__(self, id):
        """Foundation Models class that initialize the job queue"""
        super().__init__(id, "/home/joakim.bech/devel/optee_projects/fvp")
        self.jobtype = "fvp"
        # FIXME: All this could go into "config-files" instead of hardcoding it
        # here.
        if os.path.exists(self.workspace + "/.repo"):
            self.add_cmd("repo forall -c 'git checkout -f && git clean -xdf'")
        self.add_cmd("mkdir -p %s/Foundation_Platformpkg" % self.workspace)
        self.add_cmd("repo init -u https://github.com/OP-TEE/manifest.git -m %s.xml --reference %s" % (self.jobtype, Job.reference_folder))
        self.add_cmd("repo sync -j3 -d")
        self.add_cmd("ln -sf %s/toolchains %s/toolchains" % (Job.reference_folder, self.workspace))
        self.add_cmd("cd build && make all -j12")

    def __str__(self):
        return "I'm a %s class" % self.jobtype

def test():
    qemu = Qemu(1)
    qemu.build()

    rpi3 = Rpi3(2)
    rpi3.build()

    fvp = Fvp(3)
    fvp.build()

if __name__ == "__main__":
    test()
