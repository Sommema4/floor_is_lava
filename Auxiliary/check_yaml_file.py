import yaml

file = 'Baseballers.yaml'

with open(file, 'r') as f:
    try:
        # Converts yaml document to python object
        d = yaml.safe_load(f)
        print(d)
    except yaml.YAMLError as e:
        print(e)