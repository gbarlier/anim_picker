import sys

def safe_code_exec(cmd):
    '''Safely execute code in new namespace
    '''
    try:
        exec cmd in {}
    except:
        raise sys.exc_info()[0], sys.exc_info()[1], sys.exc_info()[2]