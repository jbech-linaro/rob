#!/usr/bin/python3

import json
import logging
import os
import queue
import subprocess
import sys
import time
import threading

class Job(object):
    """This class represents a build job"""
    # FIXME: Should be moved to the static flask folder?
    log_folder = os.getcwd() + "/logs"
    reference_folder = "/home/joakim.bech/devel/optee_projects/reference"

    def __init__(self, id, json_file):
        self.id = id
        self.json_file = json_file
        self.build_cmds = None
        self.clean_cmds = None
        self.folders = None
        self.reference = None
        self.repo_xml = "default.xml"
        self.toolchain = None
        self.job_type = None
        self.override = None
        self.cmds = queue.Queue()
        self.workspace = None

    def add_cmd(self, cmd):
        """Function that adds a command to the command queue"""
        self.cmds.put(cmd + self.get_log_str())

    def get_log_str(self, force_append=False):
        """Function use to output to a build log to a file with a name coming
        from the build ID. The force_append is a special case. If set to True it
        will get the 'append' line even though the cmd queue is empty"""
        if self.cmds.empty() and not force_append:
            return " > %s/%s.txt  2>&1 " % (Job.log_folder, self.id)
        else:
            return " >> %s/%s.txt 2>&1" % (Job.log_folder, self.id)

    def run(self):
        """Function that starts executing command in the command queue"""
        rc = 0
        try:
            # Measure the time it takes to run the entire job
            start = time.time()

            while not self.cmds.empty():
                cmd = self.cmds.get()
                logging.debug(">>>>> Running cmd: '%s'" % cmd)
                output = subprocess.check_call(cmd, cwd=self.workspace, shell=True)
                logging.debug("<<<<< output cmd: '%s'" % output)

            self.log_time("Total build time", start, time.time())
        except subprocess.CalledProcessError:
            loggin.error("Something went wrong, bail out ...")
            rc = 1
        finally:
            while not self.cmds.empty():
                self.cmds.get()
        return rc

    def log(self):
        """Returns the log from a job"""
        return

    def query(self):
        """Query an ongoing job"""
        logging.debug("Job ID: %s" % self.id)
        return

    def add_clean_cmds(self):
        """Function that takes care of all commands related to cleaning"""
        if self.clean_cmds is None:
            logging.debug("add_clean_cmds: No clean commands")
            return 0

        for cmd in self.clean_cmds:
            # We cannot clean a repo dir if it doesn't exist and therefore we
            # must explicitly check for existance before trying to do so.
            if "repo" in cmd:
                if os.path.exists(self.workspace + "/.repo"):
                    logging.debug("Found repo clean .. %s" % cmd)
                    self.add_cmd(cmd)
            else:
                logging.debug("cleaning .. %s" % cmd)
                self.add_cmd(cmd)
        return 0

    def create_folders(self):
        """Function that creates all folders that are expected"""
        if self.workspace is None:
            logging.error("We must have a workspace")
            return 1

        cmd = "mkdir -p %s%s" % (self.workspace, self.get_log_str())
        output = subprocess.check_call(cmd, shell=True)

        if self.folders is None:
            logging.debug("create_folders: No folder to create")
            return 0

        for folder in self.folders:
            self.add_cmd("mkdir -p %s" % folder)
        return 0

    def get_toolchains(self):
        """This is a very specific function for OP-TEE, if this should be used
        in a another more generic setup, this would need to be re-written.
        OP-TEE has a make rule that gets the toolchains. But since that takes
        some time and the toolchains in use there, seldomly changes, it saves
        time to just link to a pre-existing folder. This function symlinks to
        the toolchain stated in the json file if it was stated, otherwise it run
        the OP-TEE make command to get the toolchain"""
        if self.toolchain is None:
            self.add_cmd("cd build && make toolchains -j3")
        else:
            self.add_cmd("ln -sf %s %s/toolchains" % (self.toolchain,
                self.workspace))
        return 0

    def log_time(self, message, start, end):
        """Function that calculates hour, minutes and second and log that
        together with a message to the build log file"""
        m, s = divmod(end - start, 60)
        h, m = divmod(m, 60)
        cmd = "echo '%s: %sh %sm %ss'%s" % (message, h, m, round(s, 2), self.get_log_str(True))
        logging.debug(cmd)
        output = subprocess.check_call(cmd, shell=True)

    def add_build_cmds(self):
        """Function that adds all build commands to the build queue"""
        if self.build_cmds is None:
            logging.debug("add_build_cmds: No build commands")
            return 0

        for cmd in self.build_cmds:
            # If it's a repo init command and we have specified a reference,
            # then let's use it.
            if "repo init" in cmd and self.reference:
                cmd += " --reference %s" % self.reference
            self.add_cmd(cmd)
        return 0

    def start(self):
        """Function that starts a full build job"""
        if self.parse_json():
            return 1
        if self.create_folders():
            return 1
        if self.add_clean_cmds():
            return 1
        if self.get_toolchains():
            return 1
        if self.add_build_cmds():
            return 1
        if self.run():
            return 1
        return 0

    def stop(self):
        """Stop an ongoing job"""
        return

    def url(self):
        """Return URL to the job information"""
        return

    def parse_json(self):
        """Function that parses a JSON configuration file"""
        with open(self.json_file) as json_data:
            d = json.load(json_data)
            if "build" in d:
                self.build_cmds = d['build']
                logging.debug("json.build: %s" % self.build_cmds)

            if "clean" in d:
                self.clean_cmds = d['clean']
                logging.debug("json.clean: %s" % self.clean_cmds)

            if "folders" in d:
                self.folders = d['folders']
                logging.debug("json.folders: %s" % self.folders)

            if "override" in d:
                self.override = d['override']
                logging.debug("json.override: %s" % self.override)

            if "reference" in d:
                self.reference = d['reference']
                logging.debug("json.reference: %s" % self.reference)
            else:
                logging.error("'reference' is mandatory in the json file")
                return 1

            if "repo_xml" in d:
                self.repo_xml = d['repo_xml']
                logging.debug("json.repo_xml: %s" % self.repo_xml)
            else:
                logging.error("'repo_xml' is mandatory in the json file")
                return 1

            if "toolchain" in d:
                self.toolchain = d['toolchain']
                logging.debug("json.toolchain: %s" % self.toolchain)

            if "type" in d:
                self.job_type = d['type']
                logging.debug("json.type: %s" % self.job_type)

            if "workspace" in d:
                self.workspace = d['workspace']
                logging.debug("json.workspace: %s" % self.workspace)
            else:
                logging.error("'workspace' is mandatory in the json file")
                return 1

            return 0

    def __str__(self):
        return "json job file: %s" % self.json_file

def run_job(q):
    logging.debug("Running a build job")
    while True:
        job = q.get()
        logging.debug(job)
        job.start()
        q.task_done()

def test():
    logging.basicConfig(level=logging.DEBUG,
            format='[%(levelname)s : %(threadName)-10s] %(message)s')
    start = time.time()
    job_queue = queue.Queue()
    nbr_threads = 3

    for i in range(nbr_threads):
        worker = threading.Thread(target=run_job, args=(job_queue,))
        worker.setDaemon(True)
        worker.start()

    jobs = [Job(1, "./json/qemu.json"),
            Job(2, "./json/rpi3.json"),
            Job(3, "./json/fvp.json")]

    for j in jobs:
        job_queue.put(j)

    job_queue.join()

    m, s = divmod(time.time() - start, 60)
    h, m = divmod(m, 60)
    logging.debug("Total run time for all jobs: %sh %sm %ss" %
            (h, m, round(s, 2)))

if __name__ == "__main__":
    test()
