""" Helper function"""

def remap(v, domainlow,domainhigh,rangelow,rangehigh):
    """Maps v in (domainlow,domainhigh) to (rangelow,rangehigh)"""
    return (v-domainlow) * (rangehigh-rangelow) / (domainhigh-domainlow) + rangelow

