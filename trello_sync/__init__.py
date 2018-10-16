from confapp import conf

try:
    import local_settings
    conf += local_settings
except:
    pass