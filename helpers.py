""" Helper function"""


import logging

import sys

def remap(v, domainlow,domainhigh,rangelow,rangehigh):
    """Maps v in (domainlow,domainhigh) to (rangelow,rangehigh)"""
    return (v-domainlow) * (rangehigh-rangelow) / (domainhigh-domainlow) + rangelow

def createLogger():
    # Set up logger to log to screen
    log = logging.getLogger('logger')
    log.setLevel(logging.INFO)
    #log.setLevel(logging.DEBUG)
    h = logging.StreamHandler(sys.stdout)
    h.setFormatter(logging.Formatter('%(message)s'))  
    log.addHandler(h)    
    return log