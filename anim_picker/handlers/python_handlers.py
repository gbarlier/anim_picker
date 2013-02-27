import sys

def safe_code_exec(cmd, env=dict()):
    '''Safely execute code in new namespace with specified dictionary
    '''
    try:
        exec cmd in env
    except:
        raise sys.exc_info()[0], sys.exc_info()[1], sys.exc_info()[2]