import logging, locale, coloredlogs
coloredlogs.install(level='INFO', fmt='[%(levelname)-8s]   %(name)-50s %(message)s')
logging.basicConfig(level=logging.INFO, format="[%(levelname)-8s]   %(name)-50s %(message)s")
