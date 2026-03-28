import yaml
import pygame
import os

data = {
    'Dark magic den':{
        'obstacles': [[0, 0, 0.05, 0.95], #left curb
                      [0.05, 0, 0.90, 0.05], #top curb
                      [1 - 0.05, 0, 0.05, 0.95], # right curb
                      [0, 1 - 0.05, 1, 0.05] # bottom curb
                      ],
        'renders': [['floor_resized.png', 0, 0],
                    ],
    },
    'Satan\'s lair':{
    },

}

# Convert dictionary to YAML
with open('Maps.yaml', 'w') as outfile:
    yaml.dump(data, outfile, default_flow_style=False)