from subprocess import run as sp_run, Popen


def execute_async(cmd: str) -> Popen:
    """ Execute "cmd" and DON'T wait until it finishes """
    return Popen(cmd, shell=True)


def execute(cmd: str) -> None:
    """ Execute "cmd" and WAIT until it finishes """
    sp_run(cmd, shell=True, capture_output=True)


def get_execute(cmd: str) -> str:
    """ Execute "cmd" and return stdout as lines """
    res = sp_run(cmd, shell=True, capture_output=True).stdout
    if not res:
        return ''
    return res.decode().strip()
