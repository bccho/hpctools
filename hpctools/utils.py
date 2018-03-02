import json

def print_dict(D, indent=2):
    """ Utility function for pretty printing dictionaries in JSON format. """
    print(json.dumps(D, indent=2))
    